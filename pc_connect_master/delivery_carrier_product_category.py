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
from utilities.db import create_db_index
from lxml import etree


class delivery_carrier_product_category(osv.Model):
    """ Lists the possible delivery carriers for a given product category.
    """
    _name = 'delivery.carrier.product.category'

    def init(self, cr):
        create_db_index(
            cr, 'delivery_carrier_product_category_all_index',
            'delivery_carrier_product_category',
            'product_category_id, delivery_carrier_id')

    def fields_view_get(self, cr, uid, view_id=None, view_type=False,
                        context=None, toolbar=False, submenu=False):
        """ We hide the field for the delivery.carrier or the product.category
            depending on a flag on the view. This is to avoid hardcoding
            the tree view inside the views which contain it.
        """
        if context is None:
            context = {}

        res = super(delivery_carrier_product_category, self).fields_view_get(
            cr, uid, view_id=view_id, view_type=view_type,
            context=context, toolbar=toolbar, submenu=submenu)

        doc = etree.XML(res['arch'])

        if view_type == 'tree':
            if context.get('from_delivery_carrier'):
                for node in doc.xpath("//field[@name='delivery_carrier_id']"):
                    doc.remove(node)

            if context.get('from_product_category'):
                for node in doc.xpath("//field[@name='product_category_id']"):
                    doc.remove(node)

        res['arch'] = etree.tostring(doc)
        return res

    _columns = {
        'sequence': fields.integer(
            'Sequence', help='Sequence for reordering.'),
        'product_category_id': fields.many2one(
            'product.category', 'Product Category', required=True,
            select=True),
        'delivery_carrier_id': fields.many2one(
            'delivery.carrier', 'Delivery Method', required=True,
            select=True),
    }

    _defaults = {
        'sequence': lambda *a: 1,
    }

    _order = 'sequence ASC'

    _sql_constraints = [
        ('Allowed delivery methods can not be duplicated',
         'unique (product_category_id,delivery_carrier_id)',
         'A product category can not have allowed delivery methods '
         'which are duplicated.'),
    ]

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
