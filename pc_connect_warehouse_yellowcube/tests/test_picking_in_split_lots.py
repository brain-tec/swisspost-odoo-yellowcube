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

import unittest2
from unittest2 import skipIf
from yellowcube_testcase import yellowcube_testcase

UNDER_DEVELOPMENT = False
UNDER_DEVELOPMENT_TEXT = "Test was skipped because of being under development."


class test_picking_split_lots(yellowcube_testcase):

    def setUp(self):
        super(test_picking_split_lots, self).setUp()

        # Creates the supplier.
        self.supplier_id = self.registry('res.partner').create(
            self.cr, self.uid, {
            'name': 'Test supplier',
            'zip': '12345',
        }, self.context)

    def test_split_lot(self):
        """ Test the scenario in which a lot is repeteadly split.
        """
        cr, uid, ctx = self.cr, self.uid, self.context
        purchase_obj = self.registry('purchase.order')
        picking_in_obj = self.registry('stock.picking.in')

        product_id = self.ref('product.product_product_48')

        # Creates three lots for the given product.
        lot_a = self.create_lot('LOT-A', product_id, 100)
        lot_b = self.create_lot('LOT-B', product_id, 100)
        lot_c = self.create_lot('LOT-C', product_id, 100)

        # Creates a purchase order with just one product.
        purchase_id = self._create_purchase()
        self._add_purchase_line(purchase_id, {
            'product_id': product_id,
            'product_qty': 80,
        })

        # Validates the purchase order so that it creates a picking.IN.
        self._validate_purchase(purchase_id)

        # Gets the picking.IN created, and makes sure is unique.
        purchase = purchase_obj.browse(cr, uid, purchase_id, context=ctx)
        picking_ids = [picking.id for picking in purchase.picking_ids]
        self.assertEqual(len(picking_ids), 1,
                         "Expected number of pickings is 1 "
                         "but {0} were found".format(len(picking_ids)))
        picking = picking_in_obj.browse(cr, uid, picking_ids[0], context=ctx)
        moves = [move for move in picking.move_lines]

        yc_posno = 1
        for move in moves:
            # We assume the WBL was generated already and that the YC PosNo
            # is already assigned.
            move.write({'yc_posno': yc_posno})

        # Before the arrival of the first partial:
        self.assertEqual(len(moves), 1,
                         "Expected number of moves is 1 "
                         "but {0} were found".format(len(moves)))
        self.assertEqual(moves[0].product_qty, 80)
        self.assertEqual(moves[0].yc_qty_done, 0)
        self.assertFalse(moves[0].prodlot_id)

        # A 1st partial arrives with 20 units.
        partial = {
            'product_id': product_id,
            'prodlot_id': lot_a.id,
            'product_qty': 20,
            'product_uom': move.product_uom.id,
        }
        picking_in_obj.split_lot(
            cr, uid, picking.id, partial, yc_posno, context=ctx)
        picking = picking_in_obj.browse(cr, uid, picking_ids[0], context=ctx)
        self.assertEqual(len(picking.move_lines), 2,
                         "Expected number of moves is 2 "
                         "but {0} were found".format(len(picking.move_lines)))
        moves_expected = {(60, 0, False),
                          (20, 20, lot_a.id)}
        moves_actual = set()
        for move in picking.move_lines:
            moves_actual.add((move.product_qty,
                              move.yc_qty_done,
                              move.prodlot_id.id))
        self.assertEqual(moves_expected, moves_actual)

        # A 2nd partial arrives with 20 units.
        partial = {
            'product_id': product_id,
            'prodlot_id': lot_a.id,
            'product_qty': 20,
            'product_uom': move.product_uom.id,
        }
        picking_in_obj.split_lot(
            cr, uid, picking.id, partial, yc_posno, context=ctx)
        picking = picking_in_obj.browse(cr, uid, picking_ids[0], context=ctx)
        self.assertEqual(len(picking.move_lines), 2,
                         "Expected number of moves is 2 "
                         "but {0} were found".format(len(picking.move_lines)))
        moves_expected = {(40, 0, False),
                          (40, 40, lot_a.id)}
        moves_actual = set()
        for move in picking.move_lines:
            moves_actual.add((move.product_qty,
                              move.yc_qty_done,
                              move.prodlot_id.id))
        self.assertEqual(moves_expected, moves_actual)

        # A 3rd partial arrives with 20 units.
        partial = {
            'product_id': product_id,
            'prodlot_id': lot_b.id,
            'product_qty': 20,
            'product_uom': move.product_uom.id,
        }
        picking_in_obj.split_lot(
            cr, uid, picking.id, partial, yc_posno, context=ctx)
        picking = picking_in_obj.browse(cr, uid, picking_ids[0], context=ctx)
        self.assertEqual(len(picking.move_lines), 3,
                         "Expected number of moves is 3 "
                         "but {0} were found".format(len(picking.move_lines)))
        moves_expected = {(20, 0, False),
                          (40, 40, lot_a.id),
                          (20, 20, lot_b.id)}
        moves_actual = set()
        for move in picking.move_lines:
            moves_actual.add((move.product_qty,
                              move.yc_qty_done,
                              move.prodlot_id.id))
        self.assertEqual(moves_expected, moves_actual)

        # A 4th partial arrives with 20 units.
        partial = {
            'product_id': product_id,
            'prodlot_id': lot_b.id,
            'product_qty': 20,
            'product_uom': move.product_uom.id,
        }
        picking_in_obj.split_lot(
            cr, uid, picking.id, partial, yc_posno, context=ctx)
        picking = picking_in_obj.browse(cr, uid, picking_ids[0], context=ctx)
        self.assertEqual(len(picking.move_lines), 3,
                         "Expected number of moves is 3 "
                         "but {0} were found".format(len(picking.move_lines)))
        moves_expected = {(0, 0, False),
                          (40, 40, lot_a.id),
                          (40, 40, lot_b.id)}
        moves_actual = set()
        for move in picking.move_lines:
            moves_actual.add((move.product_qty,
                              move.yc_qty_done,
                              move.prodlot_id.id))
        self.assertEqual(moves_expected, moves_actual)

        # A 5th partial arrives with 20 extra units of a new lot.
        partial = {
            'product_id': product_id,
            'prodlot_id': lot_c.id,
            'product_qty': 20,
            'product_uom': move.product_uom.id,
        }
        picking_in_obj.split_lot(
            cr, uid, picking.id, partial, yc_posno, context=ctx)
        picking = picking_in_obj.browse(cr, uid, picking_ids[0], context=ctx)
        self.assertEqual(len(picking.move_lines), 4,
                         "Expected number of moves is 4 "
                         "but {0} were found".format(len(picking.move_lines)))
        moves_expected = {(0, 0, False),
                          (39, 40, lot_b.id),
                          (40, 40, lot_a.id),
                          (1, 20, lot_c.id)}
        moves_actual = set()
        for move in picking.move_lines:
            moves_actual.add((move.product_qty,
                              move.yc_qty_done,
                              move.prodlot_id.id))
        self.assertEqual(moves_expected, moves_actual)

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
