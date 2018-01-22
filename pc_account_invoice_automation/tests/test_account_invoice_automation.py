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
from openerp.osv import fields
from openerp.tests import common
from common import CommonTestFunctionalityAIA
from openerp.addons.pc_account_invoice_automation.\
    AccountInvoiceAutomationResult import AccountInvoiceAutomationResult
from openerp.addons.pc_connect_master.tests.common import \
    CommonTestFunctionality


UNDER_DEVELOPMENT = False
UNDER_DEVELOPMENT_TEXT = "Test was skipped because of being under development."


class TestAccountInvoiceAutomation(common.TransactionCase,
                                   CommonTestFunctionalityAIA,
                                   CommonTestFunctionality):

    def setUp(self):
        super(TestAccountInvoiceAutomation, self).setUp()
        self.context = {}

        # Sets a report in the configuration to be used when printing.
        invoice_report_id = self.ref('pc_account_pf.report_invoice')
        self.set_config(self, 'aia_report_account_invoice', invoice_report_id)

        # Sets an email template to be used if the routing is 'email'.
        email_template_id = self.ref('pc_account_invoice_automation.'
                                     'email_template_invoice_routing_email')
        self.set_config(self, 'aia_route_email_template_id', email_template_id)

        # Gets the payment methods we are going to need: paid and not epaid.
        self.payment_method_epaid_id = self.ref(
            'pc_connect_master.payment_method_epaid')
        self.payment_method_not_epaid_id = self.ref(
            'pc_connect_master.payment_method_not_epaid')

        # # Configures the doc-out.
        # for day in ['mon', 'tues', 'wednes', 'thurs', 'fri', 'satur', 'sun']:
        #     self.set_config(self, 'docout_aia_{0}day'.format(day), True)
        # self.set_config(self, 'docout_aia_activate_send_to_email', True)
        # self.set_config(self, 'docout_aia_activate_send_to_server', True)

    def tearDown(self):
        super(TestAccountInvoiceAutomation, self).tearDown()

    def __create_valid_invoice(self, defaults=None):
        """ Returns the ID of a valid invoice to be automated in the
            Account.Invoice Automation.
        """
        create_vals = {
            'automate_invoice_process': True,
            'payment_method_id': self.payment_method_epaid_id,
            'invoice_routing': 'email',
        }
        if defaults:
            create_vals.update(defaults)
        inv_id = self.create_invoice(self, create_vals)
        self.create_invoice_line(self, inv_id)
        return inv_id

    @skipIf(UNDER_DEVELOPMENT, UNDER_DEVELOPMENT_TEXT)
    def test_create_invoice_automated(self):
        """ Creates an invoice which is automated.
        """
        cr, uid, ctx = self.cr, self.uid, self.context
        inv_obj = self.registry('account.invoice')
        job_obj = self.registry('queue.job')

        inv_id = self.create_invoice(self, {'automate_invoice_process': True})
        self.create_invoice_line(self, inv_id)

        inv = inv_obj.browse(cr, uid, inv_id, context=ctx)
        self.assertTrue(inv.automate_invoice_process)
        self.assertTrue(inv.automate_invoice_process_fired)

        target_func_string = '%job_automate_account_invoice%, {0}L,%'.format(inv_id)
        job_ids = job_obj.search(cr, uid, [
            ('func_string', 'like', target_func_string),
        ], context=ctx)
        self.assertEqual(len(job_ids), 1)

    @skipIf(UNDER_DEVELOPMENT, UNDER_DEVELOPMENT_TEXT)
    def test_create_invoice_not_automated(self):
        """ Creates an invoice which is not automated.
        """
        cr, uid, ctx = self.cr, self.uid, self.context
        inv_obj = self.registry('account.invoice')
        job_obj = self.registry('queue.job')

        inv_id = self.create_invoice(self, {'automate_invoice_process': False})
        self.create_invoice_line(self, inv_id)

        inv = inv_obj.browse(cr, uid, inv_id, context=ctx)
        self.assertFalse(inv.automate_invoice_process)
        self.assertFalse(inv.automate_invoice_process_fired)

        target_func_string = '%job_automate_account_invoice%, {0}L,%'.format(inv_id)
        job_ids = job_obj.search(cr, uid, [
            ('func_string', 'like', target_func_string),
        ], context=ctx)
        self.assertEqual(len(job_ids), 0)

    @skipIf(UNDER_DEVELOPMENT, UNDER_DEVELOPMENT_TEXT)
    def test_aia_check_invoice_success(self):
        """ Tests the check of an invoice with all the required data for the AIA.
        """
        cr, uid, ctx = self.cr, self.uid, self.context
        inv_obj = self.registry('account.invoice')

        inv_id = self.__create_valid_invoice()

        aia_info = AccountInvoiceAutomationResult()
        inv_obj.aia_check_invoice(cr, uid, inv_id, aia_info, context=ctx)
        self.assertFalse(aia_info.error)
        self.assertFalse(aia_info.message)

    @skipIf(UNDER_DEVELOPMENT, UNDER_DEVELOPMENT_TEXT)
    def test_aia_check_invoice_failure(self):
        """ Tests that an invoice with missing required data must not advance in the AIA.
        """
        cr, uid, ctx = self.cr, self.uid, self.context
        inv_obj = self.registry('account.invoice')

        inv_id = self.create_invoice(self, {
            'automate_invoice_process': True,
            'payment_method_id': False,
            'invoice_routing': False,
        })
        self.create_invoice_line(self, inv_id)

        aia_info = AccountInvoiceAutomationResult()
        inv_obj.aia_check_invoice(cr, uid, inv_id, aia_info, context=ctx)
        self.assertTrue(aia_info.error)
        self.assertTrue('No payment method was set.' in aia_info.message)
        self.assertTrue('No invoice routing was set.' in aia_info.message)

    @skipIf(UNDER_DEVELOPMENT, UNDER_DEVELOPMENT_TEXT)
    def test_aia_check_invoice_failure_no_payment_term_routing_default(self):
        """ Tests that an invoice with missing required data must not advance in the AIA,
            and in particular if the payment method lacks a payment term AND
            if the routing is set to 'default', which is useless here.
        """
        cr, uid, ctx = self.cr, self.uid, self.context
        inv_obj = self.registry('account.invoice')

        payment_method_obj = self.registry('payment.method')

        payment_method_epaid_id = self.ref(
            'pc_connect_master.payment_method_epaid')
        payment_method_obj.write(cr, uid, payment_method_epaid_id, {
            'payment_term_id': False,
        }, context=ctx)
        inv_id = self.create_invoice(self, {
            'automate_invoice_process': True,
            'payment_method_id': payment_method_epaid_id,
            'invoice_routing': 'default',
        })

        aia_info = AccountInvoiceAutomationResult()
        inv_obj.aia_check_invoice(cr, uid, inv_id, aia_info, context=ctx)
        self.assertTrue(aia_info.error)
        self.assertTrue('No payment term was set on the payment method.' in aia_info.message)
        self.assertTrue("Routing 'default' is useless" in aia_info.message)

    @skipIf(UNDER_DEVELOPMENT, UNDER_DEVELOPMENT_TEXT)
    def test_aia_prepare_invoice(self):
        """ Tests that the invoice, once checked, is correctly prepared.
        """
        cr, uid, ctx = self.cr, self.uid, self.context
        inv_obj = self.registry('account.invoice')
        payment_method_obj = self.registry('payment.method')

        inv_id = self.__create_valid_invoice({
            'reference_type': 'bvr',
            'reference': False,
        })
        payment_method_epaid_id = self.ref(
            'pc_connect_master.payment_method_epaid')

        # Checks that, before, the invoice didn't have a payment term.
        inv = inv_obj.browse(cr, uid, inv_id, context=ctx)
        payment_method = payment_method_obj.browse(
            cr, uid, payment_method_epaid_id, context=ctx)
        self.assertFalse(inv.payment_term)

        aia_info = AccountInvoiceAutomationResult()
        inv_obj.aia_prepare_invoice(cr, uid, inv_id, aia_info, context=ctx)

        # Checks that, after, the invoice does have a payment term.
        inv = inv_obj.browse(cr, uid, inv_id, context=ctx)
        self.assertEqual(inv.payment_term.id, payment_method.payment_term_id.id)

        # Checks that, after, the invoice has a reference type set to
        # 'Free Reference', i.e. to value 'none', because we set the
        # 'reference' to have no value.
        self.assertEqual(inv.reference_type, 'none')
        self.assertFalse(inv.reference)

    @skipIf(UNDER_DEVELOPMENT, UNDER_DEVELOPMENT_TEXT)
    def test_aia_validate_invoice(self):
        """ Checks that an invoice, once checked and prepared, is validated.
        """
        cr, uid, ctx = self.cr, self.uid, self.context
        inv_obj = self.registry('account.invoice')

        inv_id = self.__create_valid_invoice()

        # The pre-conditions.
        inv = inv_obj.browse(cr, uid, inv_id, context=ctx)
        self.assertEqual(inv.state, 'draft')

        aia_info = AccountInvoiceAutomationResult()
        inv_obj.aia_validate_invoice(cr, uid, inv_id, aia_info, context=ctx)

        # The post-conditions.
        inv = inv_obj.browse(cr, uid, inv_id, context=ctx)
        self.assertEqual(inv.state, 'open')

    @skipIf(UNDER_DEVELOPMENT, UNDER_DEVELOPMENT_TEXT)
    def test_aia_print_invoice(self):
        cr, uid, ctx = self.cr, self.uid, self.context
        inv_obj = self.registry('account.invoice')
        attachment_obj = self.registry('ir.attachment')

        inv_id = self.__create_valid_invoice()

        # Checks that the invoice had no attachments.
        attach_ids = attachment_obj.search(cr, uid, [
            ('res_model', '=', 'account.invoice'),
            ('res_id', '=', inv_id),
        ], context=ctx)
        self.assertEqual(len(attach_ids), 0)

        aia_info = AccountInvoiceAutomationResult()
        inv_obj.aia_print_invoice(cr, uid, inv_id, aia_info, context=None)

        # Checks than an attachment was generated.
        attach_ids = attachment_obj.search(cr, uid, [
            ('res_model', '=', 'account.invoice'),
            ('res_id', '=', inv_id),
        ], context=ctx)
        self.assertEqual(len(attach_ids), 1)

        attach = attachment_obj.browse(cr, uid, attach_ids[0], context=ctx)
        expected_invoice_attach_name = 'invoice_aia_inv{0}.pdf'.format(inv_id)
        self.assertEqual(attach.name, expected_invoice_attach_name)
        self.assertEqual(len(attach.tags_ids), 1)
        self.assertEqual(attach.tags_ids[0].name, 'invoice')
        self.assertFalse(aia_info.error)
        self.assertFalse(aia_info.message)

    @skipIf(UNDER_DEVELOPMENT, UNDER_DEVELOPMENT_TEXT)
    def test_aia_send_invoice_email(self):
        """ Tests the sending of an invoice by email.
        """
        cr, uid, ctx = self.cr, self.uid, self.context
        inv_obj = self.registry('account.invoice')
        mail_obj = self.registry('mail.mail')
        message_obj = self.registry('mail.message')

        inv_id = self.__create_valid_invoice({'invoice_routing': 'email'})

        # Generates the attachment (to have something to send).
        aia_info = AccountInvoiceAutomationResult()
        attach_ids = inv_obj.aia_print_invoice(
            cr, uid, inv_id, aia_info, context=None)
        self.assertFalse(aia_info.error)
        self.assertFalse(aia_info.message)
        self.assertEqual(len(attach_ids), 1)

        # Sends the invoice with the option 'email'.
        inv_obj.aia_send_invoice(cr, uid, inv_id, aia_info, context=ctx)

        # Checks that no errors appeared and that an email is prepared.
        self.assertFalse(aia_info.error)
        self.assertFalse(aia_info.message)
        inv = inv_obj.browse(cr, uid, inv_id, context=ctx)
        message_ids = message_obj.search(cr, uid, [
            ('model', '=', 'account.invoice'),
            ('res_id', '=', inv_id),
            ('subject', '=', 'Invoice Sending Account.Invoice Automation'),
            ('attachment_ids', 'in', attach_ids[0]),
        ], context=ctx)
        self.assertEqual(len(message_ids), 1)
        mail_ids = mail_obj.search(cr, uid, [
            ('email_to', '=', inv.partner_id.email),
            ('mail_message_id', '=', message_ids[0])
        ], context=ctx)
        self.assertEqual(len(mail_ids), 1)

    @skipIf(UNDER_DEVELOPMENT, UNDER_DEVELOPMENT_TEXT)
    def test_aia_send_invoice_docout(self):
        cr, uid, ctx = self.cr, self.uid, self.context
        inv_obj = self.registry('account.invoice')
        attach_obj = self.registry('ir.attachment')

        # Only not-epaid invoices are sent to the doc-out, and also
        # they must have a partner_bank_id of state 'bvr', and also
        # must be in state open (or paid and with amount == 0).
        bvr_partner_bank_id = self.ref('pc_docout.bvr_res_partner_bank')
        inv_id = self.__create_valid_invoice({
            'invoice_routing': 'docout',
            'payment_method_id': self.payment_method_not_epaid_id,
            'partner_bank_id': bvr_partner_bank_id,
        })

        aia_info = AccountInvoiceAutomationResult()
        inv_obj.aia_validate_invoice(cr, uid, inv_id, aia_info, context=ctx)

        # Generates the attachment (to have something to send).
        aia_info = AccountInvoiceAutomationResult()
        attach_ids = inv_obj.aia_print_invoice(
            cr, uid, inv_id, aia_info, context=None)
        self.assertFalse(aia_info.error)
        self.assertFalse(aia_info.message)
        self.assertEqual(len(attach_ids), 1)

        # Sends the invoice with the option 'docout'.
        inv_obj.aia_send_invoice(cr, uid, inv_id, aia_info, context=ctx)

        # Checks that no errors appeared and that it was ready for the docout.
        self.assertFalse(aia_info.error)
        self.assertFalse(aia_info.message)
        attach = attach_obj.browse(cr, uid, attach_ids[0], context=ctx)
        self.assertEqual(attach.docout_state_email, 'to_send')
        self.assertEqual(attach.docout_state_remote_folder, 'to_send')
        self.assertEqual(attach.docout_file_type, 'invoice')

    @skipIf(UNDER_DEVELOPMENT, UNDER_DEVELOPMENT_TEXT)
    def test_aia_send_invoice_default(self):
        cr, uid, ctx = self.cr, self.uid, self.context
        inv_obj = self.registry('account.invoice')

        inv_id = self.__create_valid_invoice({'invoice_routing': 'default'})

        # Generates the attachment (to have something to send).
        aia_info = AccountInvoiceAutomationResult()
        attach_ids = inv_obj.aia_print_invoice(
            cr, uid, inv_id, aia_info, context=None)
        self.assertFalse(aia_info.error)
        self.assertFalse(aia_info.message)
        self.assertEqual(len(attach_ids), 1)

        # Sends the invoice with the option 'default'.
        inv_obj.aia_send_invoice(cr, uid, inv_id, aia_info, context=ctx)
        self.assertTrue(aia_info.error)
        self.assertEqual("The 'default' routing is not intended for the "
                         "Account.Invoice Automation.", aia_info.message)

    @skipIf(UNDER_DEVELOPMENT, UNDER_DEVELOPMENT_TEXT)
    def test_aia_send_invoice_pfgateway(self):
        cr, uid, ctx = self.cr, self.uid, self.context
        inv_obj = self.registry('account.invoice')

        inv_id = self.__create_valid_invoice({'invoice_routing': 'pfgateway'})

        # Generates the attachment (to have something to send).
        aia_info = AccountInvoiceAutomationResult()
        attach_ids = inv_obj.aia_print_invoice(
            cr, uid, inv_id, aia_info, context=None)
        self.assertFalse(aia_info.error)
        self.assertFalse(aia_info.message)
        self.assertEqual(len(attach_ids), 1)

        # Sends the invoice with the option 'pfgateway'.
        inv_obj.aia_send_invoice(cr, uid, inv_id, aia_info, context=ctx)
        self.assertTrue(aia_info.error)
        self.assertEqual("Routing 'pfgateway' is not yet implemented.",
                         aia_info.message)

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
