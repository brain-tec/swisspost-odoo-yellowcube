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

import time
from unittest2 import skipIf
from collections import defaultdict, namedtuple
from openerp.tests import common
from openerp.osv import fields, orm
from openerp.addons.pc_sale_order_automation.sale_order_ext import \
    SaleOrderAutomationResult


UNDER_DEVELOPMENT = False
UNDER_DEVELOPMENT_TEXT = 'Test was skipped because of being under development'


# Encodes the different quantities over a product.
Qty = namedtuple("Qty", "qty_available "
                        "incoming_qty "
                        "outgoing_qty "
                        "virtual_available "
                        "product_reservation_qty "
                        "qty_on_sale "
                        "qty_on_assigned_moves")


class TestAssignationsOneAndDirect(common.TransactionCase):

    def setUp(self):
        super(TestAssignationsOneAndDirect, self).setUp()
        self.context = {}

        # The unit of measure to use in all the tests, to simplify.
        self.uom_id = self.ref('product.product_uom_unit')

    def create_product(self, vals):
        """ Creates a product, without stock.
        """
        cr, uid, ctx = self.cr, self.uid, self.context
        prod_obj = self.registry('product.product')

        create_vals = {
            'name': vals.get('name', 'Test Product {0}'.format(time.time())),
            'uom_id': self.uom_id,
            'uom_po_id': self.uom_id,
        }

        prod_id = prod_obj.create(cr, uid, create_vals, context=ctx)
        return prod_id

    def create_sale_order(self, defaults=None):
        """ Creates a sale order with default values, that can be overridden
            with the values sent as the 'defaults' parameter.
        """
        if defaults is None:
            defaults = {}
        cr, uid, ctx = self.cr, self.uid, self.context
        order_obj = self.registry('sale.order')

        partner_id = self.ref('base.res_partner_2')
        payment_epaid_id = self.ref('pc_connect_master.payment_method_epaid')
        vals = {
            'partner_id': partner_id,
            'partner_invoice_id': partner_id,
            'partner_shipping_id': partner_id,
            'date_order': fields.date.today(),
            'payment_method_id': payment_epaid_id,
            'carrier_id': self.ref('delivery.delivery_carrier'),
            'pricelist_id': self.ref('product.list0'),
        }
        vals.update(defaults)

        order_id = order_obj.create(cr, uid, vals, context=ctx)
        return order_id

    def create_sale_order_line(self, vals):
        """ Creates a sale order line with the values indicated in
            the parameter 'vals'.
        """
        cr, uid, ctx = self.cr, self.uid, self.context
        line_obj = self.registry('sale.order.line')

        create_vals = {
            'product_id': vals['product_id'],
            'name': vals.get('name', 'Default Name'),
            'product_uom_qty': vals['product_uom_qty'],
            'price_unit': vals.get('price_unit', 1),
            'order_id': vals['order_id'],
            'product_uom': self.uom_id,
        }

        order_line_id = line_obj.create(cr, uid, create_vals, context=ctx)
        return order_line_id

    def order_qty(self, qty_per_product):
        """ Orders the amount of UNITS indicated for the product received.
            qty_per_product is a dictionary with keys being product's ID
            and value being the quantity (in Units) to order for it.
        """
        cr, uid, ctx = self.cr, self.uid, self.context
        picking_in_obj = self.registry('stock.picking.in')
        move_obj = self.registry('stock.move')
        prod_obj = self.registry('product.product')
        datetime_now = fields.datetime.now()

        # Creates a stock picking over the product.
        supplier_id = self.ref('base.res_partner_1')
        create_vals = {
            'partner_id': supplier_id,
            'date': fields.datetime.now(),
            'move_type': 'one',
        }
        picking_id = picking_in_obj.create(cr, uid, create_vals, context=ctx)

        # Creates the picking's lines.
        location_origin_id = self.ref('stock.stock_location_suppliers')
        location_destination_id= self.ref('stock.stock_location_stock')
        for prod_id, prod_qty in qty_per_product.iteritems():
            move_obj.create(cr, uid, {
                'name': 'Move for product ID={0}'.format(prod_id),
                'location_id': location_origin_id,
                'location_dest_id': location_destination_id,
                'product_id': prod_id,
                'product_qty': prod_qty,
                'date': datetime_now,
                'date_expected': datetime_now,
                'picking_id': picking_id,
                'product_uom': self.uom_id,
            }, context=ctx)

        # Validates the picking.in.
        qty_on_hand = defaultdict(lambda: 0)
        incoming = defaultdict(lambda: 0)
        outgoing = defaultdict(lambda: 0)
        forecasted_qty = defaultdict(lambda: 0)
        qty_on_assigned_moves = defaultdict(lambda: 0)
        reservations_on_quotations = defaultdict(lambda: 0)
        qty_available = defaultdict(lambda: 0)
        for prod_id, _ in qty_per_product.iteritems():
            prod = prod_obj.browse(cr, uid, prod_id, context=ctx)
            qty_on_hand[prod_id] = prod.qty_available
            incoming[prod_id] = prod.incoming_qty
            outgoing[prod_id] = prod.outgoing_qty
            forecasted_qty[prod_id] = prod.virtual_available
            qty_on_assigned_moves[prod_id] = prod.qty_on_assigned_moves
            reservations_on_quotations[prod_id] = prod.product_reservation_qty
            qty_available[prod_id] = prod.qty_on_sale

        picking_in_obj.draft_force_assign(cr, uid, [picking_id])

        # After validating the picking.in, the incoming quantity and the
        # forecasted quantity are the only fields that change.
        for prod_id, prod_qty in qty_per_product.iteritems():
            prod = prod_obj.browse(cr, uid, prod_id, context=ctx)

            self.assertEqual(qty_on_hand[prod_id], prod.qty_available,
                             "Quantity on Hand shouldn't change, but it did.")
            self.assertEqual(incoming[prod_id] + qty_per_product[prod_id], prod.incoming_qty,
                             "Incoming should had changed, but it did not.")
            self.assertEqual(outgoing[prod_id], prod.outgoing_qty,
                             "Outgoing shouldn't change, but it did.")
            self.assertEqual(forecasted_qty[prod_id] + prod.virtual_available, prod.virtual_available,
                             "Forecasted Quantity should had changed, but it did not.")
            self.assertEqual(qty_on_assigned_moves[prod_id], prod.qty_on_assigned_moves,
                             "Qty Assigned on Moves shouldn't change, but it did.")
            self.assertEqual(reservations_on_quotations[prod_id], prod.product_reservation_qty,
                             "Reservations shouldn't change, but it did.")
            self.assertEqual(qty_available[prod_id], prod.qty_on_sale,
                             "Quantity Available shouldn't change, but it did.")

        # Receives the picking.in.
        partials = self._get_partials(picking_id)
        self.receive_picking_in(picking_id, partials)

        # After receiving the picking.in, the quantities are moved to the
        # quantity on hand and quantity available, and are removed from the
        # incoming quantities.
        for prod_id, prod_qty in qty_per_product.iteritems():
            prod = prod_obj.browse(cr, uid, prod_id, context=ctx)

            self.assertEqual(qty_on_hand[prod_id] + qty_per_product[prod_id], prod.qty_available,
                             "Quantity on Hand should change, but it didn't.")
            self.assertEqual(incoming[prod_id], prod.incoming_qty,
                             "Incoming quantity shoudn't change, but it did.")
            self.assertEqual(outgoing[prod_id], prod.outgoing_qty,
                             "Outgoing quantity shoudn't change, but it did.")
            self.assertEqual(forecasted_qty[prod_id] + qty_per_product[prod_id], prod.virtual_available,
                             "Forecasted quantity shoud change, but it didn't")
            self.assertEqual(qty_on_assigned_moves[prod_id], prod.qty_on_assigned_moves,
                             "Qty Assigned on Moves shoudn't change, but it did.")
            self.assertEqual(reservations_on_quotations[prod_id], prod.product_reservation_qty,
                             "Reservations shoudn't change, but it did.")
            self.assertEqual(qty_available[prod_id] + qty_per_product[prod_id], prod.qty_on_sale,
                             "Qty Available should change, but it didn't.")

        return True

    def _get_partials(self, picking_id):
        """ Receives a picking and returns a data structure which is the one
            that expects the method do_partial() of the stock.picking.
        """
        cr, uid, ctx = self.cr, self.uid, self.context
        picking_obj = self.registry('stock.picking')

        partials = {}
        picking = picking_obj.browse(cr, uid, picking_id, context=ctx)
        for move in picking.move_lines:
            partials_key = 'move{0}'.format(move.id)
            partials_values = {
                'product_qty': move.product_qty,
            }
            partials[partials_key] = partials_values

        return partials

    def receive_picking_in(self, picking_id, partials):
        """ Receives the products indicated in the structure 'partials'
            over the picking received. 'partials' is the same
            data structure that expects the method do_partial() of the
            stock.picking.
        """
        cr, uid, ctx = self.cr, self.uid, self.context

        move_obj = self.registry('stock.move')
        partial_picking_obj = self.registry('stock.partial.picking')
        partial_picking_line_obj = self.registry('stock.partial.picking.line')

        partial_picking_id = partial_picking_obj.create(cr, uid, {
            'date': fields.date.today(),
            'picking_id': picking_id,
        }, context=ctx)
        for key, values in partials.iteritems():
            move_id = int(key.split('move')[-1])
            move = move_obj.browse(cr, uid, move_id, context=ctx)
            partial_picking_line_obj.create(cr, uid, {
                'product_id': move.product_id.id,
                'quantity': values['product_qty'],
                'product_uom': move.product_uom.id,
                'prodlot_id': move.prodlot_id.id,
                'wizard_id': partial_picking_id,
                'location_id': move.location_id.id,
                'location_dest_id': move.location_dest_id.id,
                'move_id': move.id,
            }, context=ctx)
        partial_picking_obj.do_partial(
            cr, uid, [partial_picking_id], context=ctx)

    def check_qty(self, product_id, expected_qty):
        """ Receives a product's ID and an instance of Qty, with the
            values that are expected for the different quantities associated
            to a product.
        """
        prod = self.registry('product.product').browse(
            self.cr, self.uid, product_id, context=self.context)
        self.assertEqual(prod.qty_available, expected_qty.qty_available)
        self.assertEqual(prod.incoming_qty, expected_qty.incoming_qty)
        self.assertEqual(prod.outgoing_qty, expected_qty.outgoing_qty)
        self.assertEqual(prod.virtual_available, expected_qty.virtual_available)
        self.assertEqual(prod.product_reservation_qty, expected_qty.product_reservation_qty)
        self.assertEqual(prod.qty_on_sale, expected_qty.qty_on_sale)
        self.assertEqual(prod.qty_on_assigned_moves, expected_qty.qty_on_assigned_moves)

    @skipIf(UNDER_DEVELOPMENT, UNDER_DEVELOPMENT_TEXT)
    def test_assignation_one_without_lots_enough_quantities(self):
        """ Tests the picking_policy set to one over a sale order
            which have enough quantities for the products it needs.
        """
        cr, uid, ctx = self.cr, self.uid, self.context
        order_obj = self.registry('sale.order')
        picking_out_obj = self.registry('stock.picking.out')
        conf_obj = self.registry('configuration.data')

        conf_id = self.ref('pc_config.default_configuration_data')
        conf_obj.write(cr, uid, conf_id, {'default_picking_policy': 'keep'},
                       context=ctx)

        product_1_qty = 7
        product_2_qty = 5

        # Creates two products and orders some quantities for them.
        product_1_id = self.create_product({'name': 'Test Product 1'})
        product_2_id = self.create_product({'name': 'Test Product 2'})
        self.order_qty({
            product_1_id: product_1_qty,
            product_2_id: product_2_qty,
        })

        # Checks the quantities up to this point.
        self.check_qty(product_1_id, Qty(7, 0, 0, 7, 0, 7, 0))
        self.check_qty(product_2_id, Qty(5, 0, 0, 5, 0, 5, 0))

        # Creates a sale order and associates the products to them.
        order_id = self.create_sale_order({
            'picking_policy': 'one',
        })
        self.create_sale_order_line({
            'product_id': product_1_id,
            'name': 'Test Product 1',
            'product_uom_qty': product_1_qty,
            'order_id': order_id,
        })
        self.create_sale_order_line({
            'product_id': product_2_id,
            'name': 'Test Product 2',
            'product_uom_qty': product_2_qty,
            'order_id': order_id,
        })

        # Checks the quantities up to this point.
        self.check_qty(product_1_id, Qty(7, 0, 0, 7, 7, 0, 0))
        self.check_qty(product_2_id, Qty(5, 0, 0, 5, 5, 0, 0))

        # Validates the order. This creates its associated picking.
        order_obj.action_button_confirm(cr, uid, [order_id], context=ctx)

        # We check that the picking don't have any items assigned.
        order = order_obj.browse(cr, uid, order_id, context=ctx)
        self.assertEqual(len(order.picking_ids), 1,
                         "The order should have just one picking but "
                         "it had {0} instead.".format(len(order.picking_ids)))
        picking = order.picking_ids[0]
        self.assertEqual(picking.state, 'confirmed',
                         'The picking should be in state confirmed, '
                         'but is on state {0}.'.format(picking.state))
        for move in picking.move_lines:
            self.assertEqual(move.state, 'confirmed')

        # Checks the quantities up to this point.
        self.check_qty(product_1_id, Qty(7, 0, -7, 0, 0, 0, 0))
        self.check_qty(product_2_id, Qty(5, 0, -5, 0, 0, 0, 0))

        # Attempts to send the pickings. Since we have enough goods
        # we must assign the items to the picking.
        soa_info = SaleOrderAutomationResult()
        order_obj.do_assignation_one(cr, uid, order_id, soa_info, context=ctx)
        self.assertEqual(soa_info.message, "Does the assignation 'one'.")
        self.assertEqual(soa_info.next_state, "print_deliveryorder_in_local")

        # All the lines of the picking must be assigned and the picking also.
        picking = picking_out_obj.browse(cr, uid, picking.id, context=ctx)
        self.assertEqual(picking.state, 'assigned')
        for move in picking.move_lines:
            self.assertEqual(move.state, 'assigned')

        # Checks the quantities up to this point.
        self.check_qty(product_1_id, Qty(7, 0, -7, 0, 0, 0, 7))
        self.check_qty(product_2_id, Qty(5, 0, -5, 0, 0, 0, 5))

    @skipIf(UNDER_DEVELOPMENT, UNDER_DEVELOPMENT_TEXT)
    def test_assignation_one_without_lots_not_enough_quantities(self):
        """ Tests the picking_policy set to one over a sale order
            which doesn't have enough quantities for the products it needs.
        """
        cr, uid, ctx = self.cr, self.uid, self.context
        order_obj = self.registry('sale.order')
        picking_out_obj = self.registry('stock.picking.out')
        conf_obj = self.registry('configuration.data')

        conf_id = self.ref('pc_config.default_configuration_data')
        conf_obj.write(cr, uid, conf_id, {'default_picking_policy': 'keep'},
                       context=ctx)

        product_1_qty = 7
        product_2_qty = 5

        # Creates two products and orders some quantities for them.
        # We order one unit less than the quantity that we need.
        product_1_id = self.create_product({'name': 'Test Product 1'})
        product_2_id = self.create_product({'name': 'Test Product 2'})
        self.order_qty({
            product_1_id: product_1_qty - 1,
            product_2_id: product_2_qty - 1,
        })

        # Checks the quantities up to this point.
        self.check_qty(product_1_id, Qty(6, 0, 0, 6, 0, 6, 0))
        self.check_qty(product_2_id, Qty(4, 0, 0, 4, 0, 4, 0))

        # Creates a sale order and associates the products to them.
        order_id = self.create_sale_order({
            'picking_policy': 'one',
        })
        self.create_sale_order_line({
            'product_id': product_1_id,
            'name': 'Test Product 1',
            'product_uom_qty': product_1_qty,
            'order_id': order_id,
        })
        self.create_sale_order_line({
            'product_id': product_2_id,
            'name': 'Test Product 2',
            'product_uom_qty': product_2_qty,
            'order_id': order_id,
        })

        # Checks the quantities up to this point.
        self.check_qty(product_1_id, Qty(6, 0, 0, 6, 7, -1, 0))
        self.check_qty(product_2_id, Qty(4, 0, 0, 4, 5, -1, 0))

        # Validates the order. This creates its associated picking.
        order_obj.action_button_confirm(cr, uid, [order_id], context=ctx)

        # We check that the picking don't have any items assigned.
        order = order_obj.browse(cr, uid, order_id, context=ctx)
        self.assertEqual(len(order.picking_ids), 1,
                         "The order should have just one picking but "
                         "it had {0} instead.".format(len(order.picking_ids)))
        picking = order.picking_ids[0]
        self.assertEqual(picking.state, 'confirmed',
                         'The picking should be in state confirmed, '
                         'but is on state {0}.'.format(picking.state))
        for move in picking.move_lines:
            self.assertEqual(move.state, 'confirmed')

        # Checks the quantities up to this point.
        self.check_qty(product_1_id, Qty(6, 0, -7, -1, 0, -1, 0))
        self.check_qty(product_2_id, Qty(4, 0, -5, -1, 0, -1, 0))

        # Attempts to send the pickings. Since we have enough goods
        # we must assign the items to the picking.
        soa_info = SaleOrderAutomationResult()
        with self.assertRaises(orm.except_orm):
            order_obj.do_assignation_one(cr, uid, order_id, soa_info, ctx)

        # All the lines of the picking must be kept confirmed and also
        # the picking.
        picking = picking_out_obj.browse(cr, uid, picking.id, context=ctx)
        self.assertEqual(picking.state, 'confirmed')
        for move in picking.move_lines:
            self.assertEqual(move.state, 'confirmed')

        # Checks the quantities up to this point.
        self.check_qty(product_1_id, Qty(6, 0, -7, -1, 0, -1, 0))
        self.check_qty(product_2_id, Qty(4, 0, -5, -1, 0, -1, 0))

    @skipIf(UNDER_DEVELOPMENT, UNDER_DEVELOPMENT_TEXT)
    def test_assignation_direct_without_lots_enough_quantities(self):
        """ Tests the picking_policy set to direct over a sale order
            which have enough quantities for the products it needs. So the
            result of this one is like in the case of direct one with enough
            quantities.
        """
        cr, uid, ctx = self.cr, self.uid, self.context
        order_obj = self.registry('sale.order')
        picking_out_obj = self.registry('stock.picking.out')
        conf_obj = self.registry('configuration.data')

        conf_id = self.ref('pc_config.default_configuration_data')
        conf_obj.write(cr, uid, conf_id, {'default_picking_policy': 'keep'},
                       context=ctx)

        product_1_qty = 7
        product_2_qty = 5

        # Creates two products and orders some quantities for them.
        product_1_id = self.create_product({'name': 'Test Product 1'})
        product_2_id = self.create_product({'name': 'Test Product 2'})
        self.order_qty({
            product_1_id: product_1_qty,
            product_2_id: product_2_qty,
        })

        # Checks the quantities up to this point.
        self.check_qty(product_1_id, Qty(7, 0, 0, 7, 0, 7, 0))
        self.check_qty(product_2_id, Qty(5, 0, 0, 5, 0, 5, 0))

        # Creates a sale order and associates the products to them.
        order_id = self.create_sale_order({
            'picking_policy': 'direct',
        })
        self.create_sale_order_line({
            'product_id': product_1_id,
            'name': 'Test Product 1',
            'product_uom_qty': product_1_qty,
            'order_id': order_id,
        })
        self.create_sale_order_line({
            'product_id': product_2_id,
            'name': 'Test Product 2',
            'product_uom_qty': product_2_qty,
            'order_id': order_id,
        })

        # Checks the quantities up to this point.
        self.check_qty(product_1_id, Qty(7, 0, 0, 7, 7, 0, 0))
        self.check_qty(product_2_id, Qty(5, 0, 0, 5, 5, 0, 0))

        # Validates the order. This creates its associated picking.
        order_obj.action_button_confirm(cr, uid, [order_id], context=ctx)

        # We check that the picking don't have any items assigned.
        order = order_obj.browse(cr, uid, order_id, context=ctx)
        self.assertEqual(len(order.picking_ids), 1,
                         "The order should have just one picking but "
                         "it had {0} instead.".format(len(order.picking_ids)))
        picking = order.picking_ids[0]
        self.assertEqual(picking.state, 'confirmed',
                         'The picking should be in state confirmed, '
                         'but is on state {0}.'.format(picking.state))
        for move in picking.move_lines:
            self.assertEqual(move.state, 'confirmed')

        # Checks the quantities up to this point.
        self.check_qty(product_1_id, Qty(7, 0, -7, 0, 0, 0, 0))
        self.check_qty(product_2_id, Qty(5, 0, -5, 0, 0, 0, 0))

        # Attempts to send the pickings. Since we have enough goods
        # we must assign the items to the picking.
        soa_info = SaleOrderAutomationResult()
        order_obj.do_assignation_direct(cr, uid, order_id, False, soa_info,
                                        ctx)
        self.assertEqual(soa_info.message, "Does the assignation 'direct'.")
        self.assertEqual(soa_info.next_state, "print_deliveryorder_in_local")

        # All the lines of the picking must be assigned and the picking also.
        picking = picking_out_obj.browse(cr, uid, picking.id, context=ctx)
        self.assertEqual(picking.state, 'assigned')
        for move in picking.move_lines:
            self.assertEqual(move.state, 'assigned')

        # Checks the quantities up to this point.
        self.check_qty(product_1_id, Qty(7, 0, -7, 0, 0, 0, 7))
        self.check_qty(product_2_id, Qty(5, 0, -5, 0, 0, 0, 5))

    @skipIf(UNDER_DEVELOPMENT, UNDER_DEVELOPMENT_TEXT)
    def test_assignation_direct_without_lots_partial_quantities(self):
        """ Tests the assignation-direct for the case in which we have
            a partial amount of the goods needed, which results in a
            back-order.
        """
        cr, uid, ctx = self.cr, self.uid, self.context
        order_obj = self.registry('sale.order')
        picking_out_obj = self.registry('stock.picking.out')
        conf_obj = self.registry('configuration.data')

        conf_id = self.ref('pc_config.default_configuration_data')
        conf_obj.write(cr, uid, conf_id, {'default_picking_policy': 'keep'},
                       context=ctx)

        product_1_qty = 7
        product_2_qty = 5

        # Creates two products and orders some quantities for them.
        product_1_id = self.create_product({'name': 'Test Product 1'})
        product_2_id = self.create_product({'name': 'Test Product 2'})
        self.order_qty({
            product_1_id: product_1_qty - 1,  # 1 units missing for product 1.
            product_2_id: product_2_qty - 2,  # 2 units missing for product 2.
        })

        # Checks the quantities up to this point.
        self.check_qty(product_1_id, Qty(6, 0, 0, 6, 0, 6, 0))
        self.check_qty(product_2_id, Qty(3, 0, 0, 3, 0, 3, 0))

        # Creates a sale order and associates the products to them.
        order_id = self.create_sale_order({
            'picking_policy': 'direct',
        })
        self.create_sale_order_line({
            'product_id': product_1_id,
            'name': 'Test Product 1',
            'product_uom_qty': product_1_qty,
            'order_id': order_id,
        })
        self.create_sale_order_line({
            'product_id': product_2_id,
            'name': 'Test Product 2',
            'product_uom_qty': product_2_qty,
            'order_id': order_id,
        })

        # Checks the quantities up to this point.
        self.check_qty(product_1_id, Qty(6, 0, 0, 6, 7, -1, 0))
        self.check_qty(product_2_id, Qty(3, 0, 0, 3, 5, -2, 0))

        # Validates the order. This creates its associated picking.
        order_obj.action_button_confirm(cr, uid, [order_id], context=ctx)

        # We check that the picking don't have any items assigned.
        order = order_obj.browse(cr, uid, order_id, context=ctx)
        self.assertEqual(len(order.picking_ids), 1,
                         "The order should have just one picking but "
                         "it had {0} instead.".format(len(order.picking_ids)))
        picking = order.picking_ids[0]
        self.assertEqual(picking.state, 'confirmed',
                         'The picking should be in state confirmed, '
                         'but is on state {0}.'.format(picking.state))
        for move in picking.move_lines:
            self.assertEqual(move.state, 'confirmed')

        # Checks the quantities up to this point.
        self.check_qty(product_1_id, Qty(6, 0, -7, -1, 0, -1, 0))
        self.check_qty(product_2_id, Qty(3, 0, -5, -2, 0, -2, 0))

        # Attempts to send the pickings. Since we have some of the quantities
        # that have to be sent, then we have to create a back-order.
        soa_info = SaleOrderAutomationResult()
        order_obj.do_assignation_direct(cr, uid, order_id, False, soa_info,
                                        ctx)
        self.assertEqual(soa_info.message, "Does the assignation 'direct'.")
        self.assertEqual(soa_info.next_state, "print_deliveryorder_in_local")

        # Checks that we have two pickings now associated to the sale order.
        order = order_obj.browse(cr, uid, order_id, context=ctx)
        self.assertEqual(len(order.picking_ids), 2,
                         "There should be 2 pickings for the order but there "
                         "are {0} instead.".format(len(order.picking_ids)))

        # Checks that the picking which is the back-order has the pending
        # quantities (this is this way in v7).
        all_pickings = [picking.id for picking in order.picking_ids]
        backorder_id = picking.id
        ready_picking_id = \
            list(set(all_pickings) - set([backorder_id]))[0]

        # All the lines of the ready picking must be assigned,
        # and the picking also.
        ready_picking = picking_out_obj.browse(cr, uid, ready_picking_id,
                                               context=ctx)
        self.assertEqual(ready_picking.state, 'assigned')
        self.assertEqual(len(ready_picking.move_lines), 2,
                         "The ready picking should have 2 lines, but has {0} "
                         "instead.". format(len(ready_picking.move_lines)))
        for move in ready_picking.move_lines:
            self.assertEqual(move.state, 'assigned')

        # All the lines of the backorder must be confirmed,
        # and the picking also.
        backorder = picking_out_obj.browse(cr, uid, backorder_id, context=ctx)
        self.assertEqual(backorder.state, 'confirmed')
        self.assertEqual(len(backorder.move_lines), 2,
                         "The backorder should have 2 lines, but has {0} "
                         "instead.".format(len(backorder.move_lines)))
        for move in backorder.move_lines:
            self.assertEqual(move.state, 'confirmed')

    @skipIf(UNDER_DEVELOPMENT, UNDER_DEVELOPMENT_TEXT)
    def test_assignation_direct_without_lots_no_quantities(self):
        """ Tests the assignation-direct for the case in which we have
            absolutely no quantities for any of the products that go on
            the sale.order.
        """
        cr, uid, ctx = self.cr, self.uid, self.context
        order_obj = self.registry('sale.order')
        picking_out_obj = self.registry('stock.picking.out')
        conf_obj = self.registry('configuration.data')

        conf_id = self.ref('pc_config.default_configuration_data')
        conf_obj.write(cr, uid, conf_id, {'default_picking_policy': 'keep'},
                       context=ctx)

        product_1_qty = 7
        product_2_qty = 5

        # Creates two products but doesn't order quantities for them.
        product_1_id = self.create_product({'name': 'Test Product 1'})
        product_2_id = self.create_product({'name': 'Test Product 2'})

        # Checks the quantities up to this point.
        self.check_qty(product_1_id, Qty(0, 0, 0, 0, 0, 0, 0))
        self.check_qty(product_2_id, Qty(0, 0, 0, 0, 0, 0, 0))

        # Creates a sale order and associates the products to them.
        order_id = self.create_sale_order({
            'picking_policy': 'direct',
        })
        self.create_sale_order_line({
            'product_id': product_1_id,
            'name': 'Test Product 1',
            'product_uom_qty': product_1_qty,
            'order_id': order_id,
        })
        self.create_sale_order_line({
            'product_id': product_2_id,
            'name': 'Test Product 2',
            'product_uom_qty': product_2_qty,
            'order_id': order_id,
        })

        # Checks the quantities up to this point.
        self.check_qty(product_1_id, Qty(0, 0, 0, 0, 7, -7, 0))
        self.check_qty(product_2_id, Qty(0, 0, 0, 0, 5, -5, 0))

        # Validates the order. This creates its associated picking.
        order_obj.action_button_confirm(cr, uid, [order_id], context=ctx)

        # We check that the picking don't have any items assigned.
        order = order_obj.browse(cr, uid, order_id, context=ctx)
        self.assertEqual(len(order.picking_ids), 1,
                         "The order should have just one picking but "
                         "it had {0} instead.".format(len(order.picking_ids)))
        picking = order.picking_ids[0]
        self.assertEqual(picking.state, 'confirmed',
                         'The picking should be in state confirmed, '
                         'but is on state {0}.'.format(picking.state))
        for move in picking.move_lines:
            self.assertEqual(move.state, 'confirmed')

        # Checks the quantities up to this point.
        self.check_qty(product_1_id, Qty(0, 0, -7, -7, 0, -7, 0))
        self.check_qty(product_2_id, Qty(0, 0, -5, -5, 0, -5, 0))

        # Attempts to send the pickings. Since we don't have enough goods it'll
        # simply do nothing (since the other option was to remove the existing
        # picking and create a backorder with *all* the goods and try again).
        soa_info = SaleOrderAutomationResult()
        order_obj.do_assignation_direct(cr, uid, order_id, False, soa_info, ctx)
        self.assertEqual(soa_info.message, "Does the assignation 'direct'.")
        self.assertEqual(soa_info.next_state, "deliveryorder_assignation_direct")

        # The picking must remain untouched.
        picking = picking_out_obj.browse(cr, uid, picking.id, context=ctx)
        self.assertEqual(picking.state, 'confirmed')
        for move in picking.move_lines:
            self.assertEqual(move.state, 'confirmed')

        # Checks the quantities up to this point.
        self.check_qty(product_1_id, Qty(0, 0, -7, -7, 0, -7, 0))
        self.check_qty(product_2_id, Qty(0, 0, -5, -5, 0, -5, 0))

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
