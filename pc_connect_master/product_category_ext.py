# b-*- encoding: utf-8 -*-
##############################################################################
#
#    Copyright (c) 2017 brain-tec AG (http://www.braintec-group.com)
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


class product_category_ext(osv.Model):
    _inherit = 'product.category'

    def is_delivery_method_allowed(self, cr, uid, ids, carrier_id,
                                   context=None):
        """ Returns whether the delivery.carrier is listed as one of the
            allowed carriers for the product.category.
        """
        if context is None:
            context = {}
        if not isinstance(ids, list):
            ids = [ids]

        carrier_per_category_obj = \
            self.pool.get('delivery.carrier.product.category')

        for category_id in ids:
            if not carrier_per_category_obj.search(
                    cr, uid, [
                        ('product_category_id', '=', category_id),
                        ('delivery_carrier_id', '=', carrier_id),
                    ], limit=1, count=True, context=context):
                return False

        return True

    def find_alternative_carrier(self, cr, uid, ids, carrier_id, context=None):
        """ Finds an alternative carrier.

            For this, tries to find a match between the list of alternative
            carriers of the provided one that is one of the allowed carriers
            for the product category.
        """
        if context is None:
            context = {}
        if not isinstance(ids, list):
            ids = [ids]

        carrier_obj = self.pool.get('delivery.carrier')

        # Stores all the allowed delivery methods for the product.category.
        prod_categ = self.browse(cr, uid, ids[0], context=context)
        allowed_carrier_ids = []
        for allowed in prod_categ.yc_allowed_delivery_method_ids:
            allowed_carrier_ids.append(allowed.delivery_carrier_id.id)

        # Gets the most prioritaire replacement's ID.
        return carrier_obj.find_alternative_carrier(
            cr, uid, carrier_id, allowed_carrier_ids, context=context)

    _columns = {
        'yc_allowed_delivery_method_ids': fields.one2many(
            'delivery.carrier.product.category',
            'product_category_id',
            'Allowed delivery methods',
            help='This is the list of delivery methods that are allowed for '
                 'sending the products in this category. If it’s empty, all '
                 'delivery methods are allowed. If a product is on a stock '
                 'move of an outgoing picking that uses another than one of '
                 'the allowed delivery methods, then the stock move must be '
                 'moved to a new picking that uses one of the allowed '
                 'delivery methods.'),

        'yc_mandatory_additional_option_ids': fields.many2many(
            'delivery.carrier.yc_option',
            'product_category_delivery_carrier_yc_option_rel',
            'product_category_id', 'delivery_carrier_yc_option_id',
            'Mandatory additional services',
            help='List of mandatory additional services that have to be '
                 'added when sending this category’s products using '
                 'YellowCube / WSBC. An example is LQ which must '
                 'mandatorily be added for dangerous products like '
                 'batteries, oil, pressurized containers, etc.'),
    }

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
