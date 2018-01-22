# b-*- encoding: utf-8 -*-
##############################################################################
#
#    Copyright (c) 2014 brain-tec AG (http://www.braintec-group.com)
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
from openerp.osv import osv, fields, orm
from openerp.tools.translate import _
from xml_abstract_factory import get_factory
from datetime import datetime, timedelta
from openerp.tools import DEFAULT_SERVER_DATETIME_FORMAT
from openerp.addons.pc_connect_master.utilities.date_utilities import get_number_of_natural_days


class product_product_ext(osv.Model):
    _inherit = 'product.product'

    def write(self, cr, uid, ids, vals, context=None):
        ''' Overwritten to prevent storing a UOM which is different than that indicated
            by the last BAR (if any was indicated).
        '''
        if context is None:
            context = {}
        if not isinstance(ids, list):
            ids = [ids]

        product_uom_obj = self.pool.get('product.uom')

        if 'uom_id' in vals:
            for product in self.browse(cr, uid, ids, context=context):
                if product.yc_bar_uom_id and (vals['uom_id'] != product.yc_bar_uom_id.id):
                    uom_product = product_uom_obj.browse(cr, uid, vals['uom_id'], context=context)
                    uom_last_bar = product_uom_obj.browse(cr, uid, product.yc_bar_uom_id.id, context=context)
                    error_message = _('Unit of Measure {0} (with ID={1}) does not match with '
                                      'that indicated in the last BAR '
                                      '({2}, with ID={3})').format(uom_product.name if uom_product else '?',
                                                                   vals['uom_id'],
                                                                   uom_last_bar.name if uom_last_bar else '?',
                                                                   product.yc_bar_uom_id.id)
                    raise orm.except_orm(_('Error!'), error_message)

        return super(product_product_ext, self).write(cr, uid, ids, vals, context=context)

    def check_xsd_rules(self, cr, uid, ids, context=None):
        cr.execute("SELECT code FROM res_lang WHERE active")
        languages = [x[0] for x in cr.fetchall()]

        for product in self.browse(cr, uid, ids, context=context):
            art_factory = get_factory([self.pool, cr, uid], "art", context=context)
            art_factory._generate_article_element(product, languages, raise_error=True)

        raise osv.except_osv('XSD validation', 'Everything was fine.')
        return True

    def yc_get_missing_bar_products(self, cr, uid, ids, context=None):
        ''' Returns the list of IDs for those products which were not seen in a BAR for the
            amount of days which was indicated in the stock.connect.
        '''
        if context is None:
            context = {}

        ret = []
        now = datetime.now()
        connect_pool = self.pool.get('stock.connect')

        # Gets all those stock.connect which have been set to check for the products which has not appeared in BAR for a certain amount of days.
        # If we have received a stock.connect in the context, we use it.
        connect_ids = context.get('connect_ids')
        if not connect_ids:
            connect_ids = connect_pool.search(cr, uid, [('yc_missing_bar_days_due', '>', '0')], context=context, order='yc_missing_bar_days_due DESC')

        for connect_id in connect_ids:

            # Gets the number of days to check against.
            limit = connect_pool.read(cr, uid, connect_id, ['yc_missing_bar_days_due'], context=context)['yc_missing_bar_days_due'] or 0
            context['yc_missing_bar_days_due'] = limit

            # Searches for those products which were absent in a BAR for the given amount of days.
            config_data = self.pool.get('configuration.data').get(cr, uid, [], context=context)
            actual_weekdays = config_data.get_open_days_support(context=context)
            date_limit = now - timedelta(days=get_number_of_natural_days(now, limit, 'backward', actual_weekdays))
            domain = [('yc_last_bar_update', '<', date_limit.strftime(DEFAULT_SERVER_DATETIME_FORMAT))]
            if ids:
                domain.append(('id', 'in', ids))
            ids = self.search(cr, uid, domain, context=context)

            for product in self.browse(cr, uid, ids, context):
                if product.yc_YCArticleNo and product.qty_available > 0:
                    ret.append(product.id)

        return ret

    def test_requirements_end_of_life_and_deactivated(self, cr, uid, ids, *args):
        ''' Returns true if all the ids fulfill the requirements to pass to
            the states 'end_of_life' or 'deactivated'.
        '''
        success_parent = super(product_product_ext, self).test_requirements_end_of_life_and_deactivated(cr, uid, ids, *args)
        if not ids:
            return success_parent

        errors = []
        context = {}

        # Checks that it did not appeared in the BAR in the last X days (indicated by a system parameter).
        # If not a value is indicated, then it assumes 5 days by default.
        product_missing_in_bar_ids = frozenset(self.yc_get_missing_bar_products(cr, uid, ids, context))
        if not product_missing_in_bar_ids:
            return success_parent
        for product_id in product_missing_in_bar_ids:
            errors.append("Product with ID={0} appeared in a BAR less than {1} days ago.".format(product_id, context['yc_missing_bar_days_due']))

        success = success_parent and (len(errors) == 0)
        return success

    def test_state_in_yc_is_deactivated(self, cr, uid, ids, *args):
        ''' Checks if the product was submitted to YellowCube but its state was set as 'deactivated'.
        '''
        success_parent = super(product_product_ext, self).test_state_in_yc_is_deactivated(cr, uid, ids, *args)

        product = self.browse(cr, uid, ids)[0]
        success = (not product.yc_last_changeflag_submitted) or (product.yc_last_changeflag_submitted == 'D')

        return (success_parent and success)

    def action_draft(self, cr, uid, ids, context=None):
        super(product_product_ext, self).action_draft(cr, uid, ids, context)
        return self.write(cr, uid, ids, {'yc_YCArticleNo': ''}, context)

    def yc_detect_outdated_products(self, cr, uid, ids, context=None, connection_id=None, warehouse_id=None):
        if not warehouse_id or not connection_id:
            # if missing parameters, return no products.
            return []
        if context is None:
            context = {
                'connection_id': connection_id,
                'warehouse_id': warehouse_id,
            }
        connection = self.pool.get('stock.connect').browse(cr, uid, connection_id, context)
        if connection.yc_missing_bar_days_due <= 0:
            # if unset, return none products
            return []

        delta_time = timedelta(days=connection.yc_missing_bar_days_due)
        date_min_update = datetime.now() - delta_time

        file_obj = self.pool.get('stock.connect.file')
        file_ids = file_obj.search(cr,
                                   uid,
                                   [('stock_connect_id', '=', connection_id),
                                    ('type', '=', 'bar'),
                                    ('state', '=', 'done'),
                                    ('write_date', '>', date_min_update),
                                    # Add date filter here
                                    ], context=context)
        if not file_ids:
            # If there was never a BAR file, we don't check anything
            return []
        ok_products = []
        for _file in file_obj.browse(cr, uid, file_ids, context):
            # The field info must provide a list of product ids
            ok_products.extend(eval(_file.info))
        # We check against all the products that where sent sometime into YC
        product_ids = self.search(cr, uid, [('create_date', '<', date_min_update),
                                            ('yc_last_changeflag_submitted_date', 'not in', [False, None, 0])], context=context)
        # We return those products that weren't updated in the last BAR files
        return [x for x in product_ids not in ok_products]

    def get_ean_type(self, cr, uid, ids, context=None):
        """ The ART needs to know the type of EAN sent. This type depends on
            its length:
            - length 8: "HK"
            - length 12: "UC"
            - length 13: "HE"
            - length 14: "UC"

            The constraint on the EAN prevents lengths different that those
            listed ones, thus we don't check for different lengths (the only
            exception being a length of zero, that means no EAN is set).
        """
        if context is None:
            context = {}
        if type(ids) is not list:
            ids = [ids]

        ean_types_depending_on_length = {
            0: '',  # For the case in which we don't have an EAN.
            8: 'HK',
            12: 'UC',
            13: 'HE',
            14: 'UC'
        }
        product = self.browse(cr, uid, ids[0], context=context)
        return ean_types_depending_on_length[len(product.ean13 or '')]

    _columns = {
        'yc_YCArticleNo': fields.char('YCArticleNo', readonly=False),
        'yc_track_outgoing_scan': fields.boolean('Scan Outgoing Lots', help="This is for the ART file of YellowCube"),
        'yc_under_delete_process': fields.boolean('Mark for deletion on YellowCube'),
        'yc_last_changeflag_submitted': fields.char('Last ChangeFlag sent to YellowCube', readonly=False),
        'yc_last_changeflag_submitted_date': fields.date('Last ChangeFlag sent to YellowCube (date)', readonly=False),
        'yc_last_bar_update': fields.datetime('Last time this product appeared in a BAR file',
                                              help='The date stored is the Timestamp of the BAR file.'),
        'yc_bar_uom_id': fields.many2one('product.uom', string='Unit of Measure of last BAR',
                                         help='Stores the last UOM sent with the last BAR', readonly=True)
    }

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: