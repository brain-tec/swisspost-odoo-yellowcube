# b-*- encoding: utf-8 -*-
##############################################################################
#
#    Copyright (c) 2015 brain-tec AG (http://www.brain-tec.ch)
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

from openerp.osv import osv, fields
from openerp.tools.translate import _
from dateutil import relativedelta
import datetime
from configuration_data_ext import _DATE_SELECTION
from openerp.tools import DEFAULT_SERVER_DATETIME_FORMAT
import decimal
from osv.orm import except_orm
import decimal_precision as dp
import logging
logger = logging.getLogger(__name__)


class product_product_ext_lot(osv.Model):
    _inherit = 'product.product'

    def get_base_uom(self, cr, uid, ids, context=None):
        ''' Returns the UOM which is the reference for the UOM
            of this product.

            This method must receive just one ID, or a list with just
            one ID, because all the others will be ignored.
        '''
        if context is None:
            context = {}
        if not isinstance(ids, list):
            ids = [ids]

        uom_obj = self.pool.get('product.uom')

        product = self.browse(cr, uid, ids[0], context=context)
        uom_ids = uom_obj.search(cr, uid, [('category_id', '=', product.uom_id.category_id.id),
                                           ('uom_type', '=', 'reference')],
                                 context=context)

        # If we don't find the UOM is is the base one, we will return False.
        base_uom = False
        if uom_ids:
            base_uom = uom_obj.browse(cr, uid, uom_ids[0], context=context)
        return base_uom

    def get_lots_available(self, cr, uid, ids, context=None):
        ''' Returns the list of stock.production.lots which have a use_date which
            is greater than today, or which is not set, for the current product.
            The result is sorted by 'life_date ASC, use_date ASC, date ASC'
        '''
        if context is None:
            context = {}
        if not isinstance(ids, list):
            ids = ids[0]

        stock_production_lot_obj = self.pool.get('stock.production.lot')

        product = self.browse(cr, uid, ids[0], context=context)

        lot_ids = stock_production_lot_obj.search(cr, uid, [('product_id', '=', product.id),
                                                            '|', ('use_date', '>', fields.datetime.now()),
                                                            ('use_date', '=', False)
                                                            ], order='life_date ASC, use_date ASC, date ASC', context=context)
        lots = stock_production_lot_obj.browse(cr, uid, lot_ids, context=context)

        return lots

    def _get_lot_date(self, cr, uid, product, lot, field, context=None):
        lot_creation_date = lot.production_date and datetime.datetime.strptime(lot.production_date, DEFAULT_SERVER_DATETIME_FORMAT)
        lot_use_date = lot.use_date and datetime.datetime.strptime(lot.use_date, DEFAULT_SERVER_DATETIME_FORMAT)

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
        if date_end is None or date_create is not None and date_create < date_end:
            return date_create
        else:
            return date_end

    def check_product_lot_expiry_dates(self, cr, uid, locations_to_consider=None, context=None):
        ''' Checks the expiration-related dates of all the lots which belong to products,
            only if the name of the location of the lot is within the list 'locations_to_consider'.
        '''
        if context is None:
            context = {}
        if locations_to_consider is None:
            locations_to_consider = []

        product_obj = self.pool.get("product.product")
        lot_obj = self.pool.get("stock.production.lot")
        revision_obj = self.pool.get("stock.production.lot.revision")
        issue_obj = self.pool.get("project.issue")
        product_ids = product_obj.search(cr, uid, [], context=context)
        # (product, lot, message, priority, color -1=ignore
        date_fields = (('alert_time', 'alert_date', _('This product lot is near its removal date'), 4, -1),
                       ('removal_time', 'removal_date', _('Attention: This product lot must be removed from sell'), 3, 3),
                       ('use_time', 'use_date', _('Warning: This product lot must not be used after this date'), 2, 2),
                       ('life_time', 'life_date', _('Danger: This product lot has exceeded its safety life-time!'), 1, 2),
                       )
        lots_under_review = []
        for product in product_obj.browse(cr, uid, product_ids, context=context):
            for prodlot in product.stock_prodlots:
                if (not prodlot.prodlot_id) or (prodlot.qty <= 0) or (prodlot.location_id.location_id.name not in locations_to_consider):
                    continue
                # For any lot under revision, we update the date fields if required
                lot = prodlot.prodlot_id
                lots_under_review.append(lot.id)
                logger.debug("Checking product {0}\tlot {1}".format(product.name, lot.name))
                for field in date_fields:
                    if not getattr(lot, field[1]):
                        date = self._get_lot_date(cr, uid, product, lot, field, context=context)
                        if date and date < datetime.datetime.today():
                            msg = _('Updating lot date {0}, with value {1}, because it has been exceeded').format(field[1], date)
                            # logger.debug(msg)
                            lot_obj.write(cr, uid, lot.id, {field[1]: date.strftime(DEFAULT_SERVER_DATETIME_FORMAT)}, context=context)
                            lot_obj.message_post(cr, uid, lot.id, msg, context=context)
        for lot_id in lots_under_review:
            lot = lot_obj.browse(cr, uid, lot_id, context=context)
            for field in date_fields:
                has_revision = False
                for revision in lot.revisions:
                    if revision.indice == field[1]:
                        has_revision = True
                        break
                if has_revision:
                    continue
                date_field_value = getattr(lot, field[1])
                if not date_field_value:
                    continue
                date = datetime.datetime.strptime(date_field_value, DEFAULT_SERVER_DATETIME_FORMAT)
                if date < datetime.datetime.today():
                    values = {
                        'name': field[2],
                        'description': None,
                        'indice': field[1],
                        'lot_id': lot.id,
                    }
                    revision_obj.create(cr, uid, values, context=context)
                    issue_ids = issue_obj.find_resource_issues(cr, uid, 'stock.production.lot', lot.id, tags=['lot', 'lot-production-date'], create=True, reopen=True, context=context)
                    for issue in issue_obj.browse(cr, uid, issue_ids, context=context):
                        issue.message_post(field[2])
                        if int(issue.priority) > field[3]:
                            issue.write({'priority': str(field[3])})
                            if field[4] >= 0:
                                issue.write({'color': field[4]})

    # The following functions tie the dates of the 'Inventory' tab to the company's system's parameters.
    # Values on the product have precedence over those defined by default.
    def _onchange_times(self, cr, uid, ids, time_field_value, field_odoo, field_uom_odoo, kind, context=None):
        IS_UOM = True
        if not time_field_value:
            # Loads the default time value, and the default unit of measure for that value.
            default_value = self.get_expiration_time_value(cr, uid, kind, not IS_UOM, context)
            default_uom_id = self.get_expiration_time_value(cr, uid, kind, IS_UOM, context)

            # Finds the value stored in the selection corresponding to the value displayed in the selection.
            uom_value_selection = self._expiration_uom_get_selection(cr, uid, default_uom_id, context)

            return {'value': {field_odoo: float(default_value), field_uom_odoo: uom_value_selection}}
        else:
            return {'value': {field_odoo: float(time_field_value)}}

    def onchange_expiration_block_time(self, cr, uid, ids, expiration_block_time, context=None):
        return self._onchange_times(cr, uid, ids, expiration_block_time, 'expiration_block_time', 'expiration_block_time_uom', 'block', context)

    def onchange_expiration_alert_time(self, cr, uid, ids, expiration_alert_time, context=None):
        return self._onchange_times(cr, uid, ids, expiration_alert_time, 'expiration_alert_time', 'expiration_alert_time_uom', 'alert', context)

    def onchange_expiration_accept_time(self, cr, uid, ids, expiration_accept_time, context=None):
        return self._onchange_times(cr, uid, ids, expiration_accept_time, 'expiration_accept_time', 'expiration_accept_time_uom', 'accept', context)

    def onchange_check_decimals(self, cr, uid, ids, value, decimal_accuracy_class, context=None):
        ''' Checks that a given magnitude has its correct number of decimals.
        '''
        if context is None:
            context = {}

        # Gets the number of decimals for this class.
        num_digits, num_digits_fraction = dp.get_precision(decimal_accuracy_class)(cr)

        # Gets the actual number of digits and decimals.
        if value:
            d = decimal.Decimal(str(value))
            d_tuple = d.as_tuple()
            num_digits_actual = len(d_tuple.digits)
            num_digits_fraction_actual = abs(d_tuple.exponent)

            # Checks.
            if (num_digits_actual > num_digits) or (num_digits_fraction_actual > num_digits_fraction):
                return {'warning': {'title': _('Bad number of digits'),
                                    'message': _('The field should have {0} digits, {1} of them being the fractional part.').format(num_digits, num_digits_fraction)}
                        }

        return {'value': {'value': value}}

    def get_expiration_time_value(self, cr, uid, kind, is_uom=False, context=None):
        if is_uom:
            key = 'post_default_expiration_{0}_time_uom'.format(kind)
        else:
            key = 'post_default_expiration_{0}_time'.format(kind)

        value = self.pool.get('configuration.data').get(cr, uid, [], context=context)[key]
        if not is_uom:
            # If not is_uom then we don't query the UOM but the value associated to it...
            return value
        else:
            # If it's a UOM then we get the value to be stored in the selection field.
            uom_value_selection = self._expiration_uom_get_selection(cr, uid, value, context)  # Returns None if not found.
            return uom_value_selection

    def _expiration_uom(self, cr, uid, tuples=True, uom='days', value=0, context=None):
        ret = []
        for f in _DATE_SELECTION:
            if tuples:
                ret.append(f)
            elif f[0] == uom:
                args = {uom: value * -1}
                return relativedelta.relativedelta(**args)
        return ret

    def _expiration_uom_get_selection(self, cr, uid, value_to_search, context):
        ''' Given a value displayed in a selection field, it returns the value stored in the selection, or None if it was not found.
        '''
        uom_allowed_values = self._expiration_uom(cr, uid, context=context)
        uom_value_selection = None
        for uom_allowed_value in uom_allowed_values:
            uom_value_displayed = uom_allowed_value[1]
            if uom_value_displayed == value_to_search:
                uom_value_selection = uom_allowed_value[0]
                break
        return uom_value_selection

    def _compute_packing(self, cr, uid, ids, field_name, arg, context=None):
        ''' Computes the 'packing' for a product.
            The packing is the multiplication of product's lenght X width X height X weight.
        '''
        if context is None:
            context = {}
        res = {}
        for product in self.browse(cr, uid, ids, context=context):
            res[product.id] = product.length * product.width * product.height * product.weight
        return res

    def _virtual_stock_calculation(self, cr, uid, ids, field, arg, context=None):
        ''' Calculates the several measures which are used to keep track of the quantity which is available.
        '''
        if context is None:
            context = {}

        ret = {}

        product_uom_obj = self.pool.get('product.uom')

        for product in self.browse(cr, uid, ids, context=context):

            qty_on_reservation_quotations = 0
            for reservation in product.draft_sale_order_lines:
                # The lines in the sale.order store the quantity in the UOM indicated
                # by the sale.order. But the Quantity on Hand and all the other fields
                # related to quantities which are shown on the product's form are in the
                # unit of measure of the product. Thus, we must convert it to that UOM.
                qty_product_uom = product_uom_obj._compute_qty(cr, uid, reservation.product_uom.id, reservation.product_uom_qty, product.uom_id.id)
                qty_on_reservation_quotations += qty_product_uom

            ret[product.id] = {
                'product_reservation_qty': qty_on_reservation_quotations,
                'qty_on_sale': product.qty_available - qty_on_reservation_quotations - abs(product.outgoing_qty),
            }

        return ret

    def _get_last_inventory(self, cr, uid, ids, field, arg=None, context=None):
        res = {}
        line_obj = self.pool.get('stock.inventory.line')
        for _id in ids:
            res[_id] = False
            for line_id in line_obj.search(cr, uid, [('product_id', '=', _id), ('state', '=', 'done')], order='inventory_id DESC', limit=1):
                res[_id] = line_obj.read(cr, uid, line_id, ['inventory_id'], context=context)['inventory_id']
        return res

    _columns = {
        # Expiration dates for the warehouse process.
        'expiration_block_time': fields.float('Expiration Block Time', required=True),
        'expiration_block_time_uom': fields.selection(_expiration_uom,
                                                      string='Unit of Measure for the Expiration Block Time',
                                                      required=False),
        'expiration_alert_time': fields.float('Expiration Alert Time', required=True),
        'expiration_alert_time_uom': fields.selection(_expiration_uom,
                                                      string='Unit of Measure for the Expiration Alert Time', required=False),
        'expiration_accept_time': fields.float('Expiration Accept Time', required=True),
        'expiration_accept_time_uom': fields.selection(_expiration_uom,
                                                       string='Unit of Measure for the Expiration Accept Time', required=False),

        # Attributes related to the features a product can have.
        'weight': fields.float("Weight", digits_compute=dp.get_precision('Stock Weight')),
        'length': fields.float('Length', digits_compute=dp.get_precision('Stock Length'), help='Length of the product (in centimeters)'),
        'width': fields.float('Width', digits_compute=dp.get_precision('Stock Width'), help='Width of the product (in centimeters)'),
        'height': fields.float('Height', digits_compute=dp.get_precision('Stock Height'), help='Height of the product (in centimeters)'),
        'diameter': fields.float('Diameter', digits_compute=dp.get_precision('Stock Diameter'), help='Diameter of the product (in centimeters)'),
        'packing': fields.function(_compute_packing, string='Packing', readonly=True, digits_compute=dp.get_precision('Stock Packing'),
                                   store={'product.product': (lambda self, cr, uid, ids, context: ids,
                                                              ['length', 'width', 'height', 'weight'], 10)},
                                   help='Length x Width x Height x Weight (gross, not net)'),
        'brand': fields.char('Brand', help='The brand of the product'),
        'manufacturer_website': fields.char('Manufacturer\'s Website', help='Link to the manufacturer\'s web site.'),

        'stock_prodlots': fields.one2many('stock.report.prodlots', 'product_id', string='Stock report by serial number', readonly=True),
        'last_inventory_id': fields.function(_get_last_inventory, string="Last inventory", type='many2one', relation='stock.inventory', store=False),

        'product_reservation_qty': fields.function(_virtual_stock_calculation, type="float", string="Reservations (on Quotations)", readonly=True,
                                                   multi='_virtual_stock_calculation',
                                                   help='It shows the amount which is on sale.order lines which are in state draft, thus corresponding to '
                                                        'quotations which are in state draft. This is useful to keep track of units which are not available '
                                                        'because of having been reserved for an order from the shop, for example.'),
        'qty_on_sale': fields.function(_virtual_stock_calculation, type="float", string="Quantity Available", readonly=True,
                                       multi='_virtual_stock_calculation',
                                       help="It is computed as 'Quantity On Hand' - 'Reservations (on Quotations)' - 'Outgoing'."),

        'draft_sale_order_lines': fields.one2many('sale.order.line', 'product_id', domain=[('state', 'in', ['draft'])], string='Appearance in quotations', readonly=True),

        'webshop_state': fields.selection([('', '<not active>'),
                                           ('on_sale', 'On Sale'),
                                           ('visible', 'Not on sale, but visible'),
                                           ('not_visible', 'Not visible'),
                                           ('not_visible_conditional', 'Not visible if quantity is 0')],
                                          'Webshop State',
                                          help='The possible states for a product in a webshop.'),

        # The following variable (target_state) was extracted from the
        # original product's life-cycle: It was found that not all the clients
        # needed nor wanted that module, but anyway those variables were still needed
        # by some of the other modules they did need; thus they was placed here
        # in the very-top module of the connector.
        'target_state': fields.selection([('inactive', 'Inactive'),
                                          ('active', 'Active')], string="Target State", required=True),
    }

    _defaults = {
        'target_state': 'inactive',
        'weight': 0.00,

        'expiration_block_time': lambda self, cr, uid, context: self.get_expiration_time_value(cr, uid, 'block', context=context),
        'expiration_block_time_uom': lambda self, cr, uid, context: self.get_expiration_time_value(cr, uid, 'block', True, context),
        'expiration_alert_time': lambda self, cr, uid, context: self.get_expiration_time_value(cr, uid, 'alert', context=context),
        'expiration_alert_time_uom': lambda self, cr, uid, context: self.get_expiration_time_value(cr, uid, 'alert', True, context),
        'expiration_accept_time': lambda self, cr, uid, context: self.get_expiration_time_value(cr, uid, 'accept', context=context),
        'expiration_accept_time_uom': lambda self, cr, uid, context: self.get_expiration_time_value(cr, uid, 'accept', True, context),
    }

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
