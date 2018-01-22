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

from unittest2 import skipIf
import netsvc
from openerp.osv import fields
from openerp.tests import common
from openerp.addons.pc_sale_order_automation.sale_order_ext import \
    SaleOrderAutomationResult, JOB_DELAYED_MESSAGE
from openerp.addons.pc_connect_master.tests.common import \
    CommonTestFunctionality
from common import CommonTestFunctionalitySOA


UNDER_DEVELOPMENT = False
UNDER_DEVELOPMENT_TEXT = 'Test was skipped because of being under development'


class TestSaleOrderInvoiceOpen(common.TransactionCase,
                               CommonTestFunctionality,
                               CommonTestFunctionalitySOA):
    """ This is to test the critical saleorder_invoice_open() of the SOA,
        in as many variants as possible.
    """

    def setUp(self):
        super(TestSaleOrderInvoiceOpen, self).setUp()
        self.context = {}

        # Gets the configuration data, that is unique.
        self.conf_obj = self.browse_ref('pc_config.default_configuration_data')

        # Sets the shop to use, which is unique.
        self.shop_id = self.ref('pc_connect_master.shop1')

        # We don't test the packaging here.
        self.set_config(self, 'packaging_enabled', False)

        # We don' wait here for aging.
        self.set_config(self, 'sale_order_min_age_in_draft_value', 0)

        # The warehouse is always opened for testing.
        self.set_config(self, 'support_start_time', 0)
        self.set_config(self, 'support_soft_end_time', 24)
        self.set_config(self, 'support_end_time', 24)

        # Creates the products we are going to use.
        self.prod_id_1 = self.create_product(self, {'name': 'P1'})
        self.prod_id_2 = self.create_product(self, {'name': 'P2'})
        self.prod_id_3 = self.create_product(self, {'name': 'P3'})
        self.service_id_1 = self.create_product(self, {'name': 'S1',
                                                       'type': 'service'})

        # Creates the payment methods, one epaid and other non-epaid.
        self.payment_method_epaid_id = \
            self.ref('pc_connect_master.payment_method_epaid')
        self.payment_method_not_epaid_id = \
            self.ref('pc_connect_master.payment_method_not_epaid')

    def tearDown(self):
        super(TestSaleOrderInvoiceOpen, self).tearDown()

    def __create_base_sale_order(self, invoice_policy, is_epaid):
        """ Creates a sale.order with 3 items of each of the 3 products,
            since each test is going to make use of this initial order.
        """
        cr, uid, ctx = self.cr, self.uid, self.context

        payment_method_id = self.payment_method_epaid_id if is_epaid \
            else self.payment_method_not_epaid_id
        sale_order_id = self.create_sale_order(self, {
            'payment_method_id': payment_method_id,
            'invoice_policy': invoice_policy,  # Overridden by the config.
            'picking_policy': 'direct',
            'shop_id': self.shop_id,
        })
        self.create_sale_order_line(self, {
            'order_id': sale_order_id,
            'product_id': self.prod_id_1,
            'product_uom_qty': 3,
            'name': 'Product P1',
        })
        self.create_sale_order_line(self, {
            'order_id': sale_order_id,
            'product_id': self.prod_id_2,
            'product_uom_qty': 3,
            'name': 'Product P2',
        })
        self.create_sale_order_line(self, {
            'order_id': sale_order_id,
            'product_id': self.prod_id_3,
            'product_uom_qty': 3,
            'name': 'Product P3',
        })
        self.create_sale_order_line(self, {
            'order_id': sale_order_id,
            'product_id': self.service_id_1,
            'product_uom_qty': 1,
            'name': 'Service S1',
        })
        return sale_order_id

    @skipIf(UNDER_DEVELOPMENT, UNDER_DEVELOPMENT_TEXT)
    def test_scenario_1(self):
        """ Order not epaid, inv. policy == 'delivery', no backorders, no discounts.
        """
        cr, uid, ctx = self.cr, self.uid, self.context
        invoice_policy = 'delivery'
        is_epaid = False

        invoice_obj = self.registry('account.invoice')

        self.set_config(self, 'invoice_policy', invoice_policy)
        self.set_config(self, 'default_picking_policy', 'keep')

        # Sale.order with 3 P1, 3 P2, 3 P3.
        self.obtain_qty(self, self.prod_id_1, 3, self.shop_id)
        self.obtain_qty(self, self.prod_id_2, 3, self.shop_id)
        self.obtain_qty(self, self.prod_id_3, 3, self.shop_id)
        order_id = self.__create_base_sale_order(
            invoice_policy=invoice_policy, is_epaid=is_epaid)

        # Initially: draft state.
        self.assertEqual(self.get_states(self, order_id, 'sale.order'),
                         ('draft', {'draft'}))

        # Validates the sale order. A shipping is created in state draft,
        # no invoices for the moment.
        self._automate_order(self, order_id,
                             'saleorder_check_inventory_for_quotation',
                             'saleorder_sent',
                             'direct')
        self.assertEqual(self.get_states(self, order_id, 'sale.order'),
                         ('manual', {'wait_invoice', 'ship'}))
        invoice_ids = self.check_num_and_get_invoices(self, order_id, 0)
        picking_ids = self.check_num_and_get_pickings(self, order_id, 1)
        self.assertEqual(self.get_states(self, picking_ids[0], 'stock.picking'),
                         ('confirmed', {'confirmed'}))

        # Assigns the items that we have. We have all of them, so there
        # is just one picking in state Ready to Deliver (state assigned).
        # No invoice for the moment.
        self._automate_order(self, order_id,
                             'deliveryorder_assignation_direct',
                             'print_deliveryorder_in_local',
                             'direct')
        self.assertEqual(self.get_states(self, order_id, 'sale.order'),
                         ('manual', {'wait_invoice', 'ship'}))
        invoice_ids = self.check_num_and_get_invoices(self, order_id, 0)
        picking_ids = self.check_num_and_get_pickings(self, order_id, 1)
        self.assertEqual(self.get_states(self, picking_ids[0], 'stock.picking'),
                         ('assigned', {'assigned'}))

        # We open the invoice, that will be opened and related to the picking.
        self._automate_order(self, order_id,
                             'invoice_open',
                             'invoice_open',
                             'direct')
        self.assertEqual(self.get_states(self, order_id, 'sale.order'),
                         ('progress', {'invoice', 'ship'}))
        invoice_ids = self.check_num_and_get_invoices(self, order_id, 1)
        self._check_carrier_from_order_in_invoice(order_id, invoice_ids)
        self._check_shop_from_order_in_invoice(order_id, invoice_ids)
        self.check_invoice_has_service_line(self, invoice_ids[0], True)
        self.assertEqual(self.get_states(self, invoice_ids[0], 'account.invoice'),
                         ('open', {'open'}))
        picking_ids = self.check_num_and_get_pickings(self, order_id, 1)
        self.assertEqual(self.get_states(self, picking_ids[0], 'stock.picking'),
                         ('assigned', {'assigned'}))
        related_invoice_ids = invoice_obj.search(cr, uid, [
            ('picking_id', '=', picking_ids[0]),
        ], context=ctx)
        self.assertEqual(invoice_ids, related_invoice_ids)

        # Prints the invoice and finishes the automation (nothing should change
        # regarding the states)
        self._automate_order(self, order_id,
                             'print_invoice_in_local',
                             'print_invoice_in_local',
                             'direct')
        self.assertEqual(self.get_states(self, order_id, 'sale.order'),
                         ('progress', {'invoice', 'ship'}))
        invoice_ids = self.check_num_and_get_invoices(self, order_id, 1)
        self._check_carrier_from_order_in_invoice(order_id, invoice_ids)
        self._check_shop_from_order_in_invoice(order_id, invoice_ids)
        self.assertEqual(self.get_states(self, invoice_ids[0], 'account.invoice'),
                         ('open', {'open'}))
        picking_ids = self.check_num_and_get_pickings(self, order_id, 1)
        self.assertEqual(self.get_states(self, picking_ids[0], 'stock.picking'),
                         ('assigned', {'assigned'}))
        related_invoice_ids = invoice_obj.search(cr, uid, [
            ('picking_id', '=', picking_ids[0]),
        ], context=ctx)
        self.assertEqual(invoice_ids, related_invoice_ids)

        # Fully delivers the picking.
        picking_ids = self.check_num_and_get_pickings(self, order_id, 1)
        self.deliver_assigned_picking(self, picking_ids)
        picking_ids = self.check_num_and_get_pickings(self, order_id, 1)
        self.assertEqual(self.get_states(self, order_id, 'sale.order'),
                         ('progress', {'invoice'}))
        self.assertEqual(self.get_states(self, picking_ids[0], 'stock.picking'),
                         ('done', {'done'}))

        # Fully pays the invoice.
        self.pay_invoice(self, invoice_ids[0])
        self.assertEqual(self.get_states(self, order_id, 'sale.order'),
                         ('done', {'done'}))
        self.assertEqual(self.get_states(self, invoice_ids[0], 'account.invoice'),
                         ('paid', {'paid'}))

    @skipIf(UNDER_DEVELOPMENT, UNDER_DEVELOPMENT_TEXT)
    def test_scenario_2(self):
        """ Order not epaid, inv. policy == 'delivery', 1 backorder, no discounts.
        """
        cr, uid, ctx = self.cr, self.uid, self.context
        invoice_policy = 'delivery'
        is_epaid = False

        invoice_obj = self.registry('account.invoice')

        self.set_config(self, 'invoice_policy', invoice_policy)
        self.set_config(self, 'default_picking_policy', 'keep')

        # Sale.order with 3 P1, 2 P2, 1 P3, so at least a backorder
        # will be needed.
        self.obtain_qty(self, self.prod_id_1, 3, self.shop_id)
        self.obtain_qty(self, self.prod_id_2, 2, self.shop_id)
        self.obtain_qty(self, self.prod_id_3, 1, self.shop_id)
        order_id = self.__create_base_sale_order(
            invoice_policy=invoice_policy, is_epaid=is_epaid)

        # Initially: draft state.
        self.assertEqual(self.get_states(self, order_id, 'sale.order'),
                         ('draft', {'draft'}))

        # Validates the sale order. A shipping is created in state draft,
        # no invoices for the moment.
        self._automate_order(self, order_id,
                             'saleorder_check_inventory_for_quotation',
                             'saleorder_sent',
                             'direct')
        self.assertEqual(self.get_states(self, order_id, 'sale.order'),
                         ('manual', {'wait_invoice', 'ship'}))
        invoice_ids = self.check_num_and_get_invoices(self, order_id, 0)
        picking_ids = self.check_num_and_get_pickings(self, order_id, 1)
        self.assertEqual(self.get_states(self, picking_ids[0], 'stock.picking'),
                         ('confirmed', {'confirmed'}))

        # Assigns the items that we have. We don't have all of them, so we
        # create a backorder.
        # No invoice for the moment.
        self._automate_order(self, order_id,
                             'deliveryorder_assignation_direct',
                             'print_deliveryorder_in_local',
                             'direct')
        self.assertEqual(self.get_states(self, order_id, 'sale.order'),
                         ('manual', {'wait_invoice', 'ship'}))
        invoice_ids = self.check_num_and_get_invoices(self, order_id, 0)
        picking_ids = self.check_num_and_get_pickings(self, order_id, 2)
        pending_id, non_pending_ids = self.find_backorder(self, picking_ids)
        self.assertTrue(pending_id)
        self.assertEqual(self.get_states(self, pending_id, 'stock.picking'),
                         ('confirmed', {'confirmed'}))
        self.assertEqual(len(non_pending_ids), 1)
        self.assertEqual(self.get_states(self, non_pending_ids[0], 'stock.picking'),
                         ('assigned', {'assigned'}))

        # We open the invoice, that will be opened and related to the picking.
        self._automate_order(self, order_id,
                             'invoice_open',
                             'invoice_open',
                             'direct')
        self.assertEqual(self.get_states(self, order_id, 'sale.order'),
                         ('progress', {'invoice', 'ship'}))
        invoice_ids = self.check_num_and_get_invoices(self, order_id, 1)
        self._check_carrier_from_order_in_invoice(order_id, invoice_ids)
        self._check_shop_from_order_in_invoice(order_id, invoice_ids)
        self.check_invoice_has_service_line(self, invoice_ids[0], True)
        self.assertEqual(self.get_states(self, invoice_ids[0], 'account.invoice'),
                         ('open', {'open'}))
        picking_ids = self.check_num_and_get_pickings(self, order_id, 2)
        self.assertEqual(self.get_states(self, picking_ids[0], 'stock.picking'),
                         ('assigned', {'assigned'}))
        related_invoice_ids = invoice_obj.search(cr, uid, [
            ('picking_id', '=', non_pending_ids[0]),
        ], context=ctx)
        self.assertEqual(invoice_ids, related_invoice_ids)

        # Prints the invoice and finishes the automation (nothing should change
        # regarding the states)
        self._automate_order(self, order_id,
                             'print_invoice_in_local',
                             'print_invoice_in_local',
                             'direct')
        self.assertEqual(self.get_states(self, order_id, 'sale.order'),
                         ('progress', {'invoice', 'ship'}))
        invoice_ids = self.check_num_and_get_invoices(self, order_id, 1)
        self._check_carrier_from_order_in_invoice(order_id, invoice_ids)
        self._check_shop_from_order_in_invoice(order_id, invoice_ids)
        self.assertEqual(self.get_states(self, invoice_ids[0], 'account.invoice'),
                         ('open', {'open'}))
        invoice_ids = self.check_num_and_get_invoices(self, order_id, 1)
        self._check_carrier_from_order_in_invoice(order_id, invoice_ids)
        self._check_shop_from_order_in_invoice(order_id, invoice_ids)
        picking_ids = self.check_num_and_get_pickings(self, order_id, 2)
        pending_id, non_pending_ids = self.find_backorder(self, picking_ids)
        self.assertTrue(pending_id)
        self.assertEqual(self.get_states(self, pending_id, 'stock.picking'),
                         ('confirmed', {'confirmed'}))
        self.assertEqual(len(non_pending_ids), 1)
        self.assertEqual(self.get_states(self, non_pending_ids[0], 'stock.picking'),
                         ('assigned', {'assigned'}))
        related_invoice_ids = invoice_obj.search(cr, uid, [
            ('picking_id', '=', non_pending_ids[0]),
        ], context=ctx)
        self.assertEqual(invoice_ids, related_invoice_ids)

        # Fully delivers the picking with the quantities that we have.
        picking_ids = self.check_num_and_get_pickings(self, order_id, 2)
        self.deliver_assigned_picking(self, [non_pending_ids[0]])
        picking_ids = self.check_num_and_get_pickings(self, order_id, 2)
        pending_id, non_pending_ids = self.find_backorder(self, picking_ids)
        self.assertEqual(self.get_states(self, order_id, 'sale.order'),
                         ('progress', {'ship', 'invoice'}))
        self.assertEqual(self.get_states(self, non_pending_ids[0], 'stock.picking'),
                         ('done', {'done'}))
        self.assertEqual(self.get_states(self, pending_id, 'stock.picking'),
                         ('confirmed', {'confirmed'}))

        # Fully pays the invoice.
        self.pay_invoice(self, invoice_ids[0])
        self.assertEqual(self.get_states(self, order_id, 'sale.order'),
                         ('progress', {'ship', 'wait_all_invoices_end'}))
        self.assertEqual(self.get_states(self, invoice_ids[0], 'account.invoice'),
                         ('paid', {'paid'}))

        # Receives the quantities that were missing: 1 P2, 2 P3.
        self.obtain_qty(self, self.prod_id_2, 1, self.shop_id)
        self.obtain_qty(self, self.prod_id_3, 2, self.shop_id)

        # Automates the pending picking.
        self._automate_order(self, order_id,
                             'deliveryorder_assignation_direct',
                             'print_deliveryorder_in_local',
                             'direct', backorder_id=pending_id)
        picking_ids = self.check_num_and_get_pickings(self, order_id, 2)
        pending_id, non_pending_ids = self.find_backorder(self, picking_ids)
        self.assertTrue(pending_id)
        self.assertEqual(len(non_pending_ids), 1)
        self.assertEqual(self.get_states(self, non_pending_ids[0], 'stock.picking'),
                         ('done', {'done'}))
        self.assertEqual(self.get_states(self, pending_id, 'stock.picking'),
                         ('assigned', {'assigned'}))

        # We open the invoice, that will be opened and related to the picking.
        self._automate_order(self, order_id,
                             'invoice_open',
                             'invoice_open',
                             'direct', backorder_id=pending_id)
        # (the state of the workflow should be 'invoice, 'ship', but it will
        #  be just 'ship' since it works with the inv_policy=='order'.
        self.assertEqual(self.get_states(self, order_id, 'sale.order'),
                         ('progress', {'ship', 'wait_all_invoices_end'}))

        invoice_ids = self.check_num_and_get_invoices(self, order_id, 2)
        self._check_carrier_from_order_in_invoice(order_id, invoice_ids)
        self._check_shop_from_order_in_invoice(order_id, invoice_ids)
        new_invoice_ids = invoice_obj.search(cr, uid, [
            ('state', '=', 'open'),
            ('id', 'in', invoice_ids),
        ], context=ctx)
        self.check_invoice_has_service_line(self, new_invoice_ids[0], False)
        self.assertEqual(len(new_invoice_ids), 1)
        related_invoice_ids = invoice_obj.search(cr, uid, [
            ('picking_id', '=', pending_id),
        ], context=ctx)
        self.assertEqual(new_invoice_ids, related_invoice_ids)

        # Fully delivers the picking with the pending quantities that we have.
        picking_ids = self.check_num_and_get_pickings(self, order_id, 2)
        self.deliver_assigned_picking(self, [pending_id])
        picking_ids = self.check_num_and_get_pickings(self, order_id, 2)
        for picking_id in picking_ids:
            self.assertEqual(self.get_states(self, picking_id, 'stock.picking'),
                             ('done', {'done'}))
        self.assertEqual(self.get_states(self, order_id, 'sale.order'),
                         ('progress', {'wait_all_invoices_end'}))

        # Fully pays the invoice.
        self.pay_invoice(self, new_invoice_ids[0])
        self.assertEqual(self.get_states(self, order_id, 'sale.order'),
                         ('done', {'done'}))
        self.assertEqual(self.get_states(self, new_invoice_ids[0], 'account.invoice'),
                         ('paid', {'paid'}))

    @skipIf(UNDER_DEVELOPMENT, UNDER_DEVELOPMENT_TEXT)
    def test_scenario_3(self):
        """ Order not epaid, inv. policy == 'delivery', 2 backorders, no discounts.
        """
        cr, uid, ctx = self.cr, self.uid, self.context
        invoice_policy = 'delivery'
        is_epaid = False

        invoice_obj = self.registry('account.invoice')

        self.set_config(self, 'invoice_policy', invoice_policy)
        self.set_config(self, 'default_picking_policy', 'keep')

        #######################################################################
        # Sale.order has with 3 P1, 3 P2, 3 P3.
        #######################################################################
        self.obtain_qty(self, self.prod_id_1, 1, self.shop_id)
        self.obtain_qty(self, self.prod_id_2, 1, self.shop_id)
        self.obtain_qty(self, self.prod_id_3, 1, self.shop_id)
        order_id = self.__create_base_sale_order(
            invoice_policy=invoice_policy, is_epaid=is_epaid)

        # Automates the sale.order until the end.
        # It will have created an invoice and a backorder.
        self._automate_order(self, order_id,
                             'saleorder_check_inventory_for_quotation',
                             'print_invoice_in_local',
                             'direct')

        picking_ids = self.check_num_and_get_pickings(self, order_id, 2)
        invoice_ids = self.check_num_and_get_invoices(self, order_id, 1)
        self._check_carrier_from_order_in_invoice(order_id, invoice_ids)
        self._check_shop_from_order_in_invoice(order_id, invoice_ids)
        first_invoice_id = invoice_ids[0]
        self.check_invoice_has_service_line(self, first_invoice_id, True)
        pending_id, non_pending_ids = self.find_backorder(self, picking_ids)
        self.assertEqual(len(non_pending_ids), 1)
        first_invoice = invoice_obj.browse(cr, uid, first_invoice_id, context=ctx)
        self.assertEqual(first_invoice.picking_id.id, non_pending_ids[0])

        # Pays and delivers the quantities that we have.

        # Fully delivers the picking with the quantities that we have.
        self.deliver_assigned_picking(self, [non_pending_ids[0]])
        self.assertEqual(self.get_states(self, non_pending_ids[0], 'stock.picking'),
                         ('done', {'done'}))
        self.assertEqual(self.get_states(self, order_id, 'sale.order'),
                         ('progress', {'ship', 'invoice'}))

        # Fully pays the invoice.
        self.pay_invoice(self, first_invoice_id)
        self.assertEqual(self.get_states(self, first_invoice_id, 'account.invoice'),
                         ('paid', {'paid'}))
        self.assertEqual(self.get_states(self, order_id, 'sale.order'),
                         ('progress', {'ship', 'wait_all_invoices_end'}))

        #######################################################################
        # Receives 1 P1, 1 P2, 1 P3.
        #######################################################################
        self.obtain_qty(self, self.prod_id_1, 1, self.shop_id)
        self.obtain_qty(self, self.prod_id_2, 1, self.shop_id)
        self.obtain_qty(self, self.prod_id_3, 1, self.shop_id)

        # Automates the new backorder.
        self._automate_order(self, order_id,
                             'deliveryorder_assignation_direct',
                             'print_invoice_in_local',
                             'direct', backorder_id=pending_id)

        picking_ids = self.check_num_and_get_pickings(self, order_id, 3)
        invoice_ids = self.check_num_and_get_invoices(self, order_id, 2)
        self._check_carrier_from_order_in_invoice(order_id, invoice_ids)
        self._check_shop_from_order_in_invoice(order_id, invoice_ids)
        pending_id, non_pending_ids = self.find_backorder(self, picking_ids)
        self.assertEqual(len(non_pending_ids), 2)
        second_invoice_id = \
            invoice_ids[0] if invoice_ids[0] != first_invoice_id \
                else invoice_ids[1]
        self.check_invoice_has_service_line(self, second_invoice_id, False)
        second_invoice = invoice_obj.browse(cr, uid, second_invoice_id, context=ctx)
        self.assertEqual(second_invoice.picking_id.id, max(non_pending_ids))

        # Pays and delivers the quantities that we have.

        # Fully delivers the picking with the quantities that we have.
        self.deliver_assigned_picking(self, [max(non_pending_ids)])
        self.assertEqual(self.get_states(self, max(non_pending_ids), 'stock.picking'),
                         ('done', {'done'}))
        self.assertEqual(self.get_states(self, order_id, 'sale.order'),
                         ('progress', {'ship', 'wait_all_invoices_end'}))

        # Fully pays the invoice.
        self.pay_invoice(self, second_invoice_id)
        self.assertEqual(self.get_states(self, second_invoice_id, 'account.invoice'),
                         ('paid', {'paid'}))
        self.assertEqual(self.get_states(self, order_id, 'sale.order'),
                         ('progress', {'ship', 'wait_all_invoices_end'}))

        #######################################################################
        # Receives 1 P1, 1 P2, 1 P3.
        #######################################################################
        self.obtain_qty(self, self.prod_id_1, 1, self.shop_id)
        self.obtain_qty(self, self.prod_id_2, 1, self.shop_id)
        self.obtain_qty(self, self.prod_id_3, 1, self.shop_id)

        # Automates the new backorder.
        self._automate_order(self, order_id,
                             'deliveryorder_assignation_direct',
                             'print_invoice_in_local',
                             'direct', backorder_id=pending_id)

        picking_ids = self.check_num_and_get_pickings(self, order_id, 3)
        invoice_ids = self.check_num_and_get_invoices(self, order_id, 3)
        self._check_carrier_from_order_in_invoice(order_id, invoice_ids)
        self._check_shop_from_order_in_invoice(order_id, invoice_ids)
        last_picking_id, non_pending_ids = self.find_backorder(self, picking_ids)
        self.assertEqual(len(non_pending_ids), 2)
        third_invoice_id = list(set(invoice_ids) - set([first_invoice_id, second_invoice_id]))[0]
        self.check_invoice_has_service_line(self, third_invoice_id, False)
        third_invoice = invoice_obj.browse(cr, uid, third_invoice_id, context=ctx)
        self.assertEqual(third_invoice.picking_id.id, last_picking_id)

        # Pays and delivers the quantities that we have.

        # Fully delivers the picking with the quantities that we have.
        self.deliver_assigned_picking(self, [last_picking_id])
        self.assertEqual(self.get_states(self, last_picking_id, 'stock.picking'),
                         ('done', {'done'}))
        self.assertEqual(self.get_states(self, order_id, 'sale.order'),
                         ('progress', {'wait_all_invoices_end'}))

        # Fully pays the invoice.
        self.pay_invoice(self, third_invoice_id)
        self.assertEqual(self.get_states(self, third_invoice_id, 'account.invoice'),
                         ('paid', {'paid'}))
        self.assertEqual(self.get_states(self, order_id, 'sale.order'),
                         ('done', {'done'}))

    @skipIf(UNDER_DEVELOPMENT, UNDER_DEVELOPMENT_TEXT)
    def test_scenario_4(self):
        """ Order not epaid, inv. policy == 'order', no backorders, no discounts.
        """
        cr, uid, ctx = self.cr, self.uid, self.context
        invoice_policy = 'order'
        is_epaid = False

        invoice_obj = self.registry('account.invoice')

        self.set_config(self, 'invoice_policy', invoice_policy)
        self.set_config(self, 'default_picking_policy', 'keep')

        # Sale.order with 3 P1, 3 P2, 3 P3.
        self.obtain_qty(self, self.prod_id_1, 3, self.shop_id)
        self.obtain_qty(self, self.prod_id_2, 3, self.shop_id)
        self.obtain_qty(self, self.prod_id_3, 3, self.shop_id)
        order_id = self.__create_base_sale_order(
            invoice_policy=invoice_policy, is_epaid=is_epaid)

        # Initially: draft state.
        self.assertEqual(self.get_states(self, order_id, 'sale.order'),
                         ('draft', {'draft'}))

        # Validates the sale order. A shipping is created in state draft,
        # no invoices for the moment.
        self._automate_order(self, order_id,
                             'saleorder_check_inventory_for_quotation',
                             'saleorder_sent',
                             'direct')
        self.assertEqual(self.get_states(self, order_id, 'sale.order'),
                         ('manual', {'wait_invoice', 'ship'}))
        invoice_ids = self.check_num_and_get_invoices(self, order_id, 0)
        picking_ids = self.check_num_and_get_pickings(self, order_id, 1)
        self.assertEqual(self.get_states(self, picking_ids[0], 'stock.picking'),
                         ('confirmed', {'confirmed'}))

        # Assigns the items that we have. We have all of them, so there
        # is just one picking in state Ready to Deliver (state assigned).
        # No invoice for the moment.
        self._automate_order(self, order_id,
                             'deliveryorder_assignation_direct',
                             'print_deliveryorder_in_local',
                             'direct')
        self.assertEqual(self.get_states(self, order_id, 'sale.order'),
                         ('manual', {'wait_invoice', 'ship'}))
        invoice_ids = self.check_num_and_get_invoices(self, order_id, 0)
        picking_ids = self.check_num_and_get_pickings(self, order_id, 1)
        self.assertEqual(self.get_states(self, picking_ids[0], 'stock.picking'),
                         ('assigned', {'assigned'}))

        # We open the invoice, that will be opened and related to the picking.
        self._automate_order(self, order_id,
                             'invoice_open',
                             'invoice_open',
                             'direct')
        self.assertEqual(self.get_states(self, order_id, 'sale.order'),
                         ('progress', {'invoice', 'ship'}))
        invoice_ids = self.check_num_and_get_invoices(self, order_id, 1)
        self._check_carrier_from_order_in_invoice(order_id, invoice_ids)
        self._check_shop_from_order_in_invoice(order_id, invoice_ids)
        self.check_invoice_has_service_line(self, invoice_ids[0], True)
        self.assertEqual(self.get_states(self, invoice_ids[0], 'account.invoice'),
                         ('open', {'open'}))
        picking_ids = self.check_num_and_get_pickings(self, order_id, 1)
        self.assertEqual(self.get_states(self, picking_ids[0], 'stock.picking'),
                         ('assigned', {'assigned'}))

        # Prints the invoice and finishes the automation (nothing should change
        # regarding the states)
        self._automate_order(self, order_id,
                             'print_invoice_in_local',
                             'print_invoice_in_local',
                             'direct')
        self.assertEqual(self.get_states(self, order_id, 'sale.order'),
                         ('progress', {'invoice', 'ship'}))
        invoice_ids = self.check_num_and_get_invoices(self, order_id, 1)
        self._check_carrier_from_order_in_invoice(order_id, invoice_ids)
        self._check_shop_from_order_in_invoice(order_id, invoice_ids)
        self.assertEqual(self.get_states(self, invoice_ids[0], 'account.invoice'),
                         ('open', {'open'}))
        picking_ids = self.check_num_and_get_pickings(self, order_id, 1)
        self.assertEqual(self.get_states(self, picking_ids[0], 'stock.picking'),
                         ('assigned', {'assigned'}))

        # Fully delivers the picking.
        picking_ids = self.check_num_and_get_pickings(self, order_id, 1)
        self.deliver_assigned_picking(self, picking_ids)
        picking_ids = self.check_num_and_get_pickings(self, order_id, 1)
        self.assertEqual(self.get_states(self, order_id, 'sale.order'),
                         ('progress', {'invoice'}))
        self.assertEqual(self.get_states(self, picking_ids[0], 'stock.picking'),
                         ('done', {'done'}))

        # Fully pays the invoice.
        self.pay_invoice(self, invoice_ids[0])
        self.assertEqual(self.get_states(self, order_id, 'sale.order'),
                         ('done', {'done'}))
        self.assertEqual(self.get_states(self, invoice_ids[0], 'account.invoice'),
                         ('paid', {'paid'}))

    @skipIf(UNDER_DEVELOPMENT, UNDER_DEVELOPMENT_TEXT)
    def test_scenario_5(self):
        """ Order not epaid, inv. policy == 'order', 2 backorders, no discounts.
        """
        cr, uid, ctx = self.cr, self.uid, self.context
        invoice_policy = 'order'
        is_epaid = False

        invoice_obj = self.registry('account.invoice')

        self.set_config(self, 'invoice_policy', invoice_policy)
        self.set_config(self, 'default_picking_policy', 'keep')

        #######################################################################
        # Sale.order has with 3 P1, 3 P2, 3 P3.
        #######################################################################
        self.obtain_qty(self, self.prod_id_1, 1, self.shop_id)
        self.obtain_qty(self, self.prod_id_2, 1, self.shop_id)
        self.obtain_qty(self, self.prod_id_3, 1, self.shop_id)
        order_id = self.__create_base_sale_order(
            invoice_policy=invoice_policy, is_epaid=is_epaid)

        # Automates the sale.order until the end.
        # It will have created an invoice and a backorder.
        self._automate_order(self, order_id,
                             'saleorder_check_inventory_for_quotation',
                             'print_invoice_in_local',
                             'direct')

        picking_ids = self.check_num_and_get_pickings(self, order_id, 2)
        invoice_ids = self.check_num_and_get_invoices(self, order_id, 1)
        self._check_carrier_from_order_in_invoice(order_id, invoice_ids)
        self._check_shop_from_order_in_invoice(order_id, invoice_ids)
        pending_id, non_pending_ids = self.find_backorder(self, picking_ids)
        self.assertEqual(len(non_pending_ids), 1)

        # Pays and delivers the quantities that we have.

        # Fully delivers the picking with the quantities that we have.
        self.deliver_assigned_picking(self, [non_pending_ids[0]])
        self.assertEqual(self.get_states(self, non_pending_ids[0], 'stock.picking'),
                         ('done', {'done'}))
        self.assertEqual(self.get_states(self, order_id, 'sale.order'),
                         ('progress', {'ship', 'invoice'}))

        # Fully pays the invoice.
        self.pay_invoice(self, invoice_ids[0])
        self.assertEqual(self.get_states(self, invoice_ids[0], 'account.invoice'),
                         ('paid', {'paid'}))
        self.assertEqual(self.get_states(self, order_id, 'sale.order'),
                         ('progress', {'ship'}))

        #######################################################################
        # Receives 1 P1, 1 P2, 1 P3.
        #######################################################################
        self.obtain_qty(self, self.prod_id_1, 1, self.shop_id)
        self.obtain_qty(self, self.prod_id_2, 1, self.shop_id)
        self.obtain_qty(self, self.prod_id_3, 1, self.shop_id)

        # Automates the new backorder.
        self._automate_order(self, order_id,
                             'deliveryorder_assignation_direct',
                             'print_invoice_in_local',
                             'direct', backorder_id=pending_id)

        picking_ids = self.check_num_and_get_pickings(self, order_id, 3)
        invoice_ids = self.check_num_and_get_invoices(self, order_id, 1)
        self._check_carrier_from_order_in_invoice(order_id, invoice_ids)
        self._check_shop_from_order_in_invoice(order_id, invoice_ids)
        self.check_invoice_has_service_line(self, invoice_ids[0], True)
        pending_id, non_pending_ids = self.find_backorder(self, picking_ids)
        self.assertEqual(len(non_pending_ids), 2)

        # Pays and delivers the quantities that we have.

        # Fully delivers the picking with the quantities that we have.
        self.deliver_assigned_picking(self, [max(non_pending_ids)])
        self.assertEqual(self.get_states(self, max(non_pending_ids), 'stock.picking'),
                         ('done', {'done'}))
        self.assertEqual(self.get_states(self, order_id, 'sale.order'),
                         ('progress', {'ship'}))

        #######################################################################
        # Receives 1 P1, 1 P2, 1 P3.
        #######################################################################
        self.obtain_qty(self, self.prod_id_1, 1, self.shop_id)
        self.obtain_qty(self, self.prod_id_2, 1, self.shop_id)
        self.obtain_qty(self, self.prod_id_3, 1, self.shop_id)

        # Automates the new backorder.
        self._automate_order(self, order_id,
                             'deliveryorder_assignation_direct',
                             'print_invoice_in_local',
                             'direct', backorder_id=pending_id)

        picking_ids = self.check_num_and_get_pickings(self, order_id, 3)
        invoice_ids = self.check_num_and_get_invoices(self, order_id, 1)
        self._check_carrier_from_order_in_invoice(order_id, invoice_ids)
        self._check_shop_from_order_in_invoice(order_id, invoice_ids)
        last_picking_id, non_pending_ids = self.find_backorder(self, picking_ids)
        self.assertEqual(len(non_pending_ids), 2)

        # Pays and delivers the quantities that we have.

        # Fully delivers the picking with the quantities that we have.
        self.deliver_assigned_picking(self, [last_picking_id])
        self.assertEqual(self.get_states(self, last_picking_id, 'stock.picking'),
                         ('done', {'done'}))
        self.assertEqual(self.get_states(self, order_id, 'sale.order'),
                         ('done', {'done'}))

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
