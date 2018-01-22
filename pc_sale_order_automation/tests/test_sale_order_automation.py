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


DEFAULT_LINE_DELAY = 9
DEFAULT_PRICE_UNIT = 7
DEFAULT_PRODUCT_UOM_QTY = 17

UNDER_DEVELOPMENT = False
UNDER_DEVELOPMENT_TEXT = 'Test was skipped because of being under development'


class TestSaleOrderAutomation(common.TransactionCase, CommonTestFunctionality):

    def setUp(self):
        super(TestSaleOrderAutomation, self).setUp()
        self.context = {}

        conf_obj = self.registry('configuration.data')
        conf = conf_obj.get(self.cr, self.uid, [], self.context)
        conf_obj.write(self.cr, self.uid, conf.id,
                       {'default_picking_policy': 'keep'},
                       context=self.context)

    def tearDown(self):
        super(TestSaleOrderAutomation, self).tearDown()

    def __create_invoice(self, defaults=None):
        if defaults is None:
            defaults = {}
        cr, uid, ctx = self.cr, self.uid, self.context

        journal_obj = self.registry('account.journal')
        account_obj = self.registry('account.account')
        invoice_obj = self.registry('account.invoice')

        test_partner_person_id = \
            self.ref('pc_sale_order_automation.test_partner_person')
        test_journal_id = journal_obj.search(
            cr, uid, [('type', '=', 'sale')], context=ctx)[0]
        test_account_id = account_obj.search(
            cr, uid, [('type', '=', 'receivable')], context=ctx)[0]

        values = {
            'partner_id': test_partner_person_id,
            'account_id': test_account_id,
            'journal_id': test_journal_id,
        }
        if defaults:
            values.update(defaults)

        inv_id = invoice_obj.create(cr, uid, values, context=ctx)

        return inv_id

    def __create_invoice_line(self, invoice_id, defaults=None):
        if defaults is None:
            defaults = {}
        cr, uid, ctx = self.cr, self.uid, self.context

        account_obj = self.registry('account.account')
        invoice_obj = self.registry('account.invoice')
        invoice_line_obj = self.registry('account.invoice.line')

        test_product_id = self.ref('product.product_product_48')
        uom_unit_id = self.ref('product.product_uom_unit')

        values = {
            'name': "Test Product",
            'product_id': test_product_id,
            'quantity': DEFAULT_PRODUCT_UOM_QTY,
            'uos_id': uom_unit_id,
            'price_unit': DEFAULT_PRICE_UNIT,
            'invoice_id': invoice_id
        }
        values.update(defaults)

        inv_line_id = invoice_line_obj.create(cr, uid, values, context=ctx)

        invoice_obj.button_reset_taxes(cr, uid, [invoice_id], context=ctx)

        return inv_line_id

    def __create_purchase_order(self, defaults=None):
        """ Creates a purchase.order with the default values, common for
            all the tests.
        :param defaults: The default values to pass to the create().
        :return: The ID of the purchase.order created.
        """
        if defaults is None:
            defaults = {}
        cr, uid, ctx = self.cr, self.uid, self.context

        purchase_obj = self.registry('purchase.order')

        # Sets the value for the sale order to be created.
        test_partner_person_id = \
            self.ref('pc_sale_order_automation.test_partner_person')
        test_payment_method_id = \
            self.ref('pc_sale_order_automation.test_payment_invoice')
        test_pricelist_id = self.ref('product.list0')
        test_currency_id = self.ref('base.CHF')
        test_company_id = self.ref('base.main_company')
        test_location_id = self.ref('stock.stock_location_stock')
        purchase_vals = {
            'partner_id': test_partner_person_id,
            'partner_invoice_id': test_partner_person_id,
            'partner_shipping_id': test_partner_person_id,
            'name': 'Test Purchase',
            'currency_id': test_currency_id,
            'company_id': test_company_id,
            'location_id': test_location_id,
            'invoice_method': 'picking',
            'date_order': fields.date.today(),
            'payment_method_id': test_payment_method_id,
            'automate_sale_order_process': False,
            'pricelist_id': test_pricelist_id,
        }
        purchase_vals.update(defaults)

        # Creates the sale order.
        purchase_id = purchase_obj.create(cr, uid, purchase_vals, context=ctx)
        return purchase_id

    def __create_purchase_order_line(self, purchase_id, defaults=None):
        """ Creates a purchase.order.line with the values provided.
        :param order_id: The ID of the order for the line.
        :param vals: Dictionary to pass to the create().
        :return: The ID of the purchase.order.line created.
        """
        if defaults is None:
            defaults = {}
        cr, uid, ctx = self.cr, self.uid, self.context

        purchase_line_obj = self.registry('purchase.order.line')

        product_id = self.ref('product.product_product_48')
        uom_unit_id = self.ref('product.product_uom_unit')
        vals = {
            'order_id': purchase_id,
            'state': 'draft',
            'date_planned': fields.date.today(),
            'product_id': product_id,
            'name': 'Test Product',
            'product_qty': DEFAULT_PRODUCT_UOM_QTY,
            'product_uom': uom_unit_id,
            'price_unit': DEFAULT_PRICE_UNIT,
            'delay': DEFAULT_LINE_DELAY,
        }
        vals.update(defaults)

        order_line_id = purchase_line_obj.create(
            cr, uid, vals, context=ctx)

        return order_line_id

    def __create_sale_order(self, defaults=None):
        """ Creates a sale.order with the default values, common for all the
            tests.
        :param defaults: The default values to pass to the create().
        :return: The ID of the new sale.order created.
        """
        if defaults is None:
            defaults = {}
        cr, uid, ctx = self.cr, self.uid, self.context

        order_obj = self.registry('sale.order')
        partner_obj = self.registry('res.partner')

        # Sets a fiscal position for the partner of the sale order.
        test_partner_person_id = \
            self.ref('pc_sale_order_automation.test_partner_person')
        fiscal_position_id = \
            self.ref('pc_sale_order_automation.test_fiscal_position')
        partner_obj.write(
            cr, uid, test_partner_person_id,
            {'property_account_position': fiscal_position_id},
            context=ctx)

        # Sets the value for the sale order to be created.
        test_payment_method_id = \
            self.ref('pc_sale_order_automation.test_payment_invoice')
        test_carrier_id = self.ref('delivery.delivery_carrier')
        test_pricelist_id = self.ref('product.list0')
        order_vals = {
            'partner_id': test_partner_person_id,
            'partner_invoice_id': test_partner_person_id,
            'partner_shipping_id': test_partner_person_id,
            'date_order': fields.date.today(),
            'payment_method_id': test_payment_method_id,
            'automate_sale_order_process': False,
            'carrier_id': test_carrier_id,
            'pricelist_id': test_pricelist_id,
        }
        order_vals.update(defaults)

        # Creates the sale order.
        order_id = order_obj.create(cr, uid, order_vals, context=ctx)
        return order_id

    def __create_sale_order_line(self, order_id, defaults=None):
        """ Creates a sale.order.line with the values provided.
        :param order_id: The ID of the order for the line.
        :param vals: Dictionary to pass to the create().
        :return: The ID of the sale.order.line created.
        """
        if defaults is None:
            defaults = {}
        cr, uid, ctx = self.cr, self.uid, self.context

        order_line_obj = self.registry('sale.order.line')

        product_id = self.ref('product.product_product_48')
        uom_unit_id = self.ref('product.product_uom_unit')
        vals = {
            'order_id': order_id,
            'product_id': product_id,
            'name': 'Test Product',
            'product_uom_qty': DEFAULT_PRODUCT_UOM_QTY,
            'product_uom': uom_unit_id,
            'price_unit': DEFAULT_PRICE_UNIT,
            'delay': DEFAULT_LINE_DELAY,
        }
        vals.update(defaults)

        order_line_id = order_line_obj.create(
            cr, uid, vals, context=ctx)

        return order_line_id

    def __create_stock_type(self, vals):
        """ Creates a stock.type with the values provided.
        :param vals: Dictionary to pass to the create ().
        :return: The ID of the stock.type created.
        """
        cr, uid, ctx = self.cr, self.uid, self.context
        stock_type_obj = self.registry('stock.type')

        stock_type_id = stock_type_obj.create(
            cr, uid, vals, context=ctx)

        return stock_type_id

    def __aux_soa_inventory(
            self, do_availability_check, soa_info_expected_msg):
        """ Auxiliary method for soa_inventory_*() tests.
        """
        cr, uid, ctx = self.cr, self.uid, self.context

        order_obj = self.registry('sale.order')

        soa_info = SaleOrderAutomationResult()

        # Creates a sale order.
        if do_availability_check:
            sale_order_defaults = {'picking_policy': 'one'}
        else:
            sale_order_defaults = {'picking_policy': 'direct'}
        order_id = self.__create_sale_order(sale_order_defaults)

        # Creates a stock type and associates it to the sale order.
        stock_type_vals = {
            "name": "Stock Type",
            "availability_check": do_availability_check,
        }
        stock_type_id = self.__create_stock_type(stock_type_vals)
        order_obj.write(
            cr, uid, order_id, {'stock_type_id': stock_type_id}, ctx)

        # The call to the method to test.
        order_obj.check_if_check_inventory_for_quotation(
            cr, uid, order_id, soa_info, ctx)

        # Tests.
        self.assertEqual(
            soa_info.next_state, 'saleorder_draft')
        self.assertEqual(soa_info.message, soa_info_expected_msg)

    @skipIf(UNDER_DEVELOPMENT, UNDER_DEVELOPMENT_TEXT)
    def test_soa_inventory_do_not_check(self):
        """ Tests check_if_check_inventory_for_quotation() for the case in
            which we don't want to perform an inventory check.
        """
        soa_info_expected_msg = \
            "Skipped the inventory check because " \
            "the picking policy is 'direct'."
        self.__aux_soa_inventory(
            do_availability_check=False,
            soa_info_expected_msg=soa_info_expected_msg)

    @skipIf(UNDER_DEVELOPMENT, UNDER_DEVELOPMENT_TEXT)
    def test_soa_inventory_do_check(self):
        """ Tests check_if_check_inventory_for_quotation() for the case in
            which we do want to perform an inventory check.
        """
        soa_info_expected_msg = \
            'Checks if there are items to start filling the order.'
        self.__aux_soa_inventory(
            do_availability_check=True,
            soa_info_expected_msg=soa_info_expected_msg)

    def __aux_test_soa_credit_check(
            self, do_credit_check, soa_info_expected_msg,
            soa_info_expected_state):
        """ Auxiliary method for tests _test_soa_credit_check_*()
        """
        cr, uid, ctx = self.cr, self.uid, self.context

        order_obj = self.registry('sale.order')

        soa_info = SaleOrderAutomationResult()

        # Sets the payment method to require a credit check.
        test_payment_method_id = \
            self.ref('pc_sale_order_automation.test_payment_invoice')
        self.registry('payment.method').write(cr, uid, test_payment_method_id,
                                              {'credit_check': True},
                                              context=ctx)

        # Creates a sale order and adds a line.
        order_id = self.__create_sale_order()
        self.__create_sale_order_line(order_id)

        # Creates a stock type and associates it to the sale order.
        stock_type_vals = {
            "name": "Stock Type",
            "credit_check": do_credit_check,
        }
        stock_type_id = self.__create_stock_type(stock_type_vals)
        order_obj.write(
            cr, uid, order_id, {'stock_type_id': stock_type_id}, ctx)

        # The call to the method to test.
        order_obj.check_if_credit_check(
            cr, uid, order_id, soa_info, ctx)

        # Tests.
        self.assertEqual(soa_info.message, soa_info_expected_msg)
        self.assertEqual(soa_info.next_state, soa_info_expected_state)
        self.assertEqual(soa_info.delay, False)

    @skipIf(UNDER_DEVELOPMENT, UNDER_DEVELOPMENT_TEXT)
    def test_soa_credit_check_do_not_check(self):
        """ Tests test_check_if_credit_check_do_not_check() for the case in
            which we do not want to perform a credit check.
        """
        cr, uid, ctx = self.cr, self.uid, self.context

        soa_info_expected_msg = \
            'Credit check skipped because of stock.type.'
        self.__aux_test_soa_credit_check(
            do_credit_check=False,
            soa_info_expected_msg=soa_info_expected_msg,
            soa_info_expected_state='saleorder_draft')

    @skipIf(UNDER_DEVELOPMENT, UNDER_DEVELOPMENT_TEXT)
    def test_soa_credit_check_do_check_positive(self):
        """ Tests test_check_if_credit_check_do_check() for the case in
            which we do want to perform a credit check. The sale order is not
            rejected in this case.
        """
        cr, uid, ctx = self.cr, self.uid, self.context

        # Sets the partner to not have credit (so that if we activate the
        # credit check, it fails).
        test_partner_person_id = \
            self.ref('pc_sale_order_automation.test_partner_person')
        self.registry('res.partner').write(cr, uid, test_partner_person_id,
                                           {'credit': 1, 'credit_limit': 1e6},
                                           context=ctx)

        soa_info_expected_msg = \
            'Sale.order was NOT rejected because of the ' \
            'credit-worthiness check.'
        self.__aux_test_soa_credit_check(
            do_credit_check=True,
            soa_info_expected_msg=soa_info_expected_msg,
            soa_info_expected_state='saleorder_draft')

    @skipIf(UNDER_DEVELOPMENT, UNDER_DEVELOPMENT_TEXT)
    def test_soa_credit_check_do_check_negative(self):
        """ Tests test_check_if_credit_check_do_check() for the case in
            which we do want to perform a credit check. The sale order is
            rejected in this case.
        """
        cr, uid, ctx = self.cr, self.uid, self.context

        # Sets the partner to not have credit (so that if we activate the
        # credit check, it fails).
        test_partner_person_id = \
            self.ref('pc_sale_order_automation.test_partner_person')
        self.registry('res.partner').write(cr, uid, test_partner_person_id,
                                           {'credit': 1, 'credit_limit': 1},
                                           context=ctx)

        soa_info_expected_msg = \
            'Sale.order was rejected because of the ' \
            'credit-worthiness check.'
        self.__aux_test_soa_credit_check(
            do_credit_check=True,
            soa_info_expected_msg=soa_info_expected_msg,
            soa_info_expected_state='saleorder_checkcredit')

    @skipIf(UNDER_DEVELOPMENT, UNDER_DEVELOPMENT_TEXT)
    def test_soa_draft_to_sent_delayed(self):
        """ Tests _process_workflow_saleorder_draft_to_sent() when the
            warehouse is closed, and the job has to be delayed.
        """
        cr, uid, ctx = self.cr, self.uid, self.context

        order_obj = self.registry('sale.order')

        soa_info = SaleOrderAutomationResult()

        # Creates an order.
        order_id = self.__create_sale_order()

        # Adds a line to the order.
        self.__create_sale_order_line(order_id)

        # Creates a stock type and associates it to the order.
        stock_type_vals = {
            'name': 'Stock Type No Dropship',
            'consider_aging': True,
            'dropship': False,
        }
        stock_type_id = self.__create_stock_type(stock_type_vals)
        order_obj.write(
            cr, uid, order_id, {'stock_type_id': stock_type_id}, ctx)

        # Sets the support as being closed so that the order is delayed.
        config = self.registry('configuration.data').get(cr, uid, [], ctx)
        config_vals = {}
        for day_str in ('monday', 'tuesday', 'wednesday', 'thursday',
                        'friday', 'saturday', 'sunday'):
            config_vals.update({'support_open_{0}'.format(day_str): False})
        self.registry('configuration.data').\
            write(cr, uid, config.id, config_vals, context=ctx)

        # The call to the method to test.
        order_obj._process_workflow_saleorder_draft_to_sent(
            cr, uid, order_id, soa_info, ctx)

        # Tests.
        self.assertEqual(soa_info.delay, True)
        self.assertEqual(soa_info.message, JOB_DELAYED_MESSAGE)

    def __aux_test_soa_draft_to_sent(
            self, expected_order_line_type, is_dropship, expected_line_delay):
        """ Auxiliary method for test_soa_draft_to_sent_*().
        """
        cr, uid, ctx = self.cr, self.uid, self.context

        order_obj = self.registry('sale.order')

        soa_info = SaleOrderAutomationResult()

        # Creates an order.
        order_id = self.__create_sale_order()

        # Adds a line to the order.
        self.__create_sale_order_line(order_id)

        # Creates a stock type and associates it to the order.
        stock_type_vals = {
            'name': 'Stock Type',
            'consider_aging': False,
            'dropship': is_dropship,
        }
        stock_type_id = self.__create_stock_type(stock_type_vals)
        order_obj.write(
            cr, uid, order_id, {'stock_type_id': stock_type_id}, ctx)

        # Pre-tests.
        order = order_obj.browse(cr, uid, order_id, context=ctx)
        for line in order.order_line:
            self.assertEqual(
                line.type, 'make_to_stock',
                "Type of line with ID={0} is {1} while should be {2}.".
                format(line.id, line.type, 'make_to_stock'))
        self.assertEqual(order.state, 'draft',
                         "State should be 'draft' but is {0}".
                         format(order.state))

        # The call to the method to test.
        order_obj._process_workflow_saleorder_draft_to_sent(
            cr, uid, order_id, soa_info, ctx)

        # Tests.
        order = order_obj.browse(cr, uid, order_id, context=ctx)
        for line in order.order_line:
            self.assertEqual(
                line.type, expected_order_line_type,
                "Type of line with ID={0} is {1} while it should be {2}.".
                format(line.id, line.type, expected_order_line_type))
            self.assertEqual(
                line.delay, expected_line_delay,
                "Delay of line with ID={0} is {1} while should be {2}".
                format(line.id, line.delay, 'zero'))
        self.assertEqual(order.state, 'sent',
                         "State should be 'sent' but is {0}".
                         format(order.state))
        self.assertEqual(
            order.order_policy, 'manual',
            "The order policy should be 'manual' but it is {0}.".
            format(order.order_policy))
        self.assertEqual(soa_info.delay, False)
        self.assertEqual(soa_info.next_state, 'saleorder_sent')
        self.assertEqual(soa_info.message,
                         "Changes a sale order from state 'draft' to 'sent'.")

    @skipIf(UNDER_DEVELOPMENT, UNDER_DEVELOPMENT_TEXT)
    def test_soa_draft_to_sent_dropship(self):
        """ Tests _process_workflow_saleorder_draft_to_sent() for the dropship
            case.
        """
        self.__aux_test_soa_draft_to_sent(
            'make_to_order', is_dropship=True,
            expected_line_delay=0)

    @skipIf(UNDER_DEVELOPMENT, UNDER_DEVELOPMENT_TEXT)
    def test_soa_draft_to_sent_regular(self):
        """ Tests _process_workflow_saleorder_draft_to_sent() for the regular
            case (i.e. the one which is no dropship).
        """
        self.__aux_test_soa_draft_to_sent(
            'make_to_stock', is_dropship=False,
            expected_line_delay=DEFAULT_LINE_DELAY)

    def __aux_test_soa_sent_to_router_assignation(
            self, initial_picking_policy, forced_picking_policy,
            expected_next_state, is_dropship):
        """ Auxiliary for test_soa_sent_to_router_assignation_*()
        """
        cr, uid, ctx = self.cr, self.uid, self.context

        order_obj = self.registry('sale.order')

        soa_info = SaleOrderAutomationResult()

        # Sets the support as being closed so that the order is delayed.
        config = self.registry('configuration.data').get(cr, uid, [], ctx)
        self.registry('configuration.data').write(
            cr, uid, config.id, {'default_picking_policy': 'keep'},
            context=ctx)

        # Creates an order.
        order_id = self.__create_sale_order(
            {'picking_policy': initial_picking_policy})

        # Adds a line to the order.
        self.__create_sale_order_line(order_id)

        # Creates a stock type and associates it to the order.
        stock_type_vals = {
            'name': 'Test Stock Type',
            'consider_aging': False,
            'dropship': is_dropship,
            'forced_picking_policy': forced_picking_policy,
        }
        stock_type_id = self.__create_stock_type(stock_type_vals)
        order_obj.write(
            cr, uid, order_id, {'stock_type_id': stock_type_id}, ctx)

        # Pre-condition: move to state 'sent'.
        order_obj._process_workflow_saleorder_draft_to_sent(
            cr, uid, order_id, soa_info, ctx)

        # Pre-tests.
        order = order_obj.browse(cr, uid, order_id, context=ctx)
        self.assertEqual(order.picking_policy, initial_picking_policy,
                         "Picking policy should be {0} but is {1}".
                         format(initial_picking_policy, order.picking_policy))

        # The call to the method to test.
        order_obj._process_workflow_saleorder_sent_to_router(
            cr, uid, order_id, soa_info, ctx)

        # Tests.
        order = order_obj.browse(cr, uid, order_id, context=ctx)
        self.assertEqual(order.state, 'manual',
                         "State should be 'manual' but is {0}".
                         format(order.state))

        self.assertEqual(soa_info.delay, False)
        self.assertEqual(
            soa_info.next_state, expected_next_state)
        self.assertEqual(
            soa_info.message,
            "Changes a sale order from state 'sent' to 'router'.")

    @skipIf(UNDER_DEVELOPMENT, UNDER_DEVELOPMENT_TEXT)
    def test_soa_sent_to_router_assignation_one(self):
        """ Tests _process_workflow_saleorder_sent_to_router() for
            assignation 'one'.
        """
        self.__aux_test_soa_sent_to_router_assignation(
            'direct', 'one', 'deliveryorder_assignation_one',
            is_dropship=False)

    @skipIf(UNDER_DEVELOPMENT, UNDER_DEVELOPMENT_TEXT)
    def test_soa_sent_to_router_assignation_direct(self):
        """ Tests _process_workflow_saleorder_sent_to_router() for
            assignation 'direct'.
        """
        self.__aux_test_soa_sent_to_router_assignation(
            'one', 'direct', 'deliveryorder_assignation_direct',
            is_dropship=False)

    @skipIf(UNDER_DEVELOPMENT, UNDER_DEVELOPMENT_TEXT)
    def test_soa_sent_to_router_assignation_dropship(self):
        """ Tests _process_workflow_saleorder_sent_to_router() for
            assignation 'dropship'.
        """
        self.__aux_test_soa_sent_to_router_assignation(
            'direct', 'keep', 'deliveryorder_assignation_dropship',
            is_dropship=True)

    @skipIf(UNDER_DEVELOPMENT, UNDER_DEVELOPMENT_TEXT)
    def test_soa_not_enough_qty_several_shops_picking_direct(self):
        """ Tests a sale order through the Sale Order Automation (SOA)
            with picking policy 'direct'. The item has enough items if the
            inventory on all the warehouses is taken into account, but not
            enough if the contents for the shop are considered, thus
            it'll create a backorder.
        """
        cr, uid, ctx = self.cr, self.uid, self.context
        order_obj = self.registry('sale.order')

        prod_id = self.create_product(self, {'name': 'PROD-SOA-1'})

        # Orders 4 items for shop 1.
        shop_1_id = self.ref('pc_connect_master.shop1')
        self.obtain_qty(self, prod_id, 7, shop_1_id)

        # Orders 3 items for shop 2.
        shop_2_id = self.ref('pc_connect_master.shop2')
        self.obtain_qty(self, prod_id, 3, shop_2_id)

        # Orders 4 items for shop 2 (which only has 3) with picking policy
        # set to be 'direct'.
        order_id = self.__create_sale_order({
            'picking_policy': 'direct',
            'shop_id': shop_2_id,
        })
        self.__create_sale_order_line(order_id, {
            'product_id': prod_id,
            'product_uom_qty': 4,
        })

        # The inventory check of the SOA must be positive (at this step).
        soa_info = order_obj.automate_sale_order(
            cr, uid, [order_id], 'saleorder_check_inventory_for_quotation',
            False, False, context=ctx)
        self.assertEqual(soa_info.next_state,'saleorder_checkcredit')
        self.assertFalse(soa_info.delay)

        # We move forward in the SOA.
        for soa_state, next_soa_state_expected in [
            ('saleorder_draft', 'saleorder_sent'),
            ('saleorder_sent', 'deliveryorder_assignation_direct'),
            ('deliveryorder_assignation_direct', 'print_deliveryorder_in_local'),
        ]:
            soa_info = order_obj.automate_sale_order(
                cr, uid, [order_id], soa_state, False, False, context=ctx)
            self.assertEqual(soa_info.next_state, next_soa_state_expected)

        # Check that the sale order now has two pickings, one assigned and
        # the other confirmed.
        order = order_obj.browse(cr, uid, order_id, context=ctx)
        self.assertEqual(len(order.picking_ids), 2)
        states = set([p.state for p in order.picking_ids])
        self.assertEqual(states, set(['confirmed', 'assigned']))

    @skipIf(UNDER_DEVELOPMENT, UNDER_DEVELOPMENT_TEXT)
    def test_soa_not_enough_qty_several_shops_picking_one(self):
        """ Tests a sale order through the Sale Order Automation (SOA)
            with picking policy 'one'. The item has enough items if the
            inventory on all the warehouses is taken into account, but not
            enough if the contents for the shop are considered, thus
            the inventory check will be negative.
        """
        cr, uid, ctx = self.cr, self.uid, self.context
        order_obj = self.registry('sale.order')

        prod_id = self.create_product(self, {'name': 'PROD-SOA-1'})

        # Orders 4 items for shop 1.
        shop_1_id = self.ref('pc_connect_master.shop1')
        self.obtain_qty(self, prod_id, 7, shop_1_id)

        # Orders 3 items for shop 2.
        shop_2_id = self.ref('pc_connect_master.shop2')
        self.obtain_qty(self, prod_id, 3, shop_2_id)

        # Orders 4 items for shop 2 (which only has 3) with picking policy
        # set to be 'one'.
        order_id = self.__create_sale_order({
            'picking_policy': 'one',
            'shop_id': shop_2_id,
        })
        self.__create_sale_order_line(order_id, {
            'product_id': prod_id,
            'product_uom_qty': 4,
        })

        # The inventory check of the SOA must be negative.
        soa_info = order_obj.automate_sale_order(
            cr, uid, [order_id], 'saleorder_check_inventory_for_quotation',
            False, False, context=ctx)
        self.assertTrue(soa_info.delay)
