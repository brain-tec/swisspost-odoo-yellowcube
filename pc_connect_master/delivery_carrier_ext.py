# b-*- encoding: utf-8 -*-
##############################################################################
#
#    Copyright (c) 2016 brain-tec AG (http://www.braintec-group.com)
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


class delivery_carrier_ext(osv.Model):
    _inherit = 'delivery.carrier'

    def find_alternative_carrier(self, cr, uid, carrier_id,
                                 allowed_carrier_ids, context=None):
        """ Returns, if any, the ID of the alternative carrier associated
            to the current one which is on the list of the allowed carriers.
        """
        if context is None:
            context = {}
        if isinstance(carrier_id, list):
            carrier_id = carrier_id[0]

        carrier_replacement_obj = self.pool.get('delivery.carrier.replacement')

        # Gets the most prioritaire replacement.
        alt_carrier_ids = carrier_replacement_obj.search(cr, uid, [
            ('original_carrier_id', '=', carrier_id),
            ('replacement_carrier_id', 'in', allowed_carrier_ids),
        ], limit=1, order='sequence ASC', context=context)

        # If no replacement was found, it returns False, otherwise the ID.
        alt_carrier_id = False
        if alt_carrier_ids:
            carrier_replacement = carrier_replacement_obj.browse(
                cr, uid, alt_carrier_ids[0], context=context)
            alt_carrier_id = carrier_replacement.replacement_carrier_id.id
        return alt_carrier_id

    _columns = {
        'show_customer_phone_on_picking': fields.boolean('Show Customer Phone Number on the Picking Report',
                                                         help='If checked, the phone of the customer will be shown on the report for the picking.'),
        'show_name_on_picking': fields.boolean('Show Delivery Method on the Picking Report',
                                               help='If checked, the name of the delivery method will be shown on the report for the picking.'),
        'pc_freight_shipping': fields.boolean('Is it used for bulk freight?'),
        'stock_type_id': fields.many2one('stock.type', string='Stock Type'),

        'product_category_ids': fields.one2many(
            'delivery.carrier.product.category',
            'delivery_carrier_id',
            'Product Categories',
            readonly=True,
            help='Product categories having this delivery method as an '
                 'allowed one.'),

        'product_templates_ids': fields.one2many(
            'delivery.carrier.product.template',
            'delivery_carrier_id',
            'Product Templates',
            readonly=True,
            help='Product templates having this delivery method as an '
                 'allowed one.'),

        'carrier_replacement_ids': fields.one2many(
            'delivery.carrier.replacement', 'original_carrier_id',
            'Alternative delivery methods',
            help='If this delivery method is not allowed for a product, '
                 'try these in the following order (top first)'),
    }

    _defaults = {
        'stock_type_id': False,
    }

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
