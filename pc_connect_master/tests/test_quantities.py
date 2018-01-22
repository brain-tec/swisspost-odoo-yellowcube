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


from openerp.tests import common
from unittest2 import skipIf
from common import CommonTestFunctionality


UNDER_DEVELOPMENT = False
UNDER_DEVELOPMENT_TEXT = "Test was skipped because of being under development."


class test_quantities(common.TransactionCase, CommonTestFunctionality):

    def setUp(self):
        super(test_quantities, self).setUp()
        self.context = {}

        cr, uid, ctx = self.cr, self.uid, self.context
        wkf_obj = self.registry('workflow')

        # Workflows over the product are deactivated because, when executing
        # all the integration tests, the module for the Product's Life-cycle
        # interfers with the creation of the products: it seems like the
        # definition of the workflow is loaded from the XML of that module,
        # but the code is not taken into account because that module not
        # being one of the dependencies of this one, thus it doesn't find
        # the methods.
        workflow_products_ids = wkf_obj.search(cr, uid, [
            ('osv', 'in', ['product.product', 'product.template']),
        ], context=ctx)
        wkf_obj.write(cr, uid, workflow_products_ids, {
            'on_create': False,
        }, context=ctx)

    @skipIf(UNDER_DEVELOPMENT, UNDER_DEVELOPMENT_TEXT)
    def test_fields_without_quantities(self):
        """ Tests the fields alone, without quantities for the product.
        """
        cr, uid, ctx = self.cr, self.uid, self.context
        prod_obj = self.registry('product.product')

        prod_1_id = self.create_product(self, {'name': 'PROD-1'})
        prod_1 = prod_obj.browse(cr, uid, prod_1_id, context=ctx)
        self.assertEqual(prod_1.qty_available, 0)
        self.assertEqual(prod_1.incoming_qty, 0)
        self.assertEqual(prod_1.outgoing_qty, 0)
        self.assertEqual(prod_1.virtual_available, 0)
        self.assertEqual(prod_1.qty_on_assigned_moves, 0)
        self.assertEqual(prod_1.product_reservation_qty, 0)
        self.assertEqual(prod_1.qty_on_sale, 0)

    @skipIf(UNDER_DEVELOPMENT, UNDER_DEVELOPMENT_TEXT)
    def test_fields_without_shops__not_lotted(self):
        """ Tests the fields alone, without querying for a shop in particular.
            The products are not lotted.
        """
        cr, uid, ctx = self.cr, self.uid, self.context
        prod_obj = self.registry('product.product')

        prod_id = self.create_product(self, {'name': 'PROD-1'})

        # Orders 7 items for shop 1.
        shop_1_id = self.ref('pc_connect_master.shop1')
        self.obtain_qty(self, prod_id, 7, shop_1_id)

        # Order 3 items for shop 2.
        shop_2_id = self.ref('pc_connect_master.shop2')
        self.obtain_qty(self, prod_id, 3, shop_2_id)

        prod = prod_obj.browse(cr, uid, prod_id, context=ctx)
        self.assertEqual(prod.qty_available, 10)
        self.assertEqual(prod.incoming_qty, 0)
        self.assertEqual(prod.outgoing_qty, 0)
        self.assertEqual(prod.virtual_available, 10)
        self.assertEqual(prod.qty_on_assigned_moves, 0)
        self.assertEqual(prod.product_reservation_qty, 0)
        self.assertEqual(prod.qty_on_sale, 10)

        # Consumes 2 items of shop 1.
        order_id = self.consume_qty(self, prod_id, 2, shop_1_id)

        prod = prod_obj.browse(cr, uid, prod_id, context=ctx)
        self.assertEqual(prod.qty_available, 10)
        self.assertEqual(prod.incoming_qty, 0)
        self.assertEqual(prod.outgoing_qty, 0)
        self.assertEqual(prod.virtual_available, 10)
        self.assertEqual(prod.qty_on_assigned_moves, 0)
        self.assertEqual(prod.product_reservation_qty, 2)
        self.assertEqual(prod.qty_on_sale, 8)

        # Validates the order.
        self.validate_order(self, order_id)

        prod = prod_obj.browse(cr, uid, prod_id, context=ctx)
        self.assertEqual(prod.qty_available, 10)
        self.assertEqual(prod.incoming_qty, 0)
        self.assertEqual(prod.outgoing_qty, -2)
        self.assertEqual(prod.virtual_available, 8)
        self.assertEqual(prod.qty_on_assigned_moves, 0)
        self.assertEqual(prod.product_reservation_qty, 0)
        self.assertEqual(prod.qty_on_sale, 8)

        # Assigns the two items from the order.
        self.assign_picking_from_order(self, order_id)

        prod = prod_obj.browse(cr, uid, prod_id, context=ctx)
        self.assertEqual(prod.qty_available, 10)
        self.assertEqual(prod.incoming_qty, 0)
        self.assertEqual(prod.outgoing_qty, -2)
        self.assertEqual(prod.virtual_available, 8)
        self.assertEqual(prod.qty_on_assigned_moves, 2)
        self.assertEqual(prod.product_reservation_qty, 0)
        self.assertEqual(prod.qty_on_sale, 8)

        # Delivers the quantities.
        order = self.registry('sale.order').browse(cr, uid, order_id, context=ctx)
        picking_ids = [p.id for p in order.picking_ids]
        self.deliver_assigned_picking(self, picking_ids)

        prod = prod_obj.browse(cr, uid, prod_id, context=ctx)
        self.assertEqual(prod.qty_available, 8)
        self.assertEqual(prod.incoming_qty, 0)
        self.assertEqual(prod.outgoing_qty, 0)
        self.assertEqual(prod.virtual_available, 8)
        self.assertEqual(prod.qty_on_assigned_moves, 0)
        self.assertEqual(prod.product_reservation_qty, 0)
        self.assertEqual(prod.qty_on_sale, 8)

    @skipIf(UNDER_DEVELOPMENT, UNDER_DEVELOPMENT_TEXT)
    def test_fields_with_shops__not_lotted(self):
        """ Tests the fields alone, querying for the quantities for a shop.
            The products are not lotted.
        """
        cr, uid, ctx = self.cr, self.uid, self.context
        prod_obj = self.registry('product.product')

        prod_id = self.create_product(self, {'name': 'PROD-1'})

        # Orders 7 items for shop 1.
        shop_1_id = self.ref('pc_connect_master.shop1')
        self.obtain_qty(self, prod_id, 7, shop_1_id)

        # Orders 3 items for shop 2.
        shop_2_id = self.ref('pc_connect_master.shop2')
        self.obtain_qty(self, prod_id, 3, shop_2_id)

        # Checks the quantities for the shop 1.
        ctx.update({'shop': shop_1_id})
        prod = prod_obj.browse(cr, uid, prod_id, context=ctx)
        self.assertEqual(prod.qty_available, 7)
        self.assertEqual(prod.incoming_qty, 0)
        self.assertEqual(prod.outgoing_qty, 0)
        self.assertEqual(prod.virtual_available, 7)
        self.assertEqual(prod.qty_on_assigned_moves, 0)
        self.assertEqual(prod.product_reservation_qty, 0)
        self.assertEqual(prod.qty_on_sale, 7)

        # Checks the quantities for the shop 2.
        ctx.update({'shop': shop_2_id})
        prod = prod_obj.browse(cr, uid, prod_id, context=ctx)
        self.assertEqual(prod.qty_available, 3)
        self.assertEqual(prod.incoming_qty, 0)
        self.assertEqual(prod.outgoing_qty, 0)
        self.assertEqual(prod.virtual_available, 3)
        self.assertEqual(prod.qty_on_assigned_moves, 0)
        self.assertEqual(prod.product_reservation_qty, 0)
        self.assertEqual(prod.qty_on_sale, 3)

        # Checks the quantities without any shop.
        if 'shop' in ctx:
            del ctx['shop']
        prod = prod_obj.browse(cr, uid, prod_id, context=ctx)
        self.assertEqual(prod.qty_available, 10)
        self.assertEqual(prod.incoming_qty, 0)
        self.assertEqual(prod.outgoing_qty, 0)
        self.assertEqual(prod.virtual_available, 10)
        self.assertEqual(prod.qty_on_assigned_moves, 0)
        self.assertEqual(prod.product_reservation_qty, 0)
        self.assertEqual(prod.qty_on_sale, 10)

        # Consumes 2 items of shop 1.
        order_id = self.consume_qty(self, prod_id, 2, shop_1_id)

        ctx.update({'shop': shop_1_id})
        prod = prod_obj.browse(cr, uid, prod_id, context=ctx)
        self.assertEqual(prod.qty_available, 7)
        self.assertEqual(prod.incoming_qty, 0)
        self.assertEqual(prod.outgoing_qty, 0)
        self.assertEqual(prod.virtual_available, 7)
        self.assertEqual(prod.qty_on_assigned_moves, 0)
        self.assertEqual(prod.product_reservation_qty, 2)
        self.assertEqual(prod.qty_on_sale, 5)

        # Validates the order.
        self.validate_order(self, order_id)

        ctx.update({'shop': shop_1_id})
        prod = prod_obj.browse(cr, uid, prod_id, context=ctx)
        self.assertEqual(prod.qty_available, 7)
        self.assertEqual(prod.incoming_qty, 0)
        self.assertEqual(prod.outgoing_qty, -2)
        self.assertEqual(prod.virtual_available, 5)
        self.assertEqual(prod.qty_on_assigned_moves, 0)
        self.assertEqual(prod.product_reservation_qty, 0)
        self.assertEqual(prod.qty_on_sale, 5)

        # Assigns the two items from the order.
        self.assign_picking_from_order(self, order_id)

        prod = prod_obj.browse(cr, uid, prod_id, context=ctx)
        self.assertEqual(prod.qty_available, 7)
        self.assertEqual(prod.incoming_qty, 0)
        self.assertEqual(prod.outgoing_qty, -2)
        self.assertEqual(prod.virtual_available, 5)
        self.assertEqual(prod.qty_on_assigned_moves, 2)
        self.assertEqual(prod.product_reservation_qty, 0)
        self.assertEqual(prod.qty_on_sale, 5)

        # Delivers the quantities.
        order = self.registry('sale.order').browse(cr, uid, order_id, context=ctx)
        picking_ids = [p.id for p in order.picking_ids]
        self.deliver_assigned_picking(self, picking_ids)

        prod = prod_obj.browse(cr, uid, prod_id, context=ctx)
        self.assertEqual(prod.qty_available, 5)
        self.assertEqual(prod.incoming_qty, 0)
        self.assertEqual(prod.outgoing_qty, 0)
        self.assertEqual(prod.virtual_available, 5)
        self.assertEqual(prod.qty_on_assigned_moves, 0)
        self.assertEqual(prod.product_reservation_qty, 0)
        self.assertEqual(prod.qty_on_sale, 5)

        # Checks that the quantities for the shop 2 remain unchanged.
        ctx.update({'shop': shop_2_id})
        prod = prod_obj.browse(cr, uid, prod_id, context=ctx)
        self.assertEqual(prod.qty_available, 3)
        self.assertEqual(prod.incoming_qty, 0)
        self.assertEqual(prod.outgoing_qty, 0)
        self.assertEqual(prod.virtual_available, 3)
        self.assertEqual(prod.qty_on_assigned_moves, 0)
        self.assertEqual(prod.product_reservation_qty, 0)
        self.assertEqual(prod.qty_on_sale, 3)

        # Checks that the global quantities match.
        if 'shop' in ctx:
            del ctx['shop']
        prod = prod_obj.browse(cr, uid, prod_id, context=ctx)
        self.assertEqual(prod.qty_available, 8)
        self.assertEqual(prod.incoming_qty, 0)
        self.assertEqual(prod.outgoing_qty, 0)
        self.assertEqual(prod.virtual_available, 8)
        self.assertEqual(prod.qty_on_assigned_moves, 0)
        self.assertEqual(prod.product_reservation_qty, 0)
        self.assertEqual(prod.qty_on_sale, 8)

    @skipIf(UNDER_DEVELOPMENT, UNDER_DEVELOPMENT_TEXT)
    def test_fields_without_shops__lotted(self):
        """ Tests the fields alone, without querying for a shop in particular.
            The products are not lotted.
        """
        cr, uid, ctx = self.cr, self.uid, self.context
        prod_obj = self.registry('product.product')

        prod_id = self.create_product(self, {'name': 'PROD-1'})

        # Creates two lots, one of them expired.
        lot_valid_id = self.create_lot(self, 'LOT-VALID', prod_id, +10)
        lot_expired_id = self.create_lot(self, 'LOT-EXPIRED', prod_id, -10)

        # Orders 7 items for shop 1, 3 expired and 4 valid.
        shop_1_id = self.ref('pc_connect_master.shop1')
        self.obtain_qty(self, prod_id, 3, shop_1_id, lot_id=lot_expired_id)
        self.obtain_qty(self, prod_id, 4, shop_1_id, lot_id=lot_valid_id)

        # Order 3 items for shop 2, all of them valid.
        shop_2_id = self.ref('pc_connect_master.shop2')
        self.obtain_qty(self, prod_id, 3, shop_2_id, lot_id=lot_valid_id)

        prod = prod_obj.browse(cr, uid, prod_id, context=ctx)
        self.assertEqual(prod.qty_available, 10)
        self.assertEqual(prod.incoming_qty, 0)
        self.assertEqual(prod.outgoing_qty, 0)
        self.assertEqual(prod.virtual_available, 10)
        self.assertEqual(prod.qty_on_assigned_moves, 0)
        self.assertEqual(prod.product_reservation_qty, 0)
        self.assertEqual(prod.qty_on_sale, 7)

        # Consumes 2 items of shop 1.
        order_id = self.consume_qty(self, prod_id, 2, shop_1_id)

        prod = prod_obj.browse(cr, uid, prod_id, context=ctx)
        self.assertEqual(prod.qty_available, 10)
        self.assertEqual(prod.incoming_qty, 0)
        self.assertEqual(prod.outgoing_qty, 0)
        self.assertEqual(prod.virtual_available, 10)
        self.assertEqual(prod.qty_on_assigned_moves, 0)
        self.assertEqual(prod.product_reservation_qty, 2)
        self.assertEqual(prod.qty_on_sale, 5)

        # Validates the order.
        self.validate_order(self, order_id)

        prod = prod_obj.browse(cr, uid, prod_id, context=ctx)
        self.assertEqual(prod.qty_available, 10)
        self.assertEqual(prod.incoming_qty, 0)
        self.assertEqual(prod.outgoing_qty, -2)
        self.assertEqual(prod.virtual_available, 8)
        self.assertEqual(prod.qty_on_assigned_moves, 0)
        self.assertEqual(prod.product_reservation_qty, 0)
        self.assertEqual(prod.qty_on_sale, 5)

        # Assigns the two items from the order.
        self.assign_picking_from_order(self, order_id)

        prod = prod_obj.browse(cr, uid, prod_id, context=ctx)
        self.assertEqual(prod.qty_available, 10)
        self.assertEqual(prod.incoming_qty, 0)
        self.assertEqual(prod.outgoing_qty, -2)
        self.assertEqual(prod.virtual_available, 8)
        self.assertEqual(prod.qty_on_assigned_moves, 2)
        self.assertEqual(prod.product_reservation_qty, 0)
        self.assertEqual(prod.qty_on_sale, 5)

        # Delivers the quantities.
        order = self.registry('sale.order').browse(cr, uid, order_id, context=ctx)
        picking_ids = [p.id for p in order.picking_ids]
        self.deliver_assigned_picking(self, picking_ids)

        prod = prod_obj.browse(cr, uid, prod_id, context=ctx)
        self.assertEqual(prod.qty_available, 8)
        self.assertEqual(prod.incoming_qty, 0)
        self.assertEqual(prod.outgoing_qty, 0)
        self.assertEqual(prod.virtual_available, 8)
        self.assertEqual(prod.qty_on_assigned_moves, 0)
        self.assertEqual(prod.product_reservation_qty, 0)
        self.assertEqual(prod.qty_on_sale, 5)

    @skipIf(UNDER_DEVELOPMENT, UNDER_DEVELOPMENT_TEXT)
    def test_fields_with_shops__lotted(self):
        """ Tests the fields alone, querying for the quantities for a shop.
            The products are not lotted.
        """
        cr, uid, ctx = self.cr, self.uid, self.context
        prod_obj = self.registry('product.product')

        prod_id = self.create_product(self, {'name': 'PROD-1'})

        # Creates two lots, one of them expired.
        lot_valid_id = self.create_lot(self, 'LOT-VALID', prod_id, +10)
        lot_expired_id = self.create_lot(self, 'LOT-EXPIRED', prod_id, -10)

        # Orders 7 items for shop 1, 3 expired and 4 valid.
        shop_1_id = self.ref('pc_connect_master.shop1')
        self.obtain_qty(self, prod_id, 3, shop_1_id, lot_id=lot_expired_id)
        self.obtain_qty(self, prod_id, 4, shop_1_id, lot_id=lot_valid_id)

        # Order 3 items for shop 2, all of them valid.
        shop_2_id = self.ref('pc_connect_master.shop2')
        self.obtain_qty(self, prod_id, 3, shop_2_id, lot_id=lot_valid_id)

        # Checks the initial quantities for each shop, and joined.
        ctx.update({'shop': shop_1_id})
        prod = prod_obj.browse(cr, uid, prod_id, context=ctx)
        self.assertEqual(prod.qty_available, 7)
        self.assertEqual(prod.incoming_qty, 0)
        self.assertEqual(prod.outgoing_qty, 0)
        self.assertEqual(prod.virtual_available, 7)
        self.assertEqual(prod.qty_on_assigned_moves, 0)
        self.assertEqual(prod.product_reservation_qty, 0)
        self.assertEqual(prod.qty_on_sale, 4)

        ctx.update({'shop': shop_2_id})
        prod = prod_obj.browse(cr, uid, prod_id, context=ctx)
        self.assertEqual(prod.qty_available, 3)
        self.assertEqual(prod.incoming_qty, 0)
        self.assertEqual(prod.outgoing_qty, 0)
        self.assertEqual(prod.virtual_available, 3)
        self.assertEqual(prod.qty_on_assigned_moves, 0)
        self.assertEqual(prod.product_reservation_qty, 0)
        self.assertEqual(prod.qty_on_sale, 3)

        if 'shop' in ctx:
            del ctx['shop']
        prod = prod_obj.browse(cr, uid, prod_id, context=ctx)
        self.assertEqual(prod.qty_available, 10)
        self.assertEqual(prod.incoming_qty, 0)
        self.assertEqual(prod.outgoing_qty, 0)
        self.assertEqual(prod.virtual_available, 10)
        self.assertEqual(prod.qty_on_assigned_moves, 0)
        self.assertEqual(prod.product_reservation_qty, 0)
        self.assertEqual(prod.qty_on_sale, 7)

        # Consumes 2 items of shop 1.
        order_id = self.consume_qty(self, prod_id, 2, shop_1_id)

        ctx.update({'shop': shop_1_id})
        prod = prod_obj.browse(cr, uid, prod_id, context=ctx)
        self.assertEqual(prod.qty_available, 7)
        self.assertEqual(prod.incoming_qty, 0)
        self.assertEqual(prod.outgoing_qty, 0)
        self.assertEqual(prod.virtual_available, 7)
        self.assertEqual(prod.qty_on_assigned_moves, 0)
        self.assertEqual(prod.product_reservation_qty, 2)
        self.assertEqual(prod.qty_on_sale, 2)

        # Validates the order.
        self.validate_order(self, order_id)

        prod = prod_obj.browse(cr, uid, prod_id, context=ctx)
        self.assertEqual(prod.qty_available, 7)
        self.assertEqual(prod.incoming_qty, 0)
        self.assertEqual(prod.outgoing_qty, -2)
        self.assertEqual(prod.virtual_available, 5)
        self.assertEqual(prod.qty_on_assigned_moves, 0)
        self.assertEqual(prod.product_reservation_qty, 0)
        self.assertEqual(prod.qty_on_sale, 2)

        # Assigns the two items from the order.
        self.assign_picking_from_order(self, order_id)

        prod = prod_obj.browse(cr, uid, prod_id, context=ctx)
        self.assertEqual(prod.qty_available, 7)
        self.assertEqual(prod.incoming_qty, 0)
        self.assertEqual(prod.outgoing_qty, -2)
        self.assertEqual(prod.virtual_available, 5)
        self.assertEqual(prod.qty_on_assigned_moves, 2)
        self.assertEqual(prod.product_reservation_qty, 0)
        self.assertEqual(prod.qty_on_sale, 2)

        # Delivers the quantities.
        order = self.registry('sale.order').browse(cr, uid, order_id, context=ctx)
        picking_ids = [p.id for p in order.picking_ids]
        self.deliver_assigned_picking(self, picking_ids)

        prod = prod_obj.browse(cr, uid, prod_id, context=ctx)
        self.assertEqual(prod.qty_available, 5)
        self.assertEqual(prod.incoming_qty, 0)
        self.assertEqual(prod.outgoing_qty, 0)
        self.assertEqual(prod.virtual_available, 5)
        self.assertEqual(prod.qty_on_assigned_moves, 0)
        self.assertEqual(prod.product_reservation_qty, 0)
        self.assertEqual(prod.qty_on_sale, 2)

        # Checks the quantity for the other shop, that must remain equal.
        ctx.update({'shop': shop_2_id})
        prod = prod_obj.browse(cr, uid, prod_id, context=ctx)
        self.assertEqual(prod.qty_available, 3)
        self.assertEqual(prod.incoming_qty, 0)
        self.assertEqual(prod.outgoing_qty, 0)
        self.assertEqual(prod.virtual_available, 3)
        self.assertEqual(prod.qty_on_assigned_moves, 0)
        self.assertEqual(prod.product_reservation_qty, 0)
        self.assertEqual(prod.qty_on_sale, 3)

        # Checks the quantity for both shops joined, that must be lower.
        if 'shop' in ctx:
            del ctx['shop']
        prod = prod_obj.browse(cr, uid, prod_id, context=ctx)
        self.assertEqual(prod.qty_available, 8)
        self.assertEqual(prod.incoming_qty, 0)
        self.assertEqual(prod.outgoing_qty, 0)
        self.assertEqual(prod.virtual_available, 8)
        self.assertEqual(prod.qty_on_assigned_moves, 0)
        self.assertEqual(prod.product_reservation_qty, 0)
        self.assertEqual(prod.qty_on_sale, 5)

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
