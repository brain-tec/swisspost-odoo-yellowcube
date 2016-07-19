# b-*- encoding: utf-8 -*-
##############################################################################
#
#    Copyright (c) 2014 brain-tec AG (http://www.brain-tec.ch)
#    All Right Reserved
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

from openerp.osv import osv, orm, fields
from openerp.tools.translate import _
from openerp.tools.safe_eval import safe_eval
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT, DEFAULT_SERVER_DATETIME_FORMAT
import base64
from dateutil import relativedelta
import datetime
import logging
logger = logging.getLogger(__name__)


class stock_production_lot_ext(osv.Model):
    _name = 'stock.production.lot'
    _inherit = ['stock.production.lot', 'mail.thread']

    def to_remove(self, cr, uid, ids, context=None):
        ''' Returns whether a lot must be removed, according to its removal_date.
        '''
        if context is None:
            context = {}
        for lot in self.browse(cr, uid, ids, context=context):
            if lot.removal_date and lot.removal_date < fields.date.today():
                return True
        return False

    def _get_virtual_available(self, cr, uid, ids, field, arg, context=None):
        ret = {}
        for lot in self.browse(cr, uid, ids, context=context):
            if lot.to_remove():
                ret[lot.id] = 0
                continue
            ret[lot.id] = lot.stock_available
            for move in lot.move_ids:
                if move.location_id.usage in ['internal'] or move.location_dest_id.usage in ['internal']:
                    if move.state in ['assigned']:
                        ret[lot.id] -= move.product_qty
        return ret

    def _get_virtual_available_for_sale(self, cr, uid, ids, fields, arg, context=None):
        ''' Gets the amount which is available for sale for the current lot.
            The amount available for sale is taken from the stock location of the warehouse.
        '''
        if context is None:
            context = {}
        if not isinstance(ids, list):
            ids = [ids]

        # Gets the current warehouse. There must be just one warehouse.
        stock_location_ids = self.pool.get('stock.warehouse').get_stock_location_ids(cr, uid, [], context=context)

        if not stock_location_ids:
            raise orm.except_orm(_('No Location Stock Defined'),
                                 _('No location was defined for stock (Location Stock) on the warehouse.'))
        elif 'use_stock_location_id' in context:
            stock_location_ids = [context['use_stock_location_id']]

        res = {}.fromkeys(ids, 0.0)
        for lot in self.browse(cr, uid, ids, context=context):
            if lot.to_remove():
                res[lot.id] = 0
                continue

            # Gets the quantity we have of this lot in the stock location.
            cr.execute('''SELECT prodlot_id, qty
                          FROM stock_report_prodlots
                          WHERE location_id in ({location})
                          AND prodlot_id = {lot}'''.format(location=','.join(map(str, stock_location_ids)),
                                                           lot=lot.id))
            res.update(dict(cr.fetchall()))

            # We don't take into account the quantity which has been already assigned.
#             for move in lot.move_ids:
#                 if (move.location_id.id == stock_location.id) and (move.state == 'assigned'):
#                         res[lot.id] -= move.product_qty
            for move in lot.move_ids:
                if move.state == 'assigned' and move.location_id.id in stock_location_ids:
                    res[lot.id] -= move.product_qty

        return res

    def _search_virtual_available_for_sale(self, cr, uid, obj, field_name, args, context=None):
        ''' Search function to be able to search on the field virtual_available_for_sale.
        '''
        if context is None:
            context = {}

        target_lot_ids = []

        # Searches for those lots which have a virtual available greater than zero.
        lots_ids = self.search(cr, uid, ['|', ('removal_date', '=', False),
                                         ('removal_date', '>=', fields.date.today()),
                                         ], context=context)

        operator = args[0][1]  # The operator to use on the comparison.
        quantity = args[0][2]  # The quantity against which we compare.

        for lot_id in lots_ids:
            virtual_available = self._get_virtual_available_for_sale(cr, uid, lot_id, False, False, context=context)[lot_id]
            if safe_eval('{virtual_available} {operator} {value}'.format(virtual_available=virtual_available, operator=operator, value=quantity)):
                target_lot_ids.append(lot_id)

        return [('id', 'in', target_lot_ids)]

    def create(self, cr, uid, values, context=None):
        ret = super(stock_production_lot_ext, self).create(cr, uid, values, context=context)
        if 'production_date' in values or 'use_date' in values:
            self._set_expiry_dates(cr, uid, ret, context)
        return ret

    def __msg_txt(self, values, key):
        if key in values:
            x = values[key]
            return '{0}:{1}'.format(type(x).__name__, x)
        else:
            return '<i>Missing</i>'

    def write(self, cr, uid, ids, values, context=None):
        if not isinstance(ids, list):
            ids = [ids]
        for _id in ids:
            old_values = self.read(cr, uid, _id, [x for x in values], context=context)
            msg = 'Change on values:<br/><table border="1px"><tr><td>Field</td><td>Old</td><td>New</td></tr>'
            for k in values:
                msg = '{0}<tr><td>{1}</td><td>{2}</td><td>{3}</td></tr>'.format(msg,
                                                                                k,
                                                                                self.__msg_txt(old_values, k),
                                                                                self.__msg_txt(values, k))
            msg = '{0}</table>'.format(msg)
            self.message_post(cr, uid, [_id], msg, context=context)
        ret = super(stock_production_lot_ext, self).write(cr, uid, ids, values, context=context)
        if 'production_date' in values or 'use_date' in values:
            self._set_expiry_dates(cr, uid, ids, context)
        return ret

    def _expiration_uom(self, cr, uid, tuples=True, uom='days', value=0, context=None):
        ret = []
        for f in [('days', 'Day(s)'),
                  ('weeks', 'Week(s)'),
                  ('months', 'Month(s)'),
                  ('years', 'Year(s)')]:
            if tuples:
                ret.append(f)
            elif f[0] == uom:
                args = {uom: value * -1}
                return relativedelta.relativedelta(**args)
        return ret

    def _get_lot_date(self, cr, uid, product, lot, field, context=None):
        lot_creation_date = lot.production_date and datetime.datetime.strptime(lot.production_date, '%Y-%m-%d %H:%M:%S')
        lot_use_date = lot.use_date and datetime.datetime.strptime(lot.use_date, '%Y-%m-%d %H:%M:%S')

        duration_create = getattr(product, field[0])
        date_create = duration_create and lot_creation_date + datetime.timedelta(days=duration_create) or None

        duration_end = None
        if lot_use_date:
            if field[0] in ('alert_time', 'removal_time'):
                f = field[0]
                if f == 'removal_time':
                    f = 'block_time'
                f = 'expiration_{0}'.format(f)
                v = float(getattr(product, f))
                u = getattr(product, '{0}_uom'.format(f))
                if u and v:
                    duration_end = self._expiration_uom(cr, uid, False, u, v, context=context)
        date_end = duration_end and lot_use_date + duration_end or None
        logger.debug('_get_lot_date')
        logger.debug('{0}: {1}'.format(type(date_create), date_create))
        logger.debug('{0}: {1}'.format(type(date_end), date_end))
        if (not date_end) and (not date_create):
            return None
        if (not date_end) or date_create and date_create < date_end:
            return date_create
        else:
            return date_end

    def _set_expiry_dates(self, cr, uid, ids, context=None):
        if isinstance(ids, list):
            for _id in ids:
                self._set_expiry_dates(cr, uid, _id, context)
            return True
        date_fields = (('alert_time', 'alert_date', _('This product lot is near its removal date'), 4, -1),
                       ('removal_time', 'removal_date', _('Attention: This product lot must be removed from sell'), 3, 3),
                       ('use_time', 'use_date', _('Warning: This product lot must not be used after this date'), 2, 2),
                       ('life_time', 'life_date', _('Danger: This product lot has exceeded its safety life-time!'), 1, 2),
                       )
        lot = self.browse(cr, uid, ids, context=context)
        product = lot.product_id

        logger.debug("Checking product {0}\tlot {1}".format(product.name, lot.name))
        for field in date_fields:
            if not getattr(lot, field[1]):
                date = self._get_lot_date(cr, uid, product, lot, field, context=context)
                if date:
                    msg = _('Updating lot date {0}, with value {1}, because it was unset').format(field[1], date)
                    # logger.debug(msg)
                    self.write(cr, uid, lot.id, {field[1]: date.strftime('%Y-%m-%d %H:%M:%S')}, context=context)
                    self.message_post(cr, uid, lot.id, msg, context=context)

    def _get_list_of_customers_who_received_a_lot(self, cr, uid, ids, context=None):
        ''' Returns a list of lists, in which each element is a field following this format:
            [name,
             shippment_address,
             email,
             phone_number,
             mobile_phone_number
            ].
            The first list contains the keys (thus, at least a list of length 1 is always returned with he headind)
        '''
        if context is None:
            context = {}

        # Caches those stock.location's to be used with customers.
        stock_location_customer_ids = frozenset(self.pool.get('stock.location').search(cr, uid, [('usage', '=', 'customer')], context=context))

        list_of_partners = [['name', 'shippment_address', 'email', 'phone_number', 'mobile_phone_number']]
        partner_ids_already_included = set([])

        # Gets those stock moves which were sent to a customer.
        stock_move_ids = self.browse(cr, uid, ids, context)[0].move_ids
        for stock_move_id in stock_move_ids:

            # Only those stock moves which were sent to a customer are considered.
            if stock_move_id.location_dest_id.id in stock_location_customer_ids:

                # Stores the fields of the partner (unless the partner was already included).
                partner_obj = self.pool.get('res.partner').browse(cr, uid, stock_move_id.partner_id.id, context)
                if partner_obj.id not in partner_ids_already_included:
                    partner_ids_already_included.add(partner_obj.id)
                    partner_fields = [partner_obj.name,
                                      partner_obj.get_html_full_address(context=context) or '',
                                      partner_obj.email or '',
                                      partner_obj.phone or '',
                                      partner_obj.mobile or '',
                                      ]
                    list_of_partners.append(partner_fields)

        return list_of_partners

    def action_export_addressees(self, cr, uid, ids, context=None):
        if context is None:
            context = {}

        # Gets the data as a CSV string, which is encoded in base64.
        data = self._get_list_of_customers_who_received_a_lot(cr, uid, ids, context=context)
        data_csv = ''
        for row in data:
            data_csv += ','.join(map(lambda row: str(row).replace(',', ';'), row)) + '\n'
        encoded_data = base64.b64encode(data_csv)

        lot_name = self.browse(cr, uid, ids, context)[0].name
        current_time_str = datetime.datetime.now().strftime('%Y-%m-%d-%H-%M-%S')
        attachment_name = 'customers_with_lot_{0}_report_date_{1}.csv'.format(lot_name, current_time_str)

        ir_attachment_obj = self.pool.get('ir.attachment')
        result = ir_attachment_obj.create(cr, uid, {'name': attachment_name,
                                                    'datas': encoded_data,
                                                    'datas_fname': attachment_name,
                                                    'res_model': 'stock.production.lot',
                                                    'res_id': ids[0],
                                                    'type': 'binary'})
        return result

    def put_apart_illegal_quantities(self, cr, uid, context=None):
        ''' This scheduler 'ensures' that there are not 'illegal' quantities around.

            So,

            1) If a lot is outdated, it empties it.

            2) If it finds a product which has the tracking of lots deactivated
            BUT it does have any lots, then it puts apart those lots.

            3) If it finds a product which has the tracking of lots activated
            BUT it does have quantities which are not tracked, then it puts
            apart that quantity.
        '''
        if context is None:
            context = {}

        product_product_obj = self.pool.get('product.product')
        stock_move_obj = self.pool.get('stock.move')
        project_issue_obj = self.pool.get('project.issue')

        configuration_data = self.pool.get('configuration.data').get(cr, uid, None, context=context)
        datetime_now_str = fields.datetime.now()

        stock_location_ids = self.pool.get('stock.warehouse').get_stock_location_ids(cr, uid, [], context=context)
        if not stock_location_ids:
            warehouse_id = self.pool.get('stock.warehouse').search(cr, uid, [], context=context)[0]
            error_message = _('No Stock Location was found for the warehouse with ID={0}, or there is more than one warehouse.').format(warehouse_id)
            project_issue_obj.create_issue(cr, uid, 'stock.warehouse', warehouse_id, error_message, tags=['inventory'], context=context)
            return True

        scrapping_destination = configuration_data.illegal_lots_destination_id
        if not scrapping_destination:
            warehouse_id = self.pool.get('stock.warehouse').search(cr, uid, [], context=context)[0]
            error_message = _('No Scraping Location was defined on the configuration, to be used when we need to put apart some quantities')
            project_issue_obj.create_issue(cr, uid, 'configuration.data', configuration_data.id, error_message, tags=['inventory'], context=context)
            return True

        # We first remove all the lots which reached the removal date.
        # The removal date is a datetime, but we remove them if they reached the day of today.
        today_date_str = fields.date.today()
        today_datetime_str = datetime.datetime.strptime(today_date_str, DEFAULT_SERVER_DATE_FORMAT).strftime(DEFAULT_SERVER_DATETIME_FORMAT)

        for location_id in stock_location_ids:

            lot_to_be_removed_ids = self.search(cr, uid, [('removal_date', '<', today_datetime_str),
                                                          ('stock_available', '!=', 0.0)], context=context)
            for lot_to_be_removed in self.browse(cr, uid, lot_to_be_removed_ids, context=context):
                cr.execute('''SELECT qty
                              FROM stock_report_prodlots
                              WHERE prodlot_id = %s AND location_id = %s;
                              ''', (lot_to_be_removed.id, location_id))
                qty = 0
                for res in cr.fetchall():
                    qty += res[0]
                stock_move_vals = {
                    'prodlot_id': lot_to_be_removed.id,
                    'product_id': lot_to_be_removed.product_id.id,
                    'product_qty': qty,
                    'product_uom': lot_to_be_removed.product_id.get_base_uom().id,  # Lots qty are always in the reference UOM.
                    'name': 'Lot has passed its removal date, therefore the lot was sent to the scrapping.',
                    'date_expected': datetime_now_str,
                    'location_id': location_id,
                    'location_dest_id': scrapping_destination.id,
                }
                stock_move_id = stock_move_obj.create(cr, uid, stock_move_vals, context=context)
                stock_move_obj.action_done(cr, uid, [stock_move_id], context=context)

            # Finds the products which have the tracking of lots activated.
            lotted_product_ids = product_product_obj.search(cr, uid, [('track_production', '=', True)], context=context)
            for product in product_product_obj.browse(cr, uid, lotted_product_ids, context=context):

                # We compute the amount available for this product on lots...
                cr.execute("""SELECT  qty
                              FROM stock_report_prodlots
                              WHERE location_id = %s AND product_id = %s AND prodlot_id is NULL;""", (location_id, product.id))
                qty_to_scrap = 0
                for res in cr.fetchall():
                    qty_to_scrap += res[0]

                # ...and compare that quantity to the one which is displayed on the product.
                if qty_to_scrap > 0:  # if product.qty_available > qty_on_lots:, since < should never happen.
                    # We have units which are not lotted, so we remove the excess.
                    stock_move_vals = {
                        'product_id': product.id,
                        'product_qty': qty_to_scrap,
                        'product_uom': product.get_base_uom().id,  # Lots qty are always in the reference UOM.
                        'name': 'Product has track_production activated but this quantity is unlotted, therefore was sent to the scrapping.',
                        'date_expected': datetime_now_str,
                        'location_id': location_id,
                        'location_dest_id': scrapping_destination.id,
                    }
                    stock_move_id = stock_move_obj.create(cr, uid, stock_move_vals, context=context)
                    stock_move_obj.action_done(cr, uid, [stock_move_id], context=context)

            # Finds the products which have the tracking of lots deactivated.
            unlotted_product_ids = product_product_obj.search(cr, uid, [('track_production', '=', False)], context=context)
            lots_ids = self.search(cr, uid, [('product_id', 'in', unlotted_product_ids),
                                             ('virtual_available_for_sale', '>', 0),
                                             ], context=context)
            for lot in self.browse(cr, uid, lots_ids, context=context):
                ctx = context.copy()
                ctx['use_stock_location_id'] = location_id
                qty = self._get_virtual_available_for_sale(cr, uid, lot.id, None, None, context=ctx)[lot.id]
                stock_move_vals = {
                    'prodlot_id': lot.id,
                    'product_id': lot.product_id.id,
                    'product_qty': qty,
                    'product_uom': lot.product_id.get_base_uom().id,  # Lots qty are always in the reference UOM.
                    'name': 'Product had no track_production activated, therefore the lot was sent to the scrapping.',
                    'date_expected': datetime_now_str,
                    'location_id': location_id,
                    'location_dest_id': scrapping_destination.id,
                }
                stock_move_id = stock_move_obj.create(cr, uid, stock_move_vals, context=context)
                stock_move_obj.action_done(cr, uid, [stock_move_id], context=context)

        return True

    _columns = {
        'virtual_available_for_sale': fields.function(_get_virtual_available_for_sale,
                                                      type='float',
                                                      string='Virtual Available for Sale',
                                                      help='Quantity available for sale for this lot in the location stock',
                                                      store=False,
                                                      fnct_search=_search_virtual_available_for_sale),
        'virtual_available': fields.function(_get_virtual_available,
                                             type='float',
                                             string='Virtual available',
                                             help='Quantity not assigned to moves',
                                             store=False),
        'production_date': fields.datetime('Production Date',
                                           help='This is the date on which the goods with this Serial Number were produced.'),
    }

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
