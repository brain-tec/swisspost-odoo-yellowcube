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
from openerp.tests import common
from openerp.addons.pc_connect_master.tests.common import \
    CommonTestFunctionality
from common import CommonTestFunctionalitySOA

UNDER_DEVELOPMENT = False
UNDER_DEVELOPMENT_TEXT = 'Test was skipped because of being under development'


class TestSaleOrderAutomationWithPickingSplit(common.TransactionCase,
                                              CommonTestFunctionality,
                                              CommonTestFunctionalitySOA):

    def setUp(self):
        super(TestSaleOrderAutomationWithPickingSplit, self).setUp()
        self.context = {}

        ir_report_obj = self.registry('ir.actions.report.xml')
        ir_model_data_obj = self.registry('ir.model.data')

        # Creates the products.
        self.prod_id = {
            'a': self.create_product(self, {'name': 'Prod A'}),
            'b': self.create_product(self, {'name': 'Prod B'}),
            'c': self.create_product(self, {'name': 'Prod C'}),
        }

        # Gets quantities for each product.
        shop_1_id = self.ref('sale.sale_shop_1')
        self.prod_qty = {'a': 5, 'b': 7, 'c': 3}
        self.obtain_qty(self, self.prod_id['a'], self.prod_qty['a'], shop_1_id)
        self.obtain_qty(self, self.prod_id['b'], self.prod_qty['b'], shop_1_id)
        self.obtain_qty(self, self.prod_id['c'], self.prod_qty['c'], shop_1_id)

        # Sets the configuration parameters common to all the tests.
        self.set_config(self, 'default_picking_policy', 'keep')
        self.set_config(self, 'sale_order_min_age_in_draft_value', 0)
        self.set_config(self, 'support_start_time', 7)
        self.set_config(self, 'support_soft_end_time', 22)
        self.set_config(self, 'support_end_time', 23)
        for weekday in [
            'monday', 'tuesday', 'wednesday', 'thursday', 'friday',
            'saturday', 'sunday',
        ]:
            self.set_config(self, 'support_open_{0}'.format(weekday), True)

        invoice_report_id = self.ref('pc_account.report_invoice')
        self.set_config(self, 'report_account_invoice', invoice_report_id)
        picking_report_id = self.ref('delivery.report_shipping')
        self.set_config(self, 'report_stock_picking', picking_report_id)

    def _set_allowed_carrier_on_product(self, prod_id, carrier_id):
        """ Sets a carrier as an allowed one for a product.
        """
        prod = self.registry('product.product').browse(
            self.cr, self.uid, prod_id, context=self.context)
        self.registry('delivery.carrier.product.template').create(
            self.cr, self.uid, {
                'delivery_carrier_id': carrier_id,
                'product_template_id': prod.product_tmpl_id.id,
            }, context=self.context)

    def _set_alternative_carrier_on_carrier(self, carrier_id, alt_carrier_id):
        """ Sets a carrier as an alternative carrier for a carrier.
        """
        self.registry('delivery.carrier.replacement').create(
            self.cr, self.uid, {
                'original_carrier_id': carrier_id,
                'replacement_carrier_id': alt_carrier_id,
            }, context=self.context)

    def _set_stock_type_on_order_carrier(self, order_id, stock_type_id):
        """ Sets the stock type on the carrier of the received order.
        """
        cr, uid, context = self.cr, self.uid, self.context
        sale_order_obj = self.registry('sale.order')
        carrier_obj = self.registry('delivery.carrier')

        order = sale_order_obj.browse(cr, uid, order_id, context=context)
        carrier_obj.write(cr, uid, order.carrier_id.id, {
            'stock_type_id': stock_type_id,
        }, context=context)

    def _check_full_invoice_is_attached(self, order_id):
        """ Checks that one invoice has been created & opened & printed,
            with all the lines of the sale.order.
        """
        cr, uid, context = self.cr, self.uid, self.context
        sale_order_obj = self.registry('sale.order')
        attach_obj = self.registry('ir.attachment')

        order = sale_order_obj.browse(cr, uid, order_id, context=context)

        # Checks that there is just one invoice for the order.
        num_invoices = len(order.invoice_ids)
        self.assertEqual(num_invoices, 1,
                         "Just one invoice should be linked to the order, "
                         "but {0} were found instead.".format(num_invoices))

        # Checks that the paper-invoice is attached to the invoice.
        conf = self.browse_ref('pc_config.default_configuration_data')
        has_invoice = attach_obj.search(
            cr, uid, [
                ('res_model', '=', 'account.invoice'),
                ('res_id', '=', order.invoice_ids[0].id)
            ], count=True, limit=1, context=context)
        self.assertTrue(has_invoice)

        # Checks that the invoice has as many lines as the sale.order has.
        order_lines = {}
        for order_line in order.order_line:
            order_lines[order_line.id] = False
        for invoice_line in order.invoice_ids[0].invoice_line:
            order_line = invoice_line.orig_sale_order_line_id
            self.assertTrue(order_line)
            self.assertFalse(order_lines[order_line.id])
            order_lines[order_line.id] = True
        self.assertTrue(all(order_lines.values()))

    def _automate_order_until_assignation_direct(self, make_backorders,
                                                 make_picking_split):
        """ Creates an automates a sale.order, with picking_policy=direct,
            which results in a split of the pickings because of the different
            delivery methods used.
        """
        cr, uid, context = self.cr, self.uid, self.context
        sale_order_obj = self.registry('sale.order')

        # Creates the sale order and associates the three products to it.
        # If we want to make backorders, we ask for more quantities than
        # we have.
        extra_qty = 1 if make_backorders else 0
        order_id = self.create_sale_order(self, {'picking_policy': 'direct'})
        for prod_letter in ['a', 'b', 'c']:
            self.create_sale_order_line(self, {
                'product_id': self.prod_id[prod_letter],
                'name': 'Prod {0}'.format(prod_letter.upper()),
                'product_uom_qty': self.prod_qty[prod_letter] + extra_qty,
                'order_id': order_id,
            })

        # Sets the stock type for the carrier that uses the sale.order
        # to be of type regular.
        stock_type_regular_direct_id = \
            self.ref('pc_sale_order_automation.test_stock_type_regular_direct')
        self._set_stock_type_on_order_carrier(
            order_id, stock_type_regular_direct_id)

        if make_picking_split:
            # Sets the carrier of the order to be a different one than the one
            # which is set on the sale order; and makes those other carriers
            # to be alternative delivery methods for the carrier of the order.
            order = sale_order_obj.browse(cr, uid, order_id, context=context)
            prod_carrier_ids = {
                'a': self.ref(
                    'pc_sale_order_automation.delivery_carrier_direct_a'),
                'b': self.ref(
                    'pc_sale_order_automation.delivery_carrier_direct_b'),
                'c': self.ref(
                    'pc_sale_order_automation.delivery_carrier_direct_c'),
            }
            for prod_letter in ['a', 'b', 'c']:
                prod_id = self.prod_id[prod_letter]
                prod_carrier_id = prod_carrier_ids[prod_letter]
                self.assertNotEqual(prod_carrier_id, order.carrier_id.id,
                                    "Carrier for product and carrier for "
                                    "order must be different in this test.")
                self._set_allowed_carrier_on_product(prod_id, prod_carrier_id)
                self._set_alternative_carrier_on_carrier(
                    order.carrier_id.id, prod_carrier_id)
        else:
            # Sets the carrier of the order to be a valid one for the products.
            order = sale_order_obj.browse(cr, uid, order_id, context=context)
            for prod_letter in ['a', 'b', 'c']:
                prod_id = self.prod_id[prod_letter]
                self._set_allowed_carrier_on_product(prod_id,
                                                     order.carrier_id.id)

        # Automates the sale order.
        self._automate_order(self, order_id,
                             'saleorder_check_inventory_for_quotation',
                             'deliveryorder_assignation_direct',
                             'direct')

        # There should be several pickings associated to the sale.order,
        # and no invoices (yet). Several of the pickings may be
        # backorders depending on the parameter received.
        order = sale_order_obj.browse(cr, uid, order_id, context=context)
        num_pickings = len(order.picking_ids)
        num_invoices = len(order.invoice_ids)

        if make_picking_split:
            if make_backorders:
                expected_num_pickings = 6
                expected_num_backorders = 3
            else:
                expected_num_pickings = 3
                expected_num_backorders = 0
        else:
            if make_backorders:
                expected_num_pickings = 2
                expected_num_backorders = 1
            else:
                expected_num_pickings = 1
                expected_num_backorders = 0

        self.assertEqual(num_pickings, expected_num_pickings,
                         "There should be {0} pickings for the order, "
                         "but {1} were found instead.".format(
                             expected_num_pickings, num_pickings))
        self.assertEqual(num_invoices, 0,
                         "There should be {0} invoices for the order, "
                         "but {1} were found instead.".format(0, num_invoices))
        num_backorders = len([p.id for p in order.picking_ids
                              if p.backorder_id])
        self.assertEqual(num_backorders, expected_num_backorders,
                         "There should be {0} backorders, but {1} were "
                         "found instead.".format(expected_num_backorders,
                                                 num_backorders))

        # The backorders, if any, must be in state 'confirmed' while
        # the regular pickings must be in state 'assigned'.
        for picking in order.picking_ids:
            if picking.backorder_id:
                self.assertEqual(picking.state, 'confirmed',
                                 "Backorder picking with ID={0} has a "
                                 "wrong state.".format(picking.state))
            else:
                self.assertEqual(picking.state, 'assigned',
                                 "Picking with ID={0} has a wrong "
                                 "state.".format(picking.state))

        if make_picking_split:
            # Checks that the carriers of the pickings are the ones for the
            # products, not the ones for the sale.order.
            actual_carrier_ids = set(prod_carrier_ids.values())
            expected_carrier_ids = set()
            for picking in order.picking_ids:
                expected_carrier_ids.add(picking.carrier_id.id)
            self.assertEqual(expected_carrier_ids, actual_carrier_ids)
        else:
            # Checks that the carrier of the picking is the one for the
            # sale.order
            self.assertEqual(picking.carrier_id.id, order.carrier_id.id)

        return order_id

    def _check_only_non_backorder_pickings_are_attached(self, order_id):
        """ Checks that just the pickings which are not backorders
            should be printed.
        """
        cr, uid, context = self.cr, self.uid, self.context
        sale_order_obj = self.registry('sale.order')
        attach_obj = self.registry('ir.attachment')

        conf = self.browse_ref('pc_config.default_configuration_data')
        order = sale_order_obj.browse(cr, uid, order_id, context=context)
        for picking in order.picking_ids:
            has_attachment = attach_obj.search(
                cr, uid, [
                    ('res_model', '=', 'stock.picking.out'),
                    ('res_id', '=', picking.id),
                ], count=True, limit=1)
            if picking.backorder_id:
                # If it's a backorder,
                # it should NOT have the picking printed.
                self.assertFalse(has_attachment)
            else:
                # If it's not a backorder,
                # it should have the picking printed.
                self.assertTrue(has_attachment)

    @skipIf(UNDER_DEVELOPMENT, UNDER_DEVELOPMENT_TEXT)
    def test_soa_one_picking_not_splitted(self):
        """ SOA with picking-policy=one, pickings not splitted.
        """
        cr, uid, context = self.cr, self.uid, self.context
        sale_order_obj = self.registry('sale.order')

        # Creates the sale order and associates the three products to it,
        # with no more quantities that we have for them.
        order_id = self.create_sale_order(self, {'picking_policy': 'one'})
        for prod_letter in ['a', 'b', 'c']:
            self.create_sale_order_line(self, {
                'product_id': self.prod_id[prod_letter],
                'name': 'Prod {0}'.format(prod_letter.upper()),
                'product_uom_qty': self.prod_qty[prod_letter],
                'order_id': order_id,
            })

        # Sets the stock type for the carrier that uses the sale.order
        # to be of type regular.
        stock_type_regular_one_id = \
            self.ref('pc_sale_order_automation.test_stock_type_regular_one')
        self._set_stock_type_on_order_carrier(
            order_id, stock_type_regular_one_id)

        # Sets the carrier of the order to be a valid one for the products.
        order = sale_order_obj.browse(cr, uid, order_id, context=context)
        for prod_letter in ['a', 'b', 'c']:
            prod_id = self.prod_id[prod_letter]
            self._set_allowed_carrier_on_product(prod_id, order.carrier_id.id)

        # Automates the sale order.
        self._automate_order(self, order_id,
                             'saleorder_check_inventory_for_quotation',
                             'deliveryorder_assignation_one',
                             'one')

        # There should be just one picking associated to the sale.order,
        # and no invoices (yet).
        order = sale_order_obj.browse(cr, uid, order_id, context=context)
        num_pickings = len(order.picking_ids)
        num_invoices = len(order.invoice_ids)
        self.assertEqual(num_pickings, 1,
                         "There should be just one picking for the order, "
                         "but {0} were found instead.".format(num_pickings))
        self.assertEqual(num_invoices, 0,
                         "There should be no invoices for the order, "
                         "but {0} were found instead.".format(num_invoices))

        # Prints the pickings.
        self._automate_order(self, order_id,
                             'print_deliveryorder_in_local',
                             'print_deliveryorder_in_local',
                             'one')
        self._check_only_non_backorder_pickings_are_attached(order_id)

        # Prints the invoices and finishes the automation.
        self._automate_order(self, order_id,
                             'invoice_open',
                             'print_invoice_in_local',
                             'one')
        self._check_full_invoice_is_attached(order_id)

        order = sale_order_obj.browse(cr, uid, order_id, context=context)
        self.assertTrue(order.automation_finished)

    @skipIf(UNDER_DEVELOPMENT, UNDER_DEVELOPMENT_TEXT)
    def test_soa_one_picking_splitted(self):
        """ SOA with picking-policy=one, no backorders, no picking split.
        """
        cr, uid, context = self.cr, self.uid, self.context
        sale_order_obj = self.registry('sale.order')

        # Creates the sale order and associates the three products to it,
        # with no more quantities that we have for them.
        order_id = self.create_sale_order(self, {'picking_policy': 'one'})
        for prod_letter in ['a', 'b', 'c']:
            self.create_sale_order_line(self, {
                'product_id': self.prod_id[prod_letter],
                'name': 'Prod {0}'.format(prod_letter.upper()),
                'product_uom_qty': self.prod_qty[prod_letter],
                'order_id': order_id,
            })

        # Sets the stock type for the carrier that uses the sale.order
        # to be of type regular.
        stock_type_regular_one_id = \
            self.ref('pc_sale_order_automation.test_stock_type_regular_one')
        self._set_stock_type_on_order_carrier(
            order_id, stock_type_regular_one_id)

        # Sets the carrier of the order to be a different one than the one
        # which is set on the sale order; and makes those other carriers
        # to be alternative delivery methods for the carrier of the order.
        order = sale_order_obj.browse(cr, uid, order_id, context=context)
        prod_carrier_ids = {
            'a': self.ref('pc_sale_order_automation.delivery_carrier_one_a'),
            'b': self.ref('pc_sale_order_automation.delivery_carrier_one_b'),
            'c': self.ref('pc_sale_order_automation.delivery_carrier_one_c'),
        }
        for prod_letter in ['a', 'b', 'c']:
            prod_id = self.prod_id[prod_letter]
            prod_carrier_id = prod_carrier_ids[prod_letter]
            self.assertNotEqual(prod_carrier_id, order.carrier_id.id,
                                "Carrier for product and carrier for order "
                                "must be different in this test.")
            self._set_allowed_carrier_on_product(prod_id, prod_carrier_id)
            self._set_alternative_carrier_on_carrier(
                order.carrier_id.id, prod_carrier_id)

        # Automates the sale order.
        self._automate_order(self, order_id,
                             'saleorder_check_inventory_for_quotation',
                             'deliveryorder_assignation_one',
                             'one')

        # There should be three pickings associated to the sale.order,
        # because of the alternative carriers,
        # and no invoices (yet).
        order = sale_order_obj.browse(cr, uid, order_id, context=context)
        num_pickings = len(order.picking_ids)
        num_invoices = len(order.invoice_ids)
        self.assertEqual(num_pickings, 3,
                         "There should be three pickings for the order, "
                         "but {0} were found instead.".format(num_pickings))
        self.assertEqual(num_invoices, 0,
                         "There should be no invoices for the order, "
                         "but {0} were found instead.".format(num_invoices))

        # Checks that the carriers of the pickings are the ones for the
        # products, not the ones for the sale.order.
        actual_carrier_ids = set(prod_carrier_ids.values())
        expected_carrier_ids = set()
        for picking in order.picking_ids:
            expected_carrier_ids.add(picking.carrier_id.id)
        self.assertEqual(expected_carrier_ids, actual_carrier_ids)

        # Prints the pickings.
        self._automate_order(self, order_id,
                             'print_deliveryorder_in_local',
                             'print_deliveryorder_in_local',
                             'one')
        self._check_only_non_backorder_pickings_are_attached(order_id)

        # Prints the invoices and finishes the automation.
        self._automate_order(self, order_id,
                             'invoice_open',
                             'print_invoice_in_local',
                             'one')
        self._check_full_invoice_is_attached(order_id)

        order = sale_order_obj.browse(cr, uid, order_id, context=context)
        self.assertTrue(order.automation_finished)

    @skipIf(UNDER_DEVELOPMENT, UNDER_DEVELOPMENT_TEXT)
    def test_soa_direct_no_backorders_picking_not_splitted(self):
        """ SOA with picking-policy=direct, no backorders, no picking split.
        """
        cr, uid, context = self.cr, self.uid, self.context
        sale_order_obj = self.registry('sale.order')

        order_id = self._automate_order_until_assignation_direct(
            make_backorders=False, make_picking_split=False)

        # Prints the pickings.
        self._automate_order(self, order_id,
                             'print_deliveryorder_in_local',
                             'print_deliveryorder_in_local',
                             'direct')
        self._check_only_non_backorder_pickings_are_attached(order_id)

        # Prints the invoices and finishes the automation.
        self._automate_order(self, order_id,
                             'invoice_open',
                             'print_invoice_in_local',
                             'direct')
        self._check_full_invoice_is_attached(order_id)

        order = sale_order_obj.browse(cr, uid, order_id, context=context)
        self.assertTrue(order.automation_finished)

    @skipIf(UNDER_DEVELOPMENT, UNDER_DEVELOPMENT_TEXT)
    def test_soa_direct_no_backorders_picking_splitted(self):
        """ SOA with picking-policy=direct, no backorders, picking split.
        """
        cr, uid, context = self.cr, self.uid, self.context
        sale_order_obj = self.registry('sale.order')

        order_id = self._automate_order_until_assignation_direct(
            make_backorders=False, make_picking_split=True)

        # Prints the pickings.
        self._automate_order(self, order_id,
                             'print_deliveryorder_in_local',
                             'print_deliveryorder_in_local',
                             'direct')
        self._check_only_non_backorder_pickings_are_attached(order_id)

        # Prints the invoices and finishes the automation.
        self._automate_order(self, order_id,
                             'invoice_open',
                             'print_invoice_in_local',
                             'direct')
        self._check_full_invoice_is_attached(order_id)

        order = sale_order_obj.browse(cr, uid, order_id, context=context)
        self.assertTrue(order.automation_finished)

    @skipIf(UNDER_DEVELOPMENT, UNDER_DEVELOPMENT_TEXT)
    def test_soa_direct_backorders_picking_not_splitted(self):
        """ SOA with picking-policy=direct, with backorders, no picking split.
        """
        cr, uid, context = self.cr, self.uid, self.context
        sale_order_obj = self.registry('sale.order')

        order_id = self._automate_order_until_assignation_direct(
            make_backorders=True, make_picking_split=False)

        # Prints the pickings.
        self._automate_order(self, order_id,
                             'print_deliveryorder_in_local',
                             'print_deliveryorder_in_local',
                             'direct')
        self._check_only_non_backorder_pickings_are_attached(order_id)

        # Prints the invoices and finishes the automation.
        self._automate_order(self, order_id,
                             'invoice_open',
                             'print_invoice_in_local',
                             'direct')
        self._check_full_invoice_is_attached(order_id)

        order = sale_order_obj.browse(cr, uid, order_id, context=context)
        self.assertTrue(order.automation_finished)

    @skipIf(UNDER_DEVELOPMENT, UNDER_DEVELOPMENT_TEXT)
    def test_soa_direct_backorders_picking_splitted(self):
        """ SOA with picking-policy=direct, with backorders, picking split.
        """
        cr, uid, context = self.cr, self.uid, self.context
        sale_order_obj = self.registry('sale.order')

        order_id = self._automate_order_until_assignation_direct(
            make_backorders=True, make_picking_split=True)

        # Prints the pickings.
        self._automate_order(self, order_id,
                             'print_deliveryorder_in_local',
                             'print_deliveryorder_in_local',
                             'direct')
        self._check_only_non_backorder_pickings_are_attached(order_id)

        # Prints the invoices and finishes the automation.
        self._automate_order(self, order_id,
                             'invoice_open',
                             'print_invoice_in_local',
                             'direct')
        self._check_full_invoice_is_attached(order_id)

        order = sale_order_obj.browse(cr, uid, order_id, context=context)
        self.assertTrue(order.automation_finished)

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
