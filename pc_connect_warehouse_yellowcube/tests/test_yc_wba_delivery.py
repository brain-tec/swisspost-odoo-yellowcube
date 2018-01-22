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


class test_yc_wba_delivery(yellowcube_testcase):

    def setUp(self):
        super(test_yc_wba_delivery, self).setUp()
        self.test_warehouse.stock_connect_id.write({
            'yc_enable_wbl_file': True,
            'yc_enable_wba_file': True,
            'yc_wba_invoice_on_import': True,
            'yc_wba_confirm_time': 0.0,
            'yc_wba_respect_eod_flag': True,
        })

        # Creates a supplier.
        supplier_vals = {
            'name': 'Test supplier',
            'zip': '12345',
        }
        self.supplier_id = self.registry('res.partner').create(
            self.cr, self.uid, supplier_vals, self.context)

        # Configures the products to use in the WBA.
        self.wba_prod_1_id = self.ref('product.product_product_3')
        self.wba_prod_1_qty = 10

    @skipIf(UNDER_DEVELOPMENT, UNDER_DEVELOPMENT_TEXT)
    def test_wba_delivery_with_qty_not_complete_flag_not_set_not_respect_eod_flag(self):
        """ Tests the WBA with quantities not fulfilling a picking,
            and the WBA doesn't set the moves to be complete, BUT
            we explicitly choose not to respect the EndOfDelivery flag.
        """
        cr, uid, ctx = self.cr, self.uid, self.context
        purchase_obj = self.registry('purchase.order')
        pick_in_obj = self.registry('stock.picking.in')

        self.test_warehouse.stock_connect_id.write({
            'yc_wba_respect_eod_flag': False,
            'yc_wba_auto_cancel_backorder': False,
        })

        stock_connect_yellowcube = \
            self.connect_obj.browse(cr,
                                    uid,
                                    ctx['stock_connect_id'],
                                    context=ctx)

        wbl_factory = get_factory([self.test_warehouse.pool, cr, uid], "wbl",
                                  context=ctx)

        # Creates a purchase & validates it.
        purchase_id = self._create_purchase()
        self._add_purchase_line(purchase_id, {
            'product_id': self.wba_prod_1_id,
            'product_qty': self.wba_prod_1_qty,
        })
        self._validate_purchase(purchase_id)

        # For the moment, no invoices.
        purchase = purchase_obj.browse(cr, uid, purchase_id, context=ctx)
        self.assertListEqual(purchase.invoice_ids, [])

        # Here we create a WBL file for an order
        wbl_factory.generate_files([('purchase_id', '=', purchase_id)])
        pick_in_id = pick_in_obj.search(cr, uid, [
            ('purchase_id', '=', purchase_id),
        ], context=ctx)[0]
        pick_in = pick_in_obj.browse(cr, uid, pick_in_id, context=ctx)
        self.assertNotEqual(pick_in.state, 'done',
                            'The stock.picking must not be done, '
                            'until everything is delivered')
        name = '.*_wbl_{0}.*IN.*\.xml'.format(purchase.name)
        self.assert_(self._yc_files(name), 'A WBL file is created')

        # Now we check some fields
        result_wbl_file = self._yc_files(name)[-1]
        wbl_node = self._get_file_node(result_wbl_file)
        self.assertEqual(len(pick_in.move_lines),
                         len(xml_tools.nspath(wbl_node, '//Position')),
                         'A position for each item in the SO:\n{0}'.format(
                             xml_tools.xml_to_string(wbl_node)))

        # Here we create the response WBA file, accepting everything
        wba_node = self._create_mirror_wba_from_wbl(wbl_node)

        quantity = xml_tools.nspath(wba_node, '//wba:QuantityUOM')[0]
        quantity.text = str(self.wba_prod_1_qty / 2)
        eod_flag = xml_tools.nspath(wba_node, '//wba:EndOfDeliveryFlag')[0]
        eod_flag.text = '0'

        # Creates the new WBA file.
        vals = {
            'input': True,
            'content': xml_tools.xml_to_string(
                wba_node, encoding='unicode', xml_declaration=False),
            'name': 'WBA1_{0}.xml'.format(time.time()),
            'stock_connect_id': self.test_warehouse.stock_connect_id.id,
            'type': 'wba',
            'warehouse_id': self.test_warehouse.id,
        }
        self.stock_connect_file.create(cr, uid, vals, context=ctx)

        # Processes the files.
        stock_connect_yellowcube.connection_process_files()

        # The WBA will make the picking be in state 'done' with a backorder
        # in state assigned.
        purchase = purchase_obj.browse(cr, uid, purchase_id, context=ctx)
        self.assertEqual(len(purchase.picking_ids), 2,
                         "Two picking.in were expected to be linked to "
                         "the purchase, but {0} were "
                         "found".format(len(purchase.picking_ids)))

        pick_in = pick_in.browse()[0]
        self.assertEqual(pick_in.state, 'assigned',
                         'The stock.picking should be in state assigned.')

        backorder_id = list(set([p.id for p in purchase.picking_ids]) -
                            set([pick_in.id]))[0]
        backorder = pick_in_obj.browse(cr, uid, backorder_id, context=ctx)
        self.assertEqual(backorder.state, 'done',
                         'The backorder should be in state done.')

    @skipIf(UNDER_DEVELOPMENT, UNDER_DEVELOPMENT_TEXT)
    def test_wba_delivery_with_qty_not_complete_flag_not_set(self):
        """ Tests the WBA with quantities not fulfilling a picking,
            and the WBA doesn't set the moves to be complete.
        """
        cr, uid, ctx = self.cr, self.uid, self.context
        purchase_obj = self.registry('purchase.order')
        pick_in_obj = self.registry('stock.picking.in')

        stock_connect_yellowcube = \
            self.connect_obj.browse(cr,
                                    uid,
                                    ctx['stock_connect_id'],
                                    context=ctx)

        wbl_factory = get_factory([self.test_warehouse.pool, cr, uid], "wbl",
                                  context=ctx)

        # Creates a purchase & validates it.
        purchase_id = self._create_purchase()
        self._add_purchase_line(purchase_id, {
            'product_id': self.wba_prod_1_id,
            'product_qty': self.wba_prod_1_qty,
        })
        self._validate_purchase(purchase_id)

        # For the moment, no invoices.
        purchase = purchase_obj.browse(cr, uid, purchase_id, context=ctx)
        self.assertListEqual(purchase.invoice_ids, [])

        # Here we create a WBL file for an order
        wbl_factory.generate_files([('purchase_id', '=', purchase_id)])
        pick_in_id = pick_in_obj.search(cr, uid, [
            ('purchase_id', '=', purchase_id),
        ], context=ctx)[0]
        pick_in = pick_in_obj.browse(cr, uid, pick_in_id, context=ctx)
        self.assertNotEqual(pick_in.state, 'done',
                            'The stock.picking must not be done, '
                            'until everything is delivered')
        name = '.*_wbl_{0}.*IN.*\.xml'.format(purchase.name)
        self.assert_(self._yc_files(name), 'A WBL file is created')

        # Now we check some fields
        result_wbl_file = self._yc_files(name)[-1]
        wbl_node = self._get_file_node(result_wbl_file)
        self.assertEqual(len(pick_in.move_lines),
                         len(xml_tools.nspath(wbl_node, '//Position')),
                         'A position for each item in the SO:\n{0}'.format(
                             xml_tools.xml_to_string(wbl_node)))

        # Here we create the response WBA file, accepting everything
        wba_node = self._create_mirror_wba_from_wbl(wbl_node)

        quantity = xml_tools.nspath(wba_node, '//wba:QuantityUOM')[0]
        quantity.text = str(self.wba_prod_1_qty / 2)
        eod_flag = xml_tools.nspath(wba_node, '//wba:EndOfDeliveryFlag')[0]
        eod_flag.text = '0'

        # Creates the new WBA file.
        vals = {
            'input': True,
            'content': xml_tools.xml_to_string(
                wba_node, encoding='unicode', xml_declaration=False),
            'name': 'WBA1_{0}.xml'.format(time.time()),
            'stock_connect_id': self.test_warehouse.stock_connect_id.id,
            'type': 'wba',
            'warehouse_id': self.test_warehouse.id,
        }
        self.stock_connect_file.create(cr, uid, vals, context=ctx)

        # Processes the files.
        stock_connect_yellowcube.connection_process_files()

        # Since the WBA was not complete:
        # The picking.in must be in state assigned, not done.
        pick_in = pick_in.browse()[0]
        self.assertEqual(pick_in.state, 'assigned',
                         'The stock.picking should be in state assigned.')

        # No backorders have to be created.
        purchase = purchase_obj.browse(cr, uid, purchase_id, context=ctx)
        self.assertEqual(len(purchase.picking_ids), 1,
                         "Just one picking.in was expected to be linked to "
                         "the purchase, but {0} were "
                         "found".format(len(purchase.picking_ids)))

    @skipIf(UNDER_DEVELOPMENT, UNDER_DEVELOPMENT_TEXT)
    def test_wba_delivery_with_qty_not_complete_flag_set_backorder(self):
        """ Tests the WBA with quantities not fulfilling a picking,
            and the WBA set set the moves to be complete so it generates
            a backorder, which is NOT cancelled.
        """
        cr, uid, ctx = self.cr, self.uid, self.context
        purchase_obj = self.registry('purchase.order')
        pick_in_obj = self.registry('stock.picking.in')

        wbl_factory = get_factory([self.test_warehouse.pool, cr, uid],
                                  "wbl", context=ctx)

        # Creates a purchase & validates it.
        purchase_id = self._create_purchase()
        self._add_purchase_line(purchase_id, {
            'product_id': self.wba_prod_1_id,
            'product_qty': self.wba_prod_1_qty,
        })
        self._validate_purchase(purchase_id)

        # For the moment, no invoices.
        purchase = purchase_obj.browse(cr, uid, purchase_id, context=ctx)
        self.assertListEqual(purchase.invoice_ids, [])

        # Here we create a WBL file for an order
        wbl_factory.generate_files([('purchase_id', '=', purchase_id)])
        pick_in_id = pick_in_obj.search(cr, uid, [
            ('purchase_id', '=', purchase_id),
        ], context=ctx)[0]
        pick_in = pick_in_obj.browse(cr, uid, pick_in_id, context=ctx)
        self.assertNotEqual(pick_in.state, 'done',
                            'The stock.picking must not be done, '
                            'until everything is delivered')
        name = '.*_wbl_{0}.*IN.*\.xml'.format(purchase.name)
        self.assert_(self._yc_files(name), 'A WBL file is created')

        # Now we check some fields
        result_wbl_file = self._yc_files(name)[-1]
        wbl_node = self._get_file_node(result_wbl_file)
        self.assertEqual(len(pick_in.move_lines),
                         len(xml_tools.nspath(wbl_node, '//Position')),
                         'A position for each item in the SO:\n{0}'.format(
                             xml_tools.xml_to_string(wbl_node)))

        # Here we create the response WBA file, accepting everything
        wba_node = self._create_mirror_wba_from_wbl(wbl_node)

        quantity = xml_tools.nspath(wba_node, '//wba:QuantityUOM')[0]
        quantity.text = str(self.wba_prod_1_qty / 2)
        eod_flag = xml_tools.nspath(wba_node, '//wba:EndOfDeliveryFlag')[0]
        eod_flag.text = '1'

        # Creates the new WBA file.
        vals = {
            'input': True,
            'content': xml_tools.xml_to_string(
                wba_node, encoding='unicode', xml_declaration=False),
            'name': 'WBA1_{0}.xml'.format(time.time()),
            'stock_connect_id': self.test_warehouse.stock_connect_id.id,
            'type': 'wba',
            'warehouse_id': self.test_warehouse.id,
        }
        self.stock_connect_file.create(cr, uid, vals, context=ctx)

        # Sets the security check for confirmation of WBA.
        # In this case we don't activate it.
        stock_connect_id = ctx['stock_connect_id']

        # We do want backorders here, so we don't cancel them.
        self.test_warehouse.stock_connect_id.write({
            'yc_wba_auto_cancel_backorder': False,
        })

        # Processes the files.
        self.test_warehouse.stock_connect_id.connection_process_files()

        # A backorder was created
        purchase = purchase_obj.browse(cr, uid, purchase_id, context=ctx)
        self.assertEqual(len(purchase.picking_ids), 2,
                         "Two picking.in was expected to be linked to "
                         "the purchase, but {0} were "
                         "found".format(len(purchase.picking_ids)))

        # One of those pickings is the back-order, that has the items delivered
        # and has to be in state done, while the other has to be in state
        # assigned.
        backorder_id = list(set([p.id for p in purchase.picking_ids]) -
                            set([pick_in_id]))
        backorder = pick_in_obj.browse(cr, uid, backorder_id[0], context=ctx)
        self.assertEqual(backorder.state, 'done',
                         "The backorder should be in state done, but is "
                         "in state {0}".format(backorder.state))
        pick_in = pick_in_obj.browse(cr, uid, pick_in_id, context=ctx)
        self.assertEqual(pick_in.state, 'assigned',
                         "The picking with the missing quantities must be in "
                         "state assigned, but is "
                         "in state {0}".format(pick_in.state))

        # The new picking with the pending quantities, apart of being cancelled
        # must have the pending quantities set to zero, and the flag cleared.
        for backorder_move in pick_in.move_lines:
            self.assertEqual(backorder_move.yc_qty_done, 0,
                             "Quantity done must be zero on all the moves "
                             "of the backorder, but the backorder with id={0} "
                             "had a greater value.".format(backorder.id))
            self.assertEqual(backorder_move.yc_eod_received, True,
                             "Flag received must be equal to the one from "
                             "the move it comes from.".format(backorder.id))

    @skipIf(UNDER_DEVELOPMENT, UNDER_DEVELOPMENT_TEXT)
    def test_wba_delivery_with_qty_complete_flag_set_cancel_backorder(self):
        """ Tests the WBA with quantities not fulfilling a picking,
            and the WBA set set the moves to be complete so it generates
            a backorder, which is cancelled.
        """
        cr, uid, ctx = self.cr, self.uid, self.context
        purchase_obj = self.registry('purchase.order')
        pick_in_obj = self.registry('stock.picking.in')

        wbl_factory = get_factory([self.test_warehouse.pool, cr, uid],
                                  "wbl", context=ctx)

        # Creates a purchase & validates it.
        purchase_id = self._create_purchase()
        self._add_purchase_line(purchase_id, {
            'product_id': self.wba_prod_1_id,
            'product_qty': self.wba_prod_1_qty,
        })
        self._validate_purchase(purchase_id)

        # For the moment, no invoices.
        purchase = purchase_obj.browse(cr, uid, purchase_id, context=ctx)
        self.assertListEqual(purchase.invoice_ids, [])

        # Here we create a WBL file for an order
        wbl_factory.generate_files([('purchase_id', '=', purchase_id)])
        pick_in_id = pick_in_obj.search(cr, uid, [
            ('purchase_id', '=', purchase_id),
        ], context=ctx)[0]
        pick_in = pick_in_obj.browse(cr, uid, pick_in_id, context=ctx)
        self.assertNotEqual(pick_in.state, 'done',
                            'The stock.picking must not be done, '
                            'until everything is delivered')
        name = '.*_wbl_{0}.*IN.*\.xml'.format(purchase.name)
        self.assert_(self._yc_files(name), 'A WBL file is created')

        # Now we check some fields
        result_wbl_file = self._yc_files(name)[-1]
        wbl_node = self._get_file_node(result_wbl_file)
        self.assertEqual(len(pick_in.move_lines),
                         len(xml_tools.nspath(wbl_node, '//Position')),
                         'A position for each item in the SO:\n{0}'.format(
                             xml_tools.xml_to_string(wbl_node)))

        # Here we create the response WBA file, accepting everything
        wba_node = self._create_mirror_wba_from_wbl(wbl_node)

        quantity = xml_tools.nspath(wba_node, '//wba:QuantityUOM')[0]
        quantity.text = str(self.wba_prod_1_qty / 2)
        eod_flag = xml_tools.nspath(wba_node, '//wba:EndOfDeliveryFlag')[0]
        eod_flag.text = '1'

        # Creates the new WBA file.
        vals = {
            'input': True,
            'content': xml_tools.xml_to_string(
                wba_node, encoding='unicode', xml_declaration=False),
            'name': 'WBA1_{0}.xml'.format(time.time()),
            'stock_connect_id': self.test_warehouse.stock_connect_id.id,
            'type': 'wba',
            'warehouse_id': self.test_warehouse.id,
        }
        self.stock_connect_file.create(cr, uid, vals, context=ctx)

        # We do NOT want backorders here, so we cancel them.
        self.test_warehouse.stock_connect_id.write({
            'yc_wba_auto_cancel_backorder': True,
        })

        # Processes the files.
        self.test_warehouse.stock_connect_id.connection_process_files()

        # A backorder was created
        purchase = purchase_obj.browse(cr, uid, purchase_id, context=ctx)
        self.assertEqual(len(purchase.picking_ids), 2,
                         "Two picking.in was expected to be linked to "
                         "the purchase, but {0} were "
                         "found".format(len(purchase.picking_ids)))

        # One of those pickings is the back-order, that has the items delivered
        # and has to be in state done, while the other has to be in state
        # cancel.
        backorder_id = list(set([p.id for p in purchase.picking_ids]) -
                            set([pick_in_id]))
        backorder = pick_in_obj.browse(cr, uid, backorder_id[0], context=ctx)
        self.assertEqual(backorder.state, 'done',
                         "The backorder should be in state done, but is "
                         "in state {0}".format(backorder.state))
        pick_in = pick_in_obj.browse(cr, uid, pick_in_id, context=ctx)
        self.assertEqual(pick_in.state, 'cancel',
                         "The picking with the missing quantities must be in "
                         "state cancel, but is "
                         "in state {0}".format(pick_in.state))

        # The new picking with the pending quantities, apart of being cancelled
        # must have the pending quantities set to zero, and the flag must be
        # equal to the one from the move it comes from.
        for backorder_move in pick_in.move_lines:
            self.assertEqual(backorder_move.yc_qty_done, 0,
                             "Quantity done must be zero on all the moves "
                             "of the backorder, but the backorder with id={0} "
                             "had a greater value.".format(backorder.id))
            self.assertEqual(backorder_move.yc_eod_received, True,
                             "Flag received must be equal to the one from "
                             "the move it comes from.".format(backorder.id))

    @skipIf(UNDER_DEVELOPMENT, UNDER_DEVELOPMENT_TEXT)
    def test_wba_delivery_with_qty_complete_flag_set(self):
        """ Tests the WBA with quantities fulfilling a picking,
            and the WBA sets the moves to be complete.
        """
        cr, uid, ctx = self.cr, self.uid, self.context
        purchase_obj = self.registry('purchase.order')
        pick_in_obj = self.registry('stock.picking.in')

        stock_connect_yellowcube = \
            self.connect_obj.browse(cr,
                                    uid,
                                    ctx['stock_connect_id'],
                                    context=ctx)

        wbl_factory = get_factory([self.test_warehouse.pool, cr, uid], "wbl",
                                  context=ctx)

        # Creates a purchase & validates it.
        purchase_id = self._create_purchase()
        self._add_purchase_line(purchase_id, {
            'product_id': self.wba_prod_1_id,
            'product_qty': self.wba_prod_1_qty,
        })
        self._validate_purchase(purchase_id)

        # For the moment, no invoices.
        purchase = purchase_obj.browse(cr, uid, purchase_id, context=ctx)
        self.assertListEqual(purchase.invoice_ids, [])

        # Here we create a WBL file for an order
        wbl_factory.generate_files([('purchase_id', '=', purchase_id)])
        pick_in_id = pick_in_obj.search(cr, uid, [
            ('purchase_id', '=', purchase_id),
        ], context=ctx)[0]
        pick_in = pick_in_obj.browse(cr, uid, pick_in_id, context=ctx)
        self.assertNotEqual(pick_in.state, 'done',
                            'The stock.picking must not be done, '
                            'until everything is delivered')
        name = '.*_wbl_{0}.*IN.*\.xml'.format(purchase.name)
        self.assert_(self._yc_files(name), 'A WBL file is created')

        # Now we check some fields
        result_wbl_file = self._yc_files(name)[-1]
        wbl_node = self._get_file_node(result_wbl_file)
        self.assertEqual(len(pick_in.move_lines),
                         len(xml_tools.nspath(wbl_node, '//Position')),
                         'A position for each item in the SO:\n{0}'.format(
                             xml_tools.xml_to_string(wbl_node)))

        # Here we create the response WBA file, accepting everything
        wba_node = self._create_mirror_wba_from_wbl(wbl_node)

        quantity = xml_tools.nspath(wba_node, '//wba:QuantityUOM')[0]
        quantity.text = str(self.wba_prod_1_qty)
        eod_flag = xml_tools.nspath(wba_node, '//wba:EndOfDeliveryFlag')[0]
        eod_flag.text = '1'

        # Creates the new WBA file.
        vals = {
            'input': True,
            'content': xml_tools.xml_to_string(
                wba_node, encoding='unicode', xml_declaration=False),
            'name': 'WBA1_{0}.xml'.format(time.time()),
            'stock_connect_id': self.test_warehouse.stock_connect_id.id,
            'type': 'wba',
            'warehouse_id': self.test_warehouse.id,
        }
        self.stock_connect_file.create(cr, uid, vals, context=ctx)

        # Processes the files.
        self.test_warehouse.stock_connect_id.connection_process_files()

        # Since the WBA was complete:
        # The picking.in must be in state done.
        pick_in = pick_in.browse()[0]
        self.assertEqual(pick_in.state, 'done',
                         'The stock.picking should be in state done.')

        # No backorders have to be created.
        purchase = purchase_obj.browse(cr, uid, purchase_id, context=ctx)
        self.assertEqual(len(purchase.picking_ids), 1,
                         "Just one picking.in was expected to be linked to "
                         "the purchase, but {0} were "
                         "found".format(len(purchase.picking_ids)))

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
