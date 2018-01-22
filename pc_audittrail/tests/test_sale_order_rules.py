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
from base_test import base_test
from openerp.osv import osv, fields
from openerp.tools.translate import _
from openerp.osv import orm
from unittest2 import skipIf


UNDER_DEVELOPMENT = False
UNDER_DEVELOPMENT_TEXT = "Test was skipped because of being under development."


class test_sale_order_rules(base_test):

    model = 'sale.order'

    def setUp(self):
        super(test_sale_order_rules, self).setUp()
        cr, uid, context = self.cr, self.uid, self.context

        self.ir_model_data = self.registry('ir.model.data')
        self.product_product = self.registry('product.product')
        self.product_pricelist = self.registry('product.pricelist')
        self.uom = self.registry('product.uom')

        self.usb_adapter_id = self.ir_model_data.get_object_reference(cr, uid, 'product', 'product_product_48')[1]
        self.datacard_id = self.ir_model_data.get_object_reference(cr, uid, 'product', 'product_product_46')[1]
        self.unit_id = self.ir_model_data.get_object_reference(cr, uid, 'product', 'product_uom_unit')[1]
        self.dozen_id = self.ir_model_data.get_object_reference(cr, uid, 'product', 'product_uom_dozen')[1]

        self.public_pricelist_id = self.ir_model_data.get_object_reference(cr, uid, 'product', 'list0')[1]
        self.sale_pricelist_id = self.product_pricelist.create(cr, uid, {
            'name': 'Sale pricelist',
            'type': 'sale',
            'version_id': [(0, 0, {
                'name': 'v1.0',
                'items_id': [(0, 0, {
                    'name': 'Discount 10%',
                    'base': 1,  # based on public price
                    'price_discount': -0.1,
                    'product_id': self.usb_adapter_id
                }), (0, 0, {
                    'name': 'Discount -0.5',
                    'base': 1,  # based on public price
                    'price_surcharge': -0.5,
                    'product_id': self.datacard_id
                })]
            })]
        }, context=context)

    def tearDown(self):
        super(test_sale_order_rules, self).tearDown()

    def create_element(self, vals):
        vals['partner_id'] = self.ref('base.res_partner_1')
        vals['partner_invoice_id'] = vals['partner_id']
        vals['partner_shipping_id'] = vals['partner_id']
        vals['pricelist_id'] = self.sale_pricelist_id
        return super(test_sale_order_rules, self).create_element(vals)

    @skipIf(UNDER_DEVELOPMENT, UNDER_DEVELOPMENT_TEXT)
    def test(self):
        self._test_check_model_rule()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwid