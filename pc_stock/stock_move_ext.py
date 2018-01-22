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
###############################################################################

from openerp.osv import osv, fields
from openerp import netsvc
from openerp.addons.pc_generics import generics


class stock_move_ext(osv.osv):
    _inherit = 'stock.move'

    def get_result(self, cr, uid, ids, context=None):
        if context is None:
            context = {}

        os_objects = self.browse(cr, uid, ids, context)
        os_object = os_objects[0]

        quantity = str(os_object.product_qty)
        quantity = int(quantity.split(".")[0])

        try:
            elements = os_object.product_uom.name.split(" ")

            if len(elements) == 1:
                return "{0} {1}".format(quantity, elements)
            else:
                ammount = float(elements[0]) * quantity
                ammount = str(ammount)
                ammount = int(ammount.split(".")[0])
                return "{0} {1}".format(ammount, elements[1])
        except:
            return quantity

    def get_ammount_result(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        os_objects = self.browse(cr, uid, ids, context)
        os_object = os_objects[0]
        result = os_object.get_result()
        return result.split(" ")[0]

    def get_serial_number(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        os_objects = self.browse(cr, uid, ids, context)
        object_line = os_objects[0]

        serial_number = object_line.product_id and object_line.product_id.default_code or ''
        return serial_number

    def get_description(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        os_objects = self.browse(cr, uid, ids, context)
        object_line = os_objects[0]

        description = object_line.product_id and object_line.product_id.name or ''
        return description

    def get_item_price(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        os_objects = self.browse(cr, uid, ids, context)
        object_line = os_objects[0]

        item_price = object_line.sale_line_id and object_line.sale_line_id.price_unit or ''
        #item_price = object_line.product_id and \
        #    object_line.product_id.price_get('list_price', context=context)[object_line.product_id.id] or ''
        return item_price

    def get_discount(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        os_objects = self.browse(cr, uid, ids, context)
        object_line = os_objects[0]

        discount = object_line.sale_line_id and object_line.sale_line_id.discount or 0.0
        return discount

    def get_tax_code(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        os_objects = self.browse(cr, uid, ids, context)
        object_line = os_objects[0]

        tax_code = object_line.sale_line_id.tax_id[0].description
        return tax_code

    def get_tax_description(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        os_objects = self.browse(cr, uid, ids, context)
        object_line = os_objects[0]

        tax_description = object_line.sale_line_id.tax_id[0].name
        return tax_description

    def get_tax_amount(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        os_objects = self.browse(cr, uid, ids, context)
        object_line = os_objects[0]

        tax_amount = object_line.sale_line_id.tax_id[0].amount * 100.0
        return tax_amount
