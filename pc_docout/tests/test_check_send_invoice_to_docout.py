# -*- coding: utf-8 -*-
#
#    Copyright (c) 2017 brain-tec AG (http://www.braintec-group.com)
#    All Right Reserved
#
#    See LICENSE file for full licensing details.

from unittest2 import skipIf
from openerp.osv import osv, fields
from openerp.tests.common import TransactionCase
import netsvc


UNDER_DEVELOPMENT = False
UNDER_DEVELOPMENT_TEXT = 'Test skipped because of being under development.'


class TestCheckSendInvoiceToDocout(TransactionCase):

    def setUp(self):
        super(TestCheckSendInvoiceToDocout, self).setUp()
        self.context = {}

        cr, uid, ctx = self.cr, self.uid, self.context

        conf_id = self.ref('pc_config.default_configuration_data')
        self.registry('configuration.data').write(
            cr, uid, conf_id, {'default_picking_policy': 'keep'}, context=ctx)

    def _create_sale_order(self, picking_policy, invoice_policy,
                           addresses_equal, epaid, positive_amount):
        cr, uid, ctx = self.cr, self.uid, self.context

        order_obj = self.registry('sale.order')
        order_line_obj = self.registry('sale.order.line')

        # Creates the sale.order.
        order_vals = {
            'picking_policy': picking_policy,
            'invoice_policy': invoice_policy,
            'partner_id': self.ref('base.res_partner_2'),
            'date_order': fields.date.today(),
            'carrier_id': self.ref('delivery.delivery_carrier'),
            'pricelist_id': self.ref('product.list0'),
        }

        if addresses_equal:
            order_vals.update({
                'partner_invoice_id': self.ref('base.res_partner_address_3'),
                'partner_shipping_id': self.ref('base.res_partner_address_3'),
            })
        else:
            order_vals.update({
                'partner_invoice_id': self.ref('base.res_partner_address_3'),
                'partner_shipping_id': self.ref('base.res_partner_address_4'),
            })

        if epaid:
            order_vals.update({
                'payment_method_id':
                    self.ref('pc_connect_master.payment_method_epaid'),
            })
        else:
            order_vals.update({
                'payment_method_id':
                    self.ref('pc_connect_master.payment_method_not_epaid'),
            })
        sale_order_id = order_obj.create(cr, uid, order_vals, ctx)

        # Creates the sale.order.line and associates it to the sale.order.
        order_line_vals = {
            'product_id': self.ref('product.product_product_48'),
            'name': 'Default Name',
            'product_uom_qty': 7,
            'type': 'make_to_stock',
            'delay': 0,
            'order_id': sale_order_id,
            'product_uom': self.ref('product.product_uom_unit'),
        }
        if positive_amount:
            order_line_vals.update({'price_unit': 1.0})
        else:
            order_line_vals.update({'price_unit': 0.0})
        order_line_obj.create(cr, uid, order_line_vals, ctx)

        return sale_order_id

    def _validate_sale_order(self, order_id):
        """ Validates a sale order.
        """
        cr, uid, ctx = self.cr, self.uid, self.context
        order_obj = self.registry('sale.order')
        order_obj.action_button_confirm(cr, uid, [order_id], ctx)
        return True

    def _invoice_full_sale_order(self, order_id):
        """ Invoices the full sale order and assigns a partner_bank_id to it.
        """
        cr, uid, ctx = self.cr, self.uid, self.context
        sale_inv_obj = self.registry('sale.advance.payment.inv')
        order_obj = self.registry('sale.order')
        invoice_obj = self.registry('account.invoice')

        ctx = ctx.copy()
        ctx.update({
            "active_model": 'sale.order',
            "active_ids": [order_id],
            "active_id": order_id,
        })
        pay_id = \
            sale_inv_obj.create(cr, uid, {'advance_payment_method': 'all'})
        sale_inv_obj.create_invoices(cr, uid, [pay_id], context=ctx)

        # Sets the Bank Account to the invoice.
        bvr_bank_id = self.ref('pc_docout.bvr_res_partner_bank')
        order = order_obj.browse(cr, uid, order_id, context=ctx)
        for invoice in order.invoice_ids:
            invoice_obj.write(cr, uid, invoice.id,
                              {'partner_bank_id': bvr_bank_id}, context=ctx)

        return True

    def _validate_invoices(self, order_id):
        """ Validates the invoice.
        """
        cr, uid, ctx = self.cr, self.uid, self.context
        order_obj = self.registry('sale.order')

        wf_service = netsvc.LocalService('workflow')

        order = order_obj.browse(cr, uid, order_id, context=ctx)
        for invoice in order.invoice_ids:
            wf_service.trg_validate(
                uid, 'account.invoice', invoice.id, 'invoice_open', cr)
        return True

    @skipIf(UNDER_DEVELOPMENT, UNDER_DEVELOPMENT_TEXT)
    def test_if_addresses_are_equal_never_to_docout(self):
        """ If addresses are equal, then no doc-out,
            no matter what the other parameters are.
        """
        cr, uid, ctx = self.cr, self.uid, self.context
        order_obj = self.registry('sale.order')
        invoice_obj = self.registry('account.invoice')
        conf_obj = self.registry('configuration.data')

        conf_id = self.ref('pc_config.default_configuration_data')

        for show_bvr_in_report in (True, False):
            conf_obj.write(
                cr, uid, conf_id,
                {'invoice_report_show_bvr_when_zero_amount_total':
                    show_bvr_in_report}, context=ctx)

            for picking_policy in ('one', 'direct'):
                for invoice_policy in ('order', 'delivery'):
                    for epaid in (True, False):
                        for positive_amount in (True, False):

                            params_string = \
                                "show_bvr_in_report={0}, " \
                                "picking_policy={1}, invoice_policy={2}, " \
                                "epaid={3}, positive_amount={4}".format(
                                    show_bvr_in_report, picking_policy,
                                    invoice_policy, epaid, positive_amount)
                            print "Testing with {0}".format(params_string)

                            order_id = self._create_sale_order(
                                picking_policy=picking_policy,
                                invoice_policy=invoice_policy,
                                addresses_equal=True,  # The fixed parameter.
                                epaid=epaid,
                                positive_amount=positive_amount)
                            self._validate_sale_order(order_id)
                            self._invoice_full_sale_order(order_id)
                            self._validate_invoices(order_id)

                            order = order_obj.browse(
                                cr, uid, order_id, context=ctx)

                            self.assertEqual(
                                len(order.invoice_ids), 1,
                                "The sale.order was expected to have "
                                "one invoice, and it "
                                "has {0}".format(len(order.invoice_ids)))

                            send_to_docout = \
                                invoice_obj.check_send_invoice_to_docout(
                                    cr, uid, order.invoice_ids[0].id,
                                    context=ctx)
                            self.assertFalse(
                                send_to_docout,
                                "Invoice was expected NOT to be sent to the "
                                "doc-out, but it was not, with the "
                                "parameters: {0}".format(params_string))

    @skipIf(UNDER_DEVELOPMENT, UNDER_DEVELOPMENT_TEXT)
    def test_if_addresses_are_different_and_epaid_never_to_docout(self):
        """ If addresses are different and it has been epaid, then no doc-out,
            no matter what the other parameters are.
        """
        cr, uid, ctx = self.cr, self.uid, self.context
        order_obj = self.registry('sale.order')
        invoice_obj = self.registry('account.invoice')
        conf_obj = self.registry('configuration.data')

        conf_id = self.ref('pc_config.default_configuration_data')

        for show_bvr_in_report in (True, False):
            conf_obj.write(
                cr, uid, conf_id,
                {'invoice_report_show_bvr_when_zero_amount_total':
                    show_bvr_in_report}, context=ctx)

            for picking_policy in ('one', 'direct'):
                for invoice_policy in ('order', 'delivery'):
                    for positive_amount in (True, False):

                        params_string = \
                            "show_bvr_in_report={0}, " \
                            "picking_policy={1}, invoice_policy={2}, " \
                            "positive_amount={3}".format(
                                show_bvr_in_report, picking_policy,
                                invoice_policy, positive_amount)
                        print "Testing with {0}".format(params_string)

                        order_id = self._create_sale_order(
                            picking_policy=picking_policy,
                            invoice_policy=invoice_policy,
                            addresses_equal=False,  # The fixed parameter.
                            epaid=True,  # The fixed parameter.
                            positive_amount=positive_amount)
                        self._validate_sale_order(order_id)
                        self._invoice_full_sale_order(order_id)
                        self._validate_invoices(order_id)

                        order = order_obj.browse(
                            cr, uid, order_id, context=ctx)

                        self.assertEqual(
                            len(order.invoice_ids), 1,
                            "The sale.order was expected to have "
                            "one invoice, and it "
                            "has {0}".format(len(order.invoice_ids)))

                        send_to_docout = \
                            invoice_obj.check_send_invoice_to_docout(
                                cr, uid, order.invoice_ids[0].id,
                                context=ctx)
                        self.assertFalse(
                            send_to_docout,
                            "Invoice was expected NOT to be sent to the "
                            "doc-out, but it was not, with the "
                            "parameters: {0}".format(params_string))

    @skipIf(UNDER_DEVELOPMENT, UNDER_DEVELOPMENT_TEXT)
    def test_if_not_epaid_and_amount_positive_then_docout(self):
        """ If was not epaid, and the amount is >0, then doc-out but
            only if the conditions of the previous tests do not apply, that is
            this only applies if address=diferent (and invoice_policy=order,
            since this is taken into account in a next test).
        """
        cr, uid, ctx = self.cr, self.uid, self.context
        order_obj = self.registry('sale.order')
        invoice_obj = self.registry('account.invoice')
        conf_obj = self.registry('configuration.data')

        conf_id = self.ref('pc_config.default_configuration_data')

        for show_bvr_in_report in (True, False):
            conf_obj.write(
                cr, uid, conf_id,
                {'invoice_report_show_bvr_when_zero_amount_total':
                    show_bvr_in_report}, context=ctx)

            for picking_policy in ('one', 'direct'):
                params_string = \
                    "show_bvr_in_report={0}, " \
                    "picking_policy={1}".format(
                        show_bvr_in_report, picking_policy)
                print "Testing with {0}".format(params_string)

                order_id = self._create_sale_order(
                    picking_policy=picking_policy,
                    invoice_policy='order',  # Fixed parameter.
                    addresses_equal=False,  # Fixed parameter.
                    epaid=False,  # Fixed parameter.
                    positive_amount=True)  # Fixed parameter.
                self._validate_sale_order(order_id)
                self._invoice_full_sale_order(order_id)
                self._validate_invoices(order_id)

                order = order_obj.browse(
                    cr, uid, order_id, context=ctx)

                self.assertEqual(
                    len(order.invoice_ids), 1,
                    "The sale.order was expected to have "
                    "one invoice, and it "
                    "has {0}".format(len(order.invoice_ids)))

                send_to_docout = \
                    invoice_obj.check_send_invoice_to_docout(
                        cr, uid, order.invoice_ids[0].id,
                        context=ctx)
                self.assertTrue(
                    send_to_docout,
                    "Invoice was expected to be sent to the "
                    "doc-out, but it was not, with the "
                    "parameters: {0}".format(params_string))

    @skipIf(UNDER_DEVELOPMENT, UNDER_DEVELOPMENT_TEXT)
    def test_if_not_epaid_and_amount_negative_then_maybe_docout(self):
        """ If was not epaid, and the amount is <= 0, then maybe doc-out but
            only if the conditions of the previous tests do not apply, that is
            this only applies if address=diferent (and invoice_policy=order,
            since =delivery is taken into account in a next test) AND also the
            'maybe' depends on if we want to show the BVR even if the quantity
            is zero: if we want, we send it; otherwise, no.
        """
        cr, uid, ctx = self.cr, self.uid, self.context
        order_obj = self.registry('sale.order')
        invoice_obj = self.registry('account.invoice')
        conf_obj = self.registry('configuration.data')

        conf_id = self.ref('pc_config.default_configuration_data')

        for show_bvr_in_report in (True, False):
            conf_obj.write(
                cr, uid, conf_id,
                {'invoice_report_show_bvr_when_zero_amount_total':
                    show_bvr_in_report}, context=ctx)

            for picking_policy in ('one', 'direct'):
                params_string = \
                    "show_bvr_in_report={0}, " \
                    "picking_policy={1}".format(
                        show_bvr_in_report, picking_policy)
                print "Testing with {0}".format(params_string)

                order_id = self._create_sale_order(
                    picking_policy=picking_policy,
                    invoice_policy='order',  # Fixed parameter.
                    addresses_equal=False,  # Fixed parameter.
                    epaid=False,  # Fixed parameter.
                    positive_amount=False)  # Fixed parameter.
                self._validate_sale_order(order_id)
                self._invoice_full_sale_order(order_id)
                self._validate_invoices(order_id)

                order = order_obj.browse(
                    cr, uid, order_id, context=ctx)

                self.assertEqual(
                    len(order.invoice_ids), 1,
                    "The sale.order was expected to have "
                    "one invoice, and it "
                    "has {0}".format(len(order.invoice_ids)))

                send_to_docout = \
                    invoice_obj.check_send_invoice_to_docout(
                        cr, uid, order.invoice_ids[0].id,
                        context=ctx)
                if show_bvr_in_report:
                    self.assertTrue(
                        send_to_docout,
                        "Invoice was expected to be sent to the "
                        "doc-out, but it was not, with the "
                        "parameters: {0}".format(params_string))
                else:
                    self.assertFalse(
                        send_to_docout,
                        "Invoice was expected NOT to be sent to the "
                        "doc-out, but it was not, with the "
                        "parameters: {0}".format(params_string))

    @skipIf(UNDER_DEVELOPMENT, UNDER_DEVELOPMENT_TEXT)
    def test_invoice_policy_delivery_diff_addr_no_epaid_amount_positive(self):
        """ If inv.policy=delivery, !=address, ¬epaid, amount >0, then doc-out.
        """
        cr, uid, ctx = self.cr, self.uid, self.context
        conf_obj = self.registry('configuration.data')
        order_obj = self.registry('sale.order')
        invoice_obj = self.registry('account.invoice')

        conf_id = self.ref('pc_config.default_configuration_data')

        for show_bvr_in_report in (True, False):
            conf_obj.write(
                cr, uid, conf_id,
                {'invoice_report_show_bvr_when_zero_amount_total':
                    show_bvr_in_report}, context=ctx)

            params_string = \
                "show_bvr_in_report={0}".format(show_bvr_in_report)
            print "Testing with {0}".format(params_string)

            order_id = self._create_sale_order(
                picking_policy='direct',  # Fixed parameter.
                invoice_policy='delivery',  # Fixed parameter.
                addresses_equal=False,  # Fixed parameter.
                epaid=False,  # Fixed parameter.
                positive_amount=True)  # Fixed parameter.
            self._validate_sale_order(order_id)
            self._invoice_full_sale_order(order_id)
            self._validate_invoices(order_id)

            order = order_obj.browse(
                cr, uid, order_id, context=ctx)

            self.assertEqual(
                len(order.invoice_ids), 1,
                "The sale.order was expected to have "
                "one invoice, and it "
                "has {0}".format(len(order.invoice_ids)))

            send_to_docout = \
                invoice_obj.check_send_invoice_to_docout(
                    cr, uid, order.invoice_ids[0].id,
                    context=ctx)

            self.assertTrue(
                send_to_docout,
                "Invoice was expected to be sent to the "
                "doc-out, but it was not, with the "
                "parameters: {0}".format(params_string))

    @skipIf(UNDER_DEVELOPMENT, UNDER_DEVELOPMENT_TEXT)
    def test_invoice_policy_delivery_diff_addr_no_epaid_amount_negative(self):
        """ If inv.policy=delivery, !=address, ¬epaid, amount <=0, then maybe
            we send it by doc-out, depends on if we want to show the BVR
            even if the quantity is zero: if we want, we send it, otherwise no.
        """
        cr, uid, ctx = self.cr, self.uid, self.context
        conf_obj = self.registry('configuration.data')
        order_obj = self.registry('sale.order')
        invoice_obj = self.registry('account.invoice')

        conf_id = self.ref('pc_config.default_configuration_data')

        for show_bvr_in_report in (True, False):
            conf_obj.write(
                cr, uid, conf_id,
                {'invoice_report_show_bvr_when_zero_amount_total':
                    show_bvr_in_report}, context=ctx)

            params_string = \
                "show_bvr_in_report={0}".format(show_bvr_in_report)
            print "Testing with {0}".format(params_string)

            order_id = self._create_sale_order(
                picking_policy='direct',  # Fixed parameter.
                invoice_policy='delivery',  # Fixed parameter.
                addresses_equal=False,  # Fixed parameter.
                epaid=False,  # Fixed parameter.
                positive_amount=False)  # Fixed parameter.
            self._validate_sale_order(order_id)
            self._invoice_full_sale_order(order_id)
            self._validate_invoices(order_id)

            order = order_obj.browse(
                cr, uid, order_id, context=ctx)

            self.assertEqual(
                len(order.invoice_ids), 1,
                "The sale.order was expected to have "
                "one invoice, and it "
                "has {0}".format(len(order.invoice_ids)))

            send_to_docout = \
                invoice_obj.check_send_invoice_to_docout(
                    cr, uid, order.invoice_ids[0].id,
                    context=ctx)

            if show_bvr_in_report:
                self.assertTrue(
                    send_to_docout,
                    "Invoice was expected to be sent to the "
                    "doc-out, but it was not, with the "
                    "parameters: {0}".format(params_string))
            else:
                self.assertFalse(
                    send_to_docout,
                    "Invoice was expected NOT to be sent to the "
                    "doc-out, but it was not, with the "
                    "parameters: {0}".format(params_string))
