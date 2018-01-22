# b-*- encoding: utf-8 -*-
##############################################################################
#
#    Copyright (c) 2015 brain-tec AG (http://www.braintec-group.com)
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
import time
from yellowcube_testcase import yellowcube_testcase
from ..xml_abstract_factory import get_factory
from ..xsd.xml_tools import _XmlTools as xml_tools
from unittest2 import skipIf


UNDER_DEVELOPMENT = False
UNDER_DEVELOPMENT_TEXT = "Test was skipped because of being under development."


class test_yc_wbl_wba(yellowcube_testcase):

    def setUp(self):
        super(test_yc_wbl_wba, self).setUp()
        self.test_warehouse.stock_connect_id.write({
            'yc_enable_wbl_file': True,
            'yc_enable_wba_file': True,
            'yc_wba_invoice_on_import': True,
        })

        vals = {
            'name': 'Test supplier',
            'zip': '12345',
        }
        self.supplier_id = self.registry('res.partner').create(self.cr, self.uid, vals, self.context)

    def _save_wba(self, wba_root, wba_file_name):
        cr, uid, ctx = self.cr, self.uid, self.context
        vals = {
            'input': True,
            'content': xml_tools.xml_to_string(wba_root, encoding='unicode',
                                               xml_declaration=False),
            'name': wba_file_name,
            'stock_connect_id': self.test_warehouse.stock_connect_id.id,
            'type': 'wba',
            'warehouse_id': self.test_warehouse.id,
        }
        stock_connect_file_id = \
            self.stock_connect_file.create(cr, uid, vals, context=ctx)
        return stock_connect_file_id

    @skipIf(UNDER_DEVELOPMENT, UNDER_DEVELOPMENT_TEXT)
    def test_ean_deactivated(self):
        """ Thea EANs are deactivated, so it doesn't matter if the EAN set in
            the WBA is not correct.
        """
        cr, uid, ctx = self.cr, self.uid, self.context
        wbl_factory = get_factory([self.test_warehouse.pool, cr, uid], "wbl",
                                  context=ctx)

        # Deactivates the EANs for the stock.connect.files.
        self.test_warehouse.stock_connect_id.write({'yc_ignore_ean': True})

        vals = {
            'name': 'IN_WBL_test',
            'partner_id': self.supplier_id,
            'location_id': self.test_warehouse.lot_input_id.id,
            'pricelist_id': self.ref('purchase.list0'),
            'invoice_method': 'picking',
        }
        purchase_id = self.purchase_obj.create(cr, uid, vals, ctx)
        purchase = self.purchase_obj.browse(cr, uid, purchase_id, ctx)
        vals = {
            'order_id': purchase_id,
            'product_id': self.ref('product.product_product_3'),
            'product_qty': 10,
            'price_unit': 7.65,
            'name': 'Test purchase product',
            'date_planned': '2050-01-01',
            'yc_posno': 99,
        }
        self.registry('purchase.order.line').create(cr, uid, vals, ctx)
        purchase.wkf_confirm_order()
        purchase.action_picking_create()
        purchase = purchase.browse()[0]
        self.assertListEqual(purchase.invoice_ids, [])

        # Here we create a WBL file for an order
        wbl_factory.generate_files([('purchase_id', '=', purchase_id)])
        pick_in_id = \
            self.pick_obj.search(cr, uid, [('purchase_id', '=', purchase_id)],
                                 context=ctx)[0]
        pick_in = self.pick_obj.browse(cr, uid, pick_in_id, ctx)
        self.assertNotIn(pick_in.state, ['done'],
                         'The stock.picking is not closed, '
                         'until everything is delivered')
        name = '.*_wbl_{0}.*IN.*\.xml'.format(purchase.name)
        self.assert_(self._yc_files(name), 'A WBL file is created')

        # Now we check some fields
        result_wbl_file = self._yc_files(name)[-1]
        wbl_node = self._get_file_node(result_wbl_file)
        self._save_node(wbl_node, 'wbl', path='//SupplierOrderNo')
        self.assertEqual(len(pick_in.move_lines),
                         len(xml_tools.nspath(wbl_node, '//Position')),
                         'A position for each item in the SO:\n{0}'.format(
                             xml_tools.xml_to_string(wbl_node)))

        # Here we create the response WBA file with a wrong EAN.
        wba_node = self._create_mirror_wba_from_wbl(wbl_node, ean='123')
        self._save_node(wba_node, 'wba', path='//wba:SupplierOrderNo')
        wba_factory = get_factory([self.test_warehouse.pool, cr, uid], "wba",
                                  context=ctx)

        # We save the WBA.
        wba_file_name = 'WBA_{0}.xml'.format(time.time())
        wba_connect_file_id = self._save_wba(wba_node, wba_file_name)

        # We check that the WBA has the EAN.
        wba_connect_file = self.stock_connect_file.browse(
            cr, uid, wba_connect_file_id, context=ctx)
        self.assertTrue('<wba:EAN>123</wba:EAN>'
                        in wba_connect_file.content)

        # We import the WBA file without errors.
        self.test_warehouse.stock_connect_id.connection_process_files()
        wba_connect_file = self.stock_connect_file.browse(
            cr, uid, wba_connect_file_id, context=ctx)
        self.assertFalse(wba_connect_file.error)
        self.assertFalse(wba_connect_file.info)
        self.assertEqual(wba_connect_file.state, 'done')

    @skipIf(UNDER_DEVELOPMENT, UNDER_DEVELOPMENT_TEXT)
    def test_ean_activated_ean_matches_with_product(self):
        """ The EANs are activated, and the one provided with the WBA
            matches with that of the product.
        """
        cr, uid, ctx = self.cr, self.uid, self.context
        wbl_factory = get_factory([self.test_warehouse.pool, cr, uid], "wbl",
                                  context=ctx)

        # Activates the EANs for the stock.connect.files.
        self.test_warehouse.stock_connect_id.write({'yc_ignore_ean': False})

        # Sets the EAN on the product.
        ean = '7611330002706'
        product_id = self.ref('product.product_product_3')
        self.product_obj.write(cr, uid, product_id,
                               {'ean13': ean}, context=ctx)

        vals = {
            'name': 'IN_WBL_test',
            'partner_id': self.supplier_id,
            'location_id': self.test_warehouse.lot_input_id.id,
            'pricelist_id': self.ref('purchase.list0'),
            'invoice_method': 'picking',
        }
        purchase_id = self.purchase_obj.create(cr, uid, vals, ctx)
        purchase = self.purchase_obj.browse(cr, uid, purchase_id, ctx)
        vals = {
            'order_id': purchase_id,
            'product_id': self.ref('product.product_product_3'),
            'product_qty': 10,
            'price_unit': 7.65,
            'name': 'Test purchase product',
            'date_planned': '2050-01-01',
            'yc_posno': 99,
        }
        self.registry('purchase.order.line').create(cr, uid, vals, ctx)
        purchase.wkf_confirm_order()
        purchase.action_picking_create()
        purchase = purchase.browse()[0]
        self.assertListEqual(purchase.invoice_ids, [])

        # Here we create a WBL file for an order
        wbl_factory.generate_files([('purchase_id', '=', purchase_id)])
        pick_in_id = \
            self.pick_obj.search(cr, uid, [('purchase_id', '=', purchase_id)],
                                 context=ctx)[0]
        pick_in = self.pick_obj.browse(cr, uid, pick_in_id, ctx)
        self.assertNotIn(pick_in.state, ['done'],
                         'The stock.picking is not closed, '
                         'until everything is delivered')
        name = '.*_wbl_{0}.*IN.*\.xml'.format(purchase.name)
        self.assert_(self._yc_files(name), 'A WBL file is created')

        # Now we check some fields
        result_wbl_file = self._yc_files(name)[-1]
        wbl_node = self._get_file_node(result_wbl_file)
        self._save_node(wbl_node, 'wbl', path='//SupplierOrderNo')
        self.assertEqual(len(pick_in.move_lines),
                         len(xml_tools.nspath(wbl_node, '//Position')),
                         'A position for each item in the SO:\n{0}'.format(
                             xml_tools.xml_to_string(wbl_node)))

        # Here we create the response WBA file with a wrong EAN.
        wba_node = self._create_mirror_wba_from_wbl(wbl_node, ean=ean)
        self._save_node(wba_node, 'wba', path='//wba:SupplierOrderNo')
        wba_factory = get_factory([self.test_warehouse.pool, cr, uid], "wba",
                                  context=ctx)

        # We save the WBA.
        wba_file_name = 'WBA_{0}.xml'.format(time.time())
        wba_connect_file_id = self._save_wba(wba_node, wba_file_name)

        # We check that the WBA has the EAN.
        wba_connect_file = self.stock_connect_file.browse(
            cr, uid, wba_connect_file_id, context=ctx)
        self.assertTrue('<wba:EAN>{0}</wba:EAN>'.format(ean)
                        in wba_connect_file.content)

        # We import the WBA file without errors.
        self.test_warehouse.stock_connect_id.connection_process_files()
        wba_connect_file = self.stock_connect_file.browse(
            cr, uid, wba_connect_file_id, context=ctx)
        self.assertFalse(wba_connect_file.error)
        self.assertFalse(wba_connect_file.info)
        self.assertEqual(wba_connect_file.state, 'done')

    @skipIf(UNDER_DEVELOPMENT, UNDER_DEVELOPMENT_TEXT)
    def test_ean_activated_ean_does_not_match_with_product(self):
        """ The EANs are activated, ant the one provided with the WBA does
            not match with that of the product.
        """
        cr, uid, ctx = self.cr, self.uid, self.context
        wbl_factory = get_factory([self.test_warehouse.pool, cr, uid], "wbl",
                                  context=ctx)

        # Activates the EANs for the stock.connect.files.
        self.test_warehouse.stock_connect_id.write({'yc_ignore_ean': False})

        # Sets the EAN on the product.
        ean1 = '7611330002706'
        ean2 = '7611330002874'
        product_id = self.ref('product.product_product_3')
        self.product_obj.write(cr, uid, product_id,
                               {'ean13': ean1}, context=ctx)

        vals = {
            'name': 'IN_WBL_test',
            'partner_id': self.supplier_id,
            'location_id': self.test_warehouse.lot_input_id.id,
            'pricelist_id': self.ref('purchase.list0'),
            'invoice_method': 'picking',
        }
        purchase_id = self.purchase_obj.create(cr, uid, vals, ctx)
        purchase = self.purchase_obj.browse(cr, uid, purchase_id, ctx)
        vals = {
            'order_id': purchase_id,
            'product_id': self.ref('product.product_product_3'),
            'product_qty': 10,
            'price_unit': 7.65,
            'name': 'Test purchase product',
            'date_planned': '2050-01-01',
            'yc_posno': 99,
        }
        self.registry('purchase.order.line').create(cr, uid, vals, ctx)
        purchase.wkf_confirm_order()
        purchase.action_picking_create()
        purchase = purchase.browse()[0]
        self.assertListEqual(purchase.invoice_ids, [])

        # Here we create a WBL file for an order
        wbl_factory.generate_files([('purchase_id', '=', purchase_id)])
        pick_in_id = \
            self.pick_obj.search(cr, uid, [('purchase_id', '=', purchase_id)],
                                 context=ctx)[0]
        pick_in = self.pick_obj.browse(cr, uid, pick_in_id, ctx)
        self.assertNotIn(pick_in.state, ['done'],
                         'The stock.picking is not closed, '
                         'until everything is delivered')
        name = '.*_wbl_{0}.*IN.*\.xml'.format(purchase.name)
        self.assert_(self._yc_files(name), 'A WBL file is created')

        # Now we check some fields
        result_wbl_file = self._yc_files(name)[-1]
        wbl_node = self._get_file_node(result_wbl_file)
        self._save_node(wbl_node, 'wbl', path='//SupplierOrderNo')
        self.assertEqual(len(pick_in.move_lines),
                         len(xml_tools.nspath(wbl_node, '//Position')),
                         'A position for each item in the SO:\n{0}'.format(
                             xml_tools.xml_to_string(wbl_node)))

        # Here we create the response WBA file with a wrong EAN.
        wba_node = self._create_mirror_wba_from_wbl(wbl_node, ean=ean2)
        self._save_node(wba_node, 'wba', path='//wba:SupplierOrderNo')
        wba_factory = get_factory([self.test_warehouse.pool, cr, uid], "wba",
                                  context=ctx)

        # We save the WBA.
        wba_file_name = 'WBA_{0}.xml'.format(time.time())
        wba_connect_file_id = self._save_wba(wba_node, wba_file_name)

        # We check that the WBA has the EAN.
        wba_connect_file = self.stock_connect_file.browse(
            cr, uid, wba_connect_file_id, context=ctx)
        self.assertTrue('<wba:EAN>{0}</wba:EAN>'.format(ean2)
                        in wba_connect_file.content)

        # We import the WBA file with errors.
        self.test_warehouse.stock_connect_id.connection_process_files()
        wba_connect_file = self.stock_connect_file.browse(
            cr, uid, wba_connect_file_id, context=ctx)
        self.assertTrue(wba_connect_file.error)
        self.assertTrue(wba_connect_file.info)
        self.assertEqual(wba_connect_file.state, 'draft')

    @skipIf(UNDER_DEVELOPMENT, UNDER_DEVELOPMENT_TEXT)
    def test_wba_with_2_lots_complete(self):
        """ The WBA sends 2 lots on a product which needs to track lots.
        """
        cr, uid, ctx = self.cr, self.uid, self.context
        wbl_factory = get_factory([self.test_warehouse.pool, cr, uid], "wbl",
                                  context=ctx)

        # Makes sure the product doesn't have the lotting active.
        product_id = self.ref('product.product_product_3')
        self.check_product_lotted(product_id, lotted=False)

        # Creates the purchase from which to create the WBL.
        vals = {
            'name': 'IN_WBL_test',
            'partner_id': self.supplier_id,
            'location_id': self.test_warehouse.lot_input_id.id,
            'warehouse_id': self.test_warehouse.id,
            'pricelist_id': self.ref('purchase.list0'),
            'invoice_method': 'picking',
        }
        purchase_id = self.purchase_obj.create(cr, uid, vals, ctx)
        purchase = self.purchase_obj.browse(cr, uid, purchase_id, ctx)
        vals = {
            'order_id': purchase_id,
            'product_id': self.ref('product.product_product_3'),
            'product_qty': 10,
            'price_unit': 7.65,
            'name': 'Test purchase product',
            'date_planned': '2050-01-01',
            'yc_posno': 99,
        }
        self.registry('purchase.order.line').create(cr, uid, vals, ctx)
        purchase.wkf_confirm_order()
        purchase.action_picking_create()
        purchase = purchase.browse()[0]
        self.assertListEqual(purchase.invoice_ids, [])

        # Here we create a WBL file for an order
        wbl_factory.generate_files([('purchase_id', '=', purchase_id)])
        pick_in_id = \
            self.pick_obj.search(cr, uid, [('purchase_id', '=', purchase_id)],
                                 context=ctx)[0]
        pick_in = self.pick_obj.browse(cr, uid, pick_in_id, ctx)
        self.assertNotIn(pick_in.state, ['done'],
                         'The stock.picking is not closed, '
                         'until everything is delivered')
        name = '.*_wbl_{0}.*IN.*\.xml'.format(purchase.name)
        self.assert_(self._yc_files(name), 'A WBL file is created')

        # Now we check some fields
        result_wbl_file = self._yc_files(name)[-1]
        wbl_node = self._get_file_node(result_wbl_file)
        self._save_node(wbl_node, 'wbl', path='//SupplierOrderNo')
        self.assertEqual(len(pick_in.move_lines),
                         len(xml_tools.nspath(wbl_node, '//Position')),
                         'A position for each item in the SO:\n{0}'.format(
                             xml_tools.xml_to_string(wbl_node)))

        # Here we create the response WBA file with the two lots
        # for the product, with different quantities.
        lot_1 = self.create_lot('LOT1_prod{0}'.format(product_id),
                                product_id, 7)
        lot_2 = self.create_lot('LOT2_prod{0}'.format(product_id),
                                product_id, 3)
        for lot in [lot_1, lot_2]:
            if lot == lot_1:
                yc_eod = '0'
            else:
                yc_eod = '1'
            wba_node = self._create_mirror_wba_from_wbl(
                wbl_node, qty=lot.virtual_available_for_sale, lot=lot,
                end=yc_eod)
            self._save_node(wba_node, 'wba', path='//wba:SupplierOrderNo')

            # We save the WBA.
            wba_file_name = 'WBA_{0}.xml'.format(time.time())
            wba_connect_file_id = self._save_wba(wba_node, wba_file_name)

            # We check that the WBA has the Lot.
            wba_connect_file = self.stock_connect_file.browse(
                cr, uid, wba_connect_file_id, context=ctx)
            self.assertTrue('<wba:Lot>{0}</wba:Lot>'.format(lot.name)
                            in wba_connect_file.content)

            # We import the WBA file without errors.
            self.test_warehouse.stock_connect_id.connection_process_files()
            wba_connect_file = self.stock_connect_file.browse(
                cr, uid, wba_connect_file_id, context=ctx)
            self.assertFalse(wba_connect_file.error)
            self.assertFalse(wba_connect_file.info)
            self.assertEqual(wba_connect_file.state, 'done')

            # The product must be set as lotted.
            self.check_product_lotted(product_id, lotted=True)

            # If the first WBA has been processed, then there is a line
            # without lot. If the second WBA has been processed, then
            # both lines have a lot.
            pick_in = self.pick_obj.browse(cr, uid, pick_in_id, ctx)
            moves = {}
            for move in pick_in.move_lines:
                moves[move.product_qty] = \
                    move.prodlot_id and move.prodlot_id.id or False
            self.assertEqual(len(moves), 2,
                             "2 moves were expected on the picking.in")
            if lot == lot_1:
                self.assertEqual(moves[7], lot_1.id, "Bad lot for 1st WBA")
                self.assertFalse(moves[3], "Bad lot for 1st WBA")
            else:  # if lot == lot_2:
                self.assertEqual(moves[7], lot_1.id, "Bad lot for 2nd WBA.")
                self.assertEqual(moves[3], lot_2.id, "Bad lot for 2nd WBA.")

        # We attempt to confirm the picking by the WBA.
        self.assertEqual(pick_in.state, 'assigned')
        self.test_warehouse.stock_connect_id.write({'yc_wba_confirm_time': 0})
        self.registry('stock.connect.yellowcube')._confirm_pickings_by_wba(
            cr, uid, self.test_warehouse.stock_connect_id.id, ctx)
        pick_in = self.pick_obj.browse(cr, uid, pick_in_id, ctx)
        self.assertEqual(pick_in.state, 'done')

    def check_product_lotted(self, product_id, lotted):
        cr, uid, ctx = self.cr, self.uid, self.context
        product = self.product_obj.browse(cr, uid, product_id, context=ctx)
        if lotted:
            self.assertTrue(product.track_production)
            self.assertTrue(product.track_incoming)
            self.assertTrue(product.track_outgoing)
        else:
            self.assertFalse(product.track_production)
            self.assertFalse(product.track_incoming)
            self.assertFalse(product.track_outgoing)

    @skipIf(UNDER_DEVELOPMENT, UNDER_DEVELOPMENT_TEXT)
    def test_wba_with_1_lot_complete(self):
        """ The WBA sends a lot on a product which needs to track lots.
        """
        cr, uid, ctx = self.cr, self.uid, self.context
        wbl_factory = get_factory([self.test_warehouse.pool, cr, uid], "wbl",
                                  context=ctx)

        # Makes sure the product doesn't have the lotting active.
        product_id = self.ref('product.product_product_3')
        self.check_product_lotted(product_id, lotted=False)

        # Creates the purchase from which to create the WBL.
        vals = {
            'name': 'IN_WBL_test',
            'partner_id': self.supplier_id,
            'warehouse_id': self.test_warehouse.id,
            'location_id': self.test_warehouse.lot_input_id.id,
            'pricelist_id': self.ref('purchase.list0'),
            'invoice_method': 'picking',
        }
        purchase_id = self.purchase_obj.create(cr, uid, vals, ctx)
        purchase = self.purchase_obj.browse(cr, uid, purchase_id, ctx)
        vals = {
            'order_id': purchase_id,
            'product_id': self.ref('product.product_product_3'),
            'product_qty': 10,
            'price_unit': 7.65,
            'name': 'Test purchase product',
            'date_planned': '2050-01-01',
            'yc_posno': 99,
        }
        self.registry('purchase.order.line').create(cr, uid, vals, ctx)
        purchase.wkf_confirm_order()
        purchase.action_picking_create()
        purchase = purchase.browse()[0]
        self.assertListEqual(purchase.invoice_ids, [])

        # Here we create a WBL file for an order
        wbl_factory.generate_files([('purchase_id', '=', purchase_id)])
        pick_in_id = \
            self.pick_obj.search(cr, uid, [('purchase_id', '=', purchase_id)],
                                 context=ctx)[0]
        pick_in = self.pick_obj.browse(cr, uid, pick_in_id, ctx)
        self.assertNotIn(pick_in.state, ['done'],
                         'The stock.picking is not closed, '
                         'until everything is delivered')
        name = '.*_wbl_{0}.*IN.*\.xml'.format(purchase.name)
        self.assert_(self._yc_files(name), 'A WBL file is created')

        # Now we check some fields
        result_wbl_file = self._yc_files(name)[-1]
        wbl_node = self._get_file_node(result_wbl_file)
        self._save_node(wbl_node, 'wbl', path='//SupplierOrderNo')
        self.assertEqual(len(pick_in.move_lines),
                         len(xml_tools.nspath(wbl_node, '//Position')),
                         'A position for each item in the SO:\n{0}'.format(
                             xml_tools.xml_to_string(wbl_node)))

        # Here we create the response WBA file with a lot which fills
        # completely the line.
        lot = self.create_lot('LOT_prod{0}'.format(product_id),
                              product_id, 10)

        wba_node = self._create_mirror_wba_from_wbl(
            wbl_node, qty=lot.virtual_available_for_sale, lot=lot)
        self._save_node(wba_node, 'wba', path='//wba:SupplierOrderNo')

        # We save the WBA.
        wba_file_name = 'WBA_{0}.xml'.format(time.time())
        wba_connect_file_id = self._save_wba(wba_node, wba_file_name)

        # We check that the WBA has the Lot.
        wba_connect_file = self.stock_connect_file.browse(
            cr, uid, wba_connect_file_id, context=ctx)
        self.assertTrue('<wba:Lot>{0}</wba:Lot>'.format(lot.name)
                        in wba_connect_file.content)

        # We import the WBA file without errors.
        self.test_warehouse.stock_connect_id.connection_process_files()
        wba_connect_file = self.stock_connect_file.browse(
            cr, uid, wba_connect_file_id, context=ctx)
        self.assertFalse(wba_connect_file.error)
        self.assertFalse(wba_connect_file.info)
        self.assertEqual(wba_connect_file.state, 'done')
        self.check_product_lotted(product_id, lotted=True)

        # If the first WBA has been processed, then there is a line
        # without lot. If the second WBA has been processed, then
        # both lines have a lot.
        pick_in = self.pick_obj.browse(cr, uid, pick_in_id, ctx)
        moves = {}
        for move in pick_in.move_lines:
            moves[move.product_qty] = \
                move.prodlot_id and move.prodlot_id.id or False
        self.assertEqual(len(moves), 1,
                         "1 move was expected on the picking.in")
        self.assertEqual(moves[10], lot.id, "Bad lot for WBA")

        # We attempt to confirm the picking by the WBA.
        self.assertEqual(pick_in.state, 'assigned')
        self.test_warehouse.stock_connect_id.write({'yc_wba_confirm_time': 0})
        self.registry('stock.connect.yellowcube')._confirm_pickings_by_wba(
            cr, uid, self.test_warehouse.stock_connect_id.id, ctx)
        pick_in = self.pick_obj.browse(cr, uid, pick_in_id, ctx)
        self.assertEqual(pick_in.state, 'done')

    @skipIf(UNDER_DEVELOPMENT, UNDER_DEVELOPMENT_TEXT)
    def test_wba_with_1_lot_incomplete(self):
        """ The WBA sends a lot on a product which needs to track lots,
            but the lot does not fill completely the move.
        """
        cr, uid, ctx = self.cr, self.uid, self.context
        wbl_factory = get_factory([self.test_warehouse.pool, cr, uid], "wbl",
                                  context=ctx)

        # Makes sure the product doesn't have the lotting active.
        product_id = self.ref('product.product_product_3')
        self.check_product_lotted(product_id, lotted=False)

        # Creates the purchase from which to create the WBL.
        vals = {
            'name': 'IN_WBL_test',
            'partner_id': self.supplier_id,
            'location_id': self.test_warehouse.lot_input_id.id,
            'pricelist_id': self.ref('purchase.list0'),
            'invoice_method': 'picking',
        }
        purchase_id = self.purchase_obj.create(cr, uid, vals, ctx)
        purchase = self.purchase_obj.browse(cr, uid, purchase_id, ctx)
        vals = {
            'order_id': purchase_id,
            'product_id': self.ref('product.product_product_3'),
            'product_qty': 10,
            'price_unit': 7.65,
            'name': 'Test purchase product',
            'date_planned': '2050-01-01',
            'yc_posno': 99,
        }
        self.registry('purchase.order.line').create(cr, uid, vals, ctx)
        purchase.wkf_confirm_order()
        purchase.action_picking_create()
        purchase = purchase.browse()[0]
        self.assertListEqual(purchase.invoice_ids, [])

        # Here we create a WBL file for an order
        wbl_factory.generate_files([('purchase_id', '=', purchase_id)])
        pick_in_id = \
            self.pick_obj.search(cr, uid, [('purchase_id', '=', purchase_id)],
                                 context=ctx)[0]
        pick_in = self.pick_obj.browse(cr, uid, pick_in_id, ctx)
        self.assertNotIn(pick_in.state, ['done'],
                         'The stock.picking is not closed, '
                         'until everything is delivered')
        name = '.*_wbl_{0}.*IN.*\.xml'.format(purchase.name)
        self.assert_(self._yc_files(name), 'A WBL file is created')

        # Now we check some fields
        result_wbl_file = self._yc_files(name)[-1]
        wbl_node = self._get_file_node(result_wbl_file)
        self._save_node(wbl_node, 'wbl', path='//SupplierOrderNo')
        self.assertEqual(len(pick_in.move_lines),
                         len(xml_tools.nspath(wbl_node, '//Position')),
                         'A position for each item in the SO:\n{0}'.format(
                             xml_tools.xml_to_string(wbl_node)))

        # Here we create the response WBA file with a lot which fills
        # completely the line.
        lot = self.create_lot('LOT_prod{0}'.format(product_id),
                              product_id, 9)

        wba_node = self._create_mirror_wba_from_wbl(
            wbl_node, qty=lot.virtual_available_for_sale, lot=lot)
        self._save_node(wba_node, 'wba', path='//wba:SupplierOrderNo')

        # We save the WBA.
        wba_file_name = 'WBA_{0}.xml'.format(time.time())
        wba_connect_file_id = self._save_wba(wba_node, wba_file_name)

        # We check that the WBA has the Lot.
        wba_connect_file = self.stock_connect_file.browse(
            cr, uid, wba_connect_file_id, context=ctx)
        self.assertTrue('<wba:Lot>{0}</wba:Lot>'.format(lot.name)
                        in wba_connect_file.content)

        # We import the WBA file without errors.
        self.test_warehouse.stock_connect_id.connection_process_files()
        wba_connect_file = self.stock_connect_file.browse(
            cr, uid, wba_connect_file_id, context=ctx)
        self.assertFalse(wba_connect_file.error)
        self.assertFalse(wba_connect_file.info)
        self.assertEqual(wba_connect_file.state, 'done')
        self.check_product_lotted(product_id, lotted=True)

        # If the first WBA has been processed, then there is a line
        # without lot. If the second WBA has been processed, then
        # both lines have a lot.
        pick_in = self.pick_obj.browse(cr, uid, pick_in_id, ctx)
        moves = {}
        for move in pick_in.move_lines:
            moves[move.product_qty] = \
                move.prodlot_id and move.prodlot_id.id or False
        self.assertEqual(len(moves), 2,
                         "2 moves were expected on the picking.in")
        self.assertEqual(moves[9], lot.id, "Bad lot for the WBA")
        self.assertFalse(moves[1], "Bad lot for the WBA")

        # We attempt to confirm the picking by the WBA, which won't do the
        # work since the quantities are not yet assigned.
        self.assertEqual(pick_in.state, 'assigned')
        self.test_warehouse.stock_connect_id.write({'yc_wba_confirm_time': 1})
        self.registry('stock.connect.yellowcube')._confirm_pickings_by_wba(
            cr, uid, self.test_warehouse.stock_connect_id.id, ctx)
        pick_in = self.pick_obj.browse(cr, uid, pick_in_id, ctx)
        self.assertEqual(pick_in.state, 'assigned')

    @skipIf(UNDER_DEVELOPMENT, UNDER_DEVELOPMENT_TEXT)
    def test_wba_eod_flag_qty_done_block(self):
        """ The WBA has to be blocked when EoDFlag is set and Qty-Done=0 for
            a *given* move.
            Thest added to check issue i12382.
        """
        cr, uid, ctx = self.cr, self.uid, self.context
        wbl_factory = get_factory([self.test_warehouse.pool, cr, uid], "wbl",
                                  context=ctx)

        # Makes sure the products don't have the lotting active.
        product_1_id = self.ref('product.product_product_3')
        product_2_id = self.ref('product.product_product_2')
        self.check_product_lotted(product_1_id, lotted=False)
        self.check_product_lotted(product_2_id, lotted=False)

        # Creates the purchase from which to create the WBL.
        purchase_id = self.purchase_obj.create(cr, uid, {
            'name': 'IN_WBL_test',
            'partner_id': self.supplier_id,
            'location_id': self.test_warehouse.lot_input_id.id,
            'pricelist_id': self.ref('purchase.list0'),
            'invoice_method': 'picking',
        }, ctx)
        self.purchase_line_obj.create(cr, uid, {
            'order_id': purchase_id,
            'product_id': product_1_id,
            'product_qty': 10,
            'price_unit': 7.65,
            'name': 'Test purchase product 1',
            'date_planned': '2050-01-01',
            'yc_posno': 100,
        }, ctx)
        self.purchase_line_obj.create(cr, uid, {
            'order_id': purchase_id,
            'product_id': product_2_id,
            'product_qty': 20,
            'price_unit': 1.35,
            'name': 'Test purchase product 2',
            'date_planned': '2050-01-01',
            'yc_posno': 200,
        }, ctx)

        # Validates the purchase and creates the picking.
        purchase = self.purchase_obj.browse(cr, uid, purchase_id, ctx)
        purchase.wkf_confirm_order()
        purchase.action_picking_create()
        purchase = purchase.browse()[0]
        self.assertListEqual(purchase.invoice_ids, [])

        # Here we create a WBL file for an order
        wbl_factory.generate_files([('purchase_id', '=', purchase_id)])
        pick_in_id = self.pick_obj.search(cr, uid, [
            ('purchase_id', '=', purchase_id)
        ], context=ctx)[0]
        pick_in = self.pick_obj.browse(cr, uid, pick_in_id, ctx)
        self.assertNotIn(pick_in.state, ['done'],
                         'The stock.picking is not closed, '
                         'until everything is delivered')
        name = '.*_wbl_{0}.*IN.*\.xml'.format(purchase.name)
        self.assert_(self._yc_files(name), 'A WBL file is created')

        # Now we check some fields
        result_wbl_file = self._yc_files(name)[-1]
        wbl_node = self._get_file_node(result_wbl_file)
        self._save_node(wbl_node, 'wbl', path='//SupplierOrderNo')
        self.assertEqual(len(pick_in.move_lines),
                         len(xml_tools.nspath(wbl_node, '//Position')),
                         'A position for each item in the SO:\n{0}'.format(
                             xml_tools.xml_to_string(wbl_node)))

        # We create the WBA just for the first product and save it.
        wba_node = self._create_mirror_wba_from_wbl(
            wbl_node, partial=100, qty=5)
        self._save_node(wba_node, 'wba', path='//wba:SupplierOrderNo')
        wba_file_name = 'WBA_{0}.xml'.format(time.time())
        wba_connect_file_id = self._save_wba(wba_node, wba_file_name)

        # We set the moves for the first product to have yc_qty_done==0 and
        # yc_eod_received==True.
        move_ids = self.move_obj.search(self.cr, self.uid, [
            ('picking_id', '=', pick_in_id),
            ('product_id', '=', product_1_id)
        ], context=self.context)
        self.move_obj.write(cr, uid, move_ids, {
            'yc_qty_done': 0.0,
            'yc_eod_received': True,
        }, context=ctx)

        # We import the WBA file with errors.
        self.test_warehouse.stock_connect_id.connection_process_files()
        wba_connect_file = self.stock_connect_file.browse(
            cr, uid, wba_connect_file_id, context=ctx)
        self.assertTrue(wba_connect_file.error)
        self.assertTrue(wba_connect_file.info)
        self.assertTrue('having yc_qty_done == 0 and yc_eod_received == True' in wba_connect_file.info)
        self.assertEqual(wba_connect_file.state, 'draft')

    @skipIf(UNDER_DEVELOPMENT, UNDER_DEVELOPMENT_TEXT)
    def test_wba_eod_flag_qty_done_not_block(self):
        """ The WBA has to not to be blocked when EoDFlag is set and
            Qty-Done=0 for a move different than the given one.
            Thest added to check issue i12382.
        """
        cr, uid, ctx = self.cr, self.uid, self.context
        wbl_factory = get_factory([self.test_warehouse.pool, cr, uid], "wbl",
                                  context=ctx)

        # Makes sure the products don't have the lotting active.
        product_1_id = self.ref('product.product_product_3')
        product_2_id = self.ref('product.product_product_2')
        self.check_product_lotted(product_1_id, lotted=False)
        self.check_product_lotted(product_2_id, lotted=False)

        # Creates the purchase from which to create the WBL.
        purchase_id = self.purchase_obj.create(cr, uid, {
            'name': 'IN_WBL_test',
            'partner_id': self.supplier_id,
            'location_id': self.test_warehouse.lot_input_id.id,
            'pricelist_id': self.ref('purchase.list0'),
            'invoice_method': 'picking',
        }, ctx)
        self.purchase_line_obj.create(cr, uid, {
            'order_id': purchase_id,
            'product_id': product_1_id,
            'product_qty': 10,
            'price_unit': 7.65,
            'name': 'Test purchase product 1',
            'date_planned': '2050-01-01',
            'yc_posno': 100,
        }, ctx)
        self.purchase_line_obj.create(cr, uid, {
            'order_id': purchase_id,
            'product_id': product_2_id,
            'product_qty': 20,
            'price_unit': 1.35,
            'name': 'Test purchase product 2',
            'date_planned': '2050-01-01',
            'yc_posno': 200,
        }, ctx)

        # Validates the purchase and creates the picking.
        purchase = self.purchase_obj.browse(cr, uid, purchase_id, ctx)
        purchase.wkf_confirm_order()
        purchase.action_picking_create()
        purchase = purchase.browse()[0]
        self.assertListEqual(purchase.invoice_ids, [])

        # Here we create a WBL file for an order
        wbl_factory.generate_files([('purchase_id', '=', purchase_id)])
        pick_in_id = self.pick_obj.search(cr, uid, [
            ('purchase_id', '=', purchase_id)
        ], context=ctx)[0]
        pick_in = self.pick_obj.browse(cr, uid, pick_in_id, ctx)
        self.assertNotIn(pick_in.state, ['done'],
                         'The stock.picking is not closed, '
                         'until everything is delivered')
        name = '.*_wbl_{0}.*IN.*\.xml'.format(purchase.name)
        self.assert_(self._yc_files(name), 'A WBL file is created')

        # Now we check some fields
        result_wbl_file = self._yc_files(name)[-1]
        wbl_node = self._get_file_node(result_wbl_file)
        self._save_node(wbl_node, 'wbl', path='//SupplierOrderNo')
        self.assertEqual(len(pick_in.move_lines),
                         len(xml_tools.nspath(wbl_node, '//Position')),
                         'A position for each item in the SO:\n{0}'.format(
                             xml_tools.xml_to_string(wbl_node)))

        # We create the WBA just for the first product and save it.
        wba_node = self._create_mirror_wba_from_wbl(
            wbl_node, partial=100, qty=5)
        self._save_node(wba_node, 'wba', path='//wba:SupplierOrderNo')
        wba_file_name = 'WBA_{0}.xml'.format(time.time())
        wba_connect_file_id = self._save_wba(wba_node, wba_file_name)

        # We set the moves for the SECOND product to have yc_qty_done==0 and
        # yc_eod_received==True (we only generate the WBL for the first product).
        move_ids = self.move_obj.search(self.cr, self.uid, [
            ('picking_id', '=', pick_in_id),
            ('product_id', '=', product_2_id)
        ], context=self.context)
        self.move_obj.write(cr, uid, move_ids, {
            'yc_qty_done': 0.0,
            'yc_eod_received': True,
        }, context=ctx)

        # We import the WBA file with errors.
        self.test_warehouse.stock_connect_id.connection_process_files()
        wba_connect_file = self.stock_connect_file.browse(
            cr, uid, wba_connect_file_id, context=ctx)
        self.assertFalse(wba_connect_file.error)
        self.assertFalse(wba_connect_file.info)
        self.assertEqual(wba_connect_file.state, 'done')

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
