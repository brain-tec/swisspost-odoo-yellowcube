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
import logging
logger = logging.getLogger(__name__)
from yellowcube_testcase import yellowcube_testcase, subTest
from ..xml_abstract_factory import get_factory
from ..xsd.xml_tools import nspath, create_root, create_element, xml_to_string, schema_namespaces
import unittest2


class test_yc_wbl_wba(yellowcube_testcase):

    def setUp(self):
        super(test_yc_wbl_wba, self).setUp()
        self.test_warehouse.stock_connect_id.write({'yc_enable_wab_file': True, 'yc_enable_war_file': True})
        vals = {
            'name': 'Test supplier',
            'zip': '1234',
            'country_id': self.ref('base.ch'),
        }
        self.supplier_id = self.registry('res.partner').create(self.cr, self.uid, vals, self.context)

    def test_purchase_process(self):
        """
        This test, tests the workflow followed after a sale is closed
        """
        cr, uid, ctx = self.cr, self.uid, self.context
        wbl_factory = get_factory(self.test_warehouse.env, "wbl", context=ctx)

        vals = {
            'name': 'IN_WBL_test',
            'partner_id': self.supplier_id,
            'location_id': self.test_warehouse.lot_input_id.id,
            'pricelist_id': self.ref('purchase.list0'),
        }

        purchase_id = self.purchase_obj.create(cr, uid, vals, ctx)
        vals = {
            'order_id': purchase_id,
            'product_id': self.ref('product.product_product_3'),
            'product_qty': 10,
            'price_unit': 7.65,
            'name': 'Test purchase product',
            'date_planned': '2050-01-01',
        }
        self.registry('purchase.order.line').create(cr, uid, vals, ctx)
        self.purchase_obj.action_picking_create(cr, uid, purchase_id, ctx)
        purchase = self.purchase_obj.browse(cr, uid, purchase_id, ctx)

        # Here we create a WBL file for an order
        wbl_factory.generate_files([('purchase_id', '=', purchase_id)])
        pick_in_id = self.pick_obj.search(cr, uid, [('purchase_id', '=', purchase_id)], context=ctx)[0]
        pick_in = self.pick_obj.browse(cr, uid, pick_in_id, ctx)
        self.assertNotIn(pick_in.state, ['done'], 'The stock.picking is not closed, until everything is delivered')
        name = '.*_wbl_{0}.*IN.*\.xml'.format(purchase.name)
        self.assert_(self._yc_files(name), 'A WBL file is created')

        # Now we check some fields
        result_wbl_file = self._yc_files(name)[-1]
        wbl_node = self._get_file_node(result_wbl_file)
        self._save_node(wbl_node, 'wbl', path='//SupplierOrderNo')
        self.assertEqual(len(pick_in.move_lines), len(nspath(wbl_node, '//Position')),
                         'A position for each item in the SO:\n{0}'.format(xml_to_string(wbl_node)))

        # Here we create the response WBA file, accepting everything
        wba_node = self._create_mirror_wba_from_wbl(wbl_node)
        self._save_node(wba_node, 'wba', path='//wba:SupplierOrderNo')
        wba_factory = get_factory(self.test_warehouse.env, "wba", context=ctx)
        wba_factory.import_file(xml_to_string(wba_node))

        # Now we check the stock.picking state
        pick_in = self.pick_obj.browse(cr, uid, pick_in_id, ctx)
        self.assertIn(pick_in.state, ['done'], 'The stock.picking is closed, once everything is delivered')

    def test_purchase_process_multies(self):
        """
        This test, tests the workflow followed after a sale is closed
        """
        cr, uid, ctx = self.cr, self.uid, self.context
        wbl_factory = get_factory(self.test_warehouse.env, "wbl", context=ctx)

        vals = {
            'partner_id': self.supplier_id,
            'location_id': self.test_warehouse.lot_input_id.id,
            'pricelist_id': self.ref('purchase.list0'),
        }
        purchase_id = self.purchase_obj.create(cr, uid, vals, ctx)
        products = [
            {'id': self.ref('product.product_product_3'),
             'qty': 10},
            {'id': self.ref('product.product_product_3'),
             'qty': 10},
            {'id': self.ref('product.product_product_3'),
             'qty': 10},
        ]
        i = 0
        for p in products:
            i += 1
            vals = {
                'order_id': purchase_id,
                'product_id': p['id'],
                'product_qty': p['qty'],
                'price_unit': 7.65,
                'name': '{0}: Test purchase product #{1}'.format(i, p['id']),
                'date_planned': '2050-01-01',
            }
            self.registry('purchase.order.line').create(cr, uid, vals, ctx)
        purchase = self.purchase_obj.browse(cr, uid, purchase_id, ctx)
        purchase.action_picking_create()
        pick_in_id = self.pick_obj.search(cr, uid, [('purchase_id', '=', purchase_id)], context=ctx)[0]
        pick_in = self.pick_obj.browse(cr, uid, pick_in_id, ctx)
        line_numbers = len(pick_in.move_lines)
        self.assertTrue(line_numbers > 1, 'The example needs multiple lines: {0}'.format(line_numbers))

        # Here we create a WBL file for an order
        wbl_factory.generate_files([('purchase_id', '=', purchase_id)])
        self.assertNotIn(pick_in.state, ['done'], 'The stock.picking is not closed, until everything is delivered')
        name = '.*_wbl_{0}.*IN.*\.xml'.format(purchase.name)
        self.assert_(self._yc_files(name), 'A WBL file is created')
        # Now we check some fields
        result_wbl_file = self._yc_files(name)[-1]
        wbl_node = self._get_file_node(result_wbl_file)
        self._save_node(wbl_node, 'wbl', path='//SupplierOrderNo')
        self.assertEqual(line_numbers, len(nspath(wbl_node, '//Position')),
                         'A position for each item in the SO:\n{0}'.format(xml_to_string(wbl_node)))
        # Here we create the response WBA file, accepting one item at a time
        for line_number in range(1, line_numbers + 1):
            is_end = True if line_number == line_numbers else False
            wba_node = self._create_mirror_wba_from_wbl(wbl_node, partial=line_number, end='1' if is_end else '0')
            self._save_node(wba_node, 'wba', path='//wba:SupplierOrderNo', extra='_posno{0}'.format(line_number))
            wba_factory = get_factory(self.test_warehouse.env, "wba", context=ctx)
            wba_factory.import_file(xml_to_string(wba_node))
            # Now we check the stock.picking state
            pick_in = self.pick_obj.browse(cr, uid, pick_in_id, ctx)
            if is_end:
                self.assertIn(pick_in.state, ['done'], 'The stock.picking is closed, once everything is delivered')
            else:
                self.assertNotIn(pick_in.state, ['done'], 'The stock.picking is not closed, once everything is delivered')
        self.assertIn(pick_in.state, ['done'], 'The stock.picking is closed, once everything is delivered')


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
