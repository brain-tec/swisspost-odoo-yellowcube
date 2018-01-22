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

# Imports for the anybox to change the time.
# (see https://pypi.python.org/pypi/anybox.testing.datetime)
import anybox.testing.datetime
from datetime import datetime, timedelta
import time

from unittest2 import skipIf
from openerp.osv import fields
from openerp.tests import common
from openerp.addons.pc_account_invoice_automation.\
    tests.common import CommonTestFunctionalityAIA
from openerp.addons.pc_connect_master.tests.common import \
    CommonTestFunctionality
from common import CommonTestFunctionalityFollowupPF


UNDER_DEVELOPMENT = False
UNDER_DEVELOPMENT_TEXT = "Test was skipped because of being under development."


class TestAccountInvoiceAutomation(common.TransactionCase,
                                   CommonTestFunctionalityAIA,
                                   CommonTestFunctionalityFollowupPF,
                                   CommonTestFunctionality):

    def setUp(self):
        super(TestAccountInvoiceAutomation, self).setUp()
        self.context = {}

        cr, uid, ctx = self.cr, self.uid, self.context

        followup_level_obj = self.registry('followup.level')
        partner_bank_obj = self.registry('res.partner.bank')

        # Defines the penalisation products for the follow-up levels.
        self.penalisation_id_1 = self.create_product(self, {
            'name': 'Penalisation LEVEL 1',
            'type': 'service',
            'sale_delay': 0,
            'list_price': 10,
        })
        self.penalisation_id_2 = self.create_product(self, {
            'name': 'Penalisation LEVEL 2',
            'type': 'service',
            'sale_delay': 0,
            'list_price': 20,
        })
        self.penalisation_id_3 = self.create_product(self, {
            'name': 'Penalisation LEVEL 3',
            'type': 'service',
            'sale_delay': 0,
            'list_price': 30,
        })
        penalisation_ids = [
            self.penalisation_id_1,
            self.penalisation_id_2,
            self.penalisation_id_3,
        ]

        # Configures the follow-up levels with the 'default' values for tests.
        self.level_1_id = self.ref('bt_followup.demo_followup_line1')
        self.level_2_id = self.ref('bt_followup.demo_followup_line2')
        self.level_3_id = self.ref('bt_followup.demo_followup_line3')
        level_ids = [self.level_1_id, self.level_2_id, self.level_3_id]
        for num_level in xrange(len(level_ids)):
            followup_level_obj.write(
                cr, uid, level_ids[num_level], {
                    'delay': (num_level + 1) * 10,
                    'manual_action': False,
                    'block_new_invoice': False,
                    'send_email': False,
                    'send_letter': True,
                    'invoice_routing': 'force_docout',
                    'report_account_invoice': self.ref(
                        'pc_followup_pf.report_followup_pf'),
                    'product_id': penalisation_ids[num_level],
                }, context=ctx)

        # Creates and sets a bank-account on the company. This is needed
        # for follow-ups to run.
        self.partner_bank_id = partner_bank_obj.create(
            cr, uid, {
                'state': 'bank',
                'acc_number': 123,
                'partner_id': self.ref('base.main_partner'),
                'bank': self.ref('base.res_bank_1'),
                'bank_name': 'Test Bank for Follow-ups',
                'company_id': self.ref('base.main_company'),
            }, context=ctx)

    def tearDown(self):
        super(TestAccountInvoiceAutomation, self).tearDown()

    def create_and_open_invoice_due_today(self):
        """ Creates an invoice that dues today, and validates it.
        """
        inv_id = self.create_invoice(self, {'date_due': fields.date.today()})
        self.create_invoice_line(self, inv_id)
        self.validate_invoice(self, inv_id)
        return inv_id

    def pay_with_bank_statement(self, cr, uid, inv_id, amount, context=None):
        """ Pays the invoice, but with a bank statement.
        """
        cr, uid, ctx = self.cr, self.uid, self.context
        bank_stat_obj = self.registry('account.bank.statement')
        bank_stat_line_obj = self.registry('account.bank.statement.line')
        bank_stat_aux_wizard_obj = self.registry(
            'account.statement.from.invoice.lines')
        inv_obj = self.registry('account.invoice')
        journal_obj = self.registry('account.journal')
        acc_move_line_obj = self.registry('account.move.line')

        inv = inv_obj.browse(cr, uid, inv_id, context=ctx)

        # Gets the journal for the bank. It has no XML-ID and we need its ID
        # because calling the on-change over the journal sets the balance_start
        # that we need to validate the bank statement.
        bank_journal_id = journal_obj.search(cr, uid, [
            ('name', '=', 'Bank'),
        ], limit=1, context=ctx)[0]

        create_vals = {
            'name': 'Bank Statement for invoice with id={0}, '
                    'amount={1}'.format(inv.id, amount),
            'journal_id': bank_journal_id,
        }

        # Sets the balance_end_real.
        vals = bank_stat_obj.onchange_journal_id(
            cr, uid, False, bank_journal_id, context=ctx)
        create_vals.update(vals['value'])
        create_vals['company_id'] = vals['value']['company_id'][0]
        balance_start = vals['value']['balance_start']
        create_vals.update({
            'balance_end_real': balance_start + inv.amount_total,
        })

        bank_stat_id = bank_stat_obj.create(cr, uid, create_vals, context=ctx)

        # Finds the account.move.lines from the invoice that we want to
        # add to the bank.statement. Adds it to it.
        acc_move_line_ids = acc_move_line_obj.search(cr, uid, [
            ('account_id.type', 'in', ['receivable', 'payable']),
            ('reconcile_id', '=', False),
            ('reconcile_partial_id', '=', False),
            ('state', '=', 'valid'),
            ('move_id', '=', inv.move_id.id),
        ], context=ctx)
        self.assertEqual(len(acc_move_line_ids), 1)
        bank_stat_aux_wizard_id = bank_stat_aux_wizard_obj.create(cr, uid, {
            'line_ids': [(6, False, acc_move_line_ids)],
        }, context=ctx)
        ctx['statement_id'] = bank_stat_id
        bank_stat_aux_wizard_obj.populate_statement(
            cr, uid, [bank_stat_aux_wizard_id], context=ctx)
        del ctx['statement_id']

        # Confirms the bank.statement so that the invoice is paid.
        bank_stat_obj.button_dummy(cr, uid, [bank_stat_id], context=ctx)
        bank_stat_obj.button_confirm_bank(cr, uid, [bank_stat_id], context=ctx)

        return bank_stat_id

    def check_and_return_penalisation_invoice_ids(self, inv_id, expected_num):
        """ Checks that the number of penalisation invoices associated to
            the given one is the number received. And returns a list with
            the ids of the penalisation invoices.
        """
        cr, uid, ctx = self.cr, self.uid, self.context
        invoice_obj = self.registry('account.invoice')

        inv = invoice_obj.browse(cr, uid, inv_id, context=ctx)
        pen_inv_ids = [pen_inv.id
                       for pen_inv in inv.followup_penalization_invoice_ids]
        self.assertEqual(len(pen_inv_ids), expected_num)

        return pen_inv_ids

    def allow_cancelling_entries_for_journal_of_invoice(self, inv_id):
        """ Makes the journal set on the invoice to be able to cancel entries.
        """
        cr, uid, ctx = self.cr, self.uid, self.context
        invoice_obj = self.registry('account.invoice')
        inv = invoice_obj.browse(cr, uid, inv_id, context=ctx)
        inv.journal_id.write({'update_posted': True})

    @skipIf(UNDER_DEVELOPMENT, UNDER_DEVELOPMENT_TEXT)
    def test_followup_level_set(self):
        """ Tests the setting of a follow-up level over an outdated invoice.
        """
        cr, uid, ctx = self.cr, self.uid, self.context

        invoice_obj = self.registry('account.invoice')

        # Creates an invoice, to be paid today, and validates it.
        inv_id = self.create_and_open_invoice_due_today()

        # Moves forward in time for the day *after* the invoice qualifies
        # for the 1st follow-up level.
        delay_1 = self.get_delay_followup_level(self, self.level_1_id)
        datetime.set_now(datetime.now() + timedelta(delay_1 + 1))

        inv = invoice_obj.browse(cr, uid, inv_id, context=ctx)
        self.assertEqual(inv.follow_up_date_due_days, delay_1 + 1)
        self.assertFalse(inv.followup_level_id)

        # Executes the schedulers which sets the follow-up levels.
        invoice_obj.cron_update_invoice_followup_level(cr, uid, context=ctx)

        inv = invoice_obj.browse(cr, uid, inv_id, context=ctx)
        self.assertEqual(inv.follow_up_date_due_days, delay_1)
        self.assertEqual(inv.followup_level_id.id, self.level_1_id)

        # Moves again to the real-now.
        datetime.real_now()

    @skipIf(UNDER_DEVELOPMENT, UNDER_DEVELOPMENT_TEXT)
    def test_followup_handled(self):
        """ Tests the handling of an invoice having a follow-up level
            which creates an extra invoice with the dunning fee.
        """
        cr, uid, ctx = self.cr, self.uid, self.context

        invoice_obj = self.registry('account.invoice')
        foll_level_obj = self.registry('followup.level')

        # Creates an invoice, to be paid today, and validates it.
        inv_id = self.create_and_open_invoice_due_today()

        # Moves forward in time for the day *after* the invoice qualifies
        # for the 1st follow-up level.
        delay_1 = self.get_delay_followup_level(self, self.level_1_id)
        datetime.set_now(datetime.now() + timedelta(delay_1 + 1 ))

        inv = invoice_obj.browse(cr, uid, inv_id, context=ctx)
        self.assertEqual(inv.follow_up_date_due_days, delay_1 + 1)
        self.assertFalse(inv.followup_level_id)

        # Executes the schedulers which sets the follow-up levels.
        invoice_obj.cron_update_invoice_followup_level(cr, uid, context=ctx)

        inv = invoice_obj.browse(cr, uid, inv_id, context=ctx)
        self.assertEqual(inv.follow_up_date_due_days, delay_1)
        self.assertEqual(inv.followup_level_id.id, self.level_1_id)

        # Handles the invoice.
        invoice_obj.do_handle_followup(cr, uid, inv_id, context=ctx)

        inv = invoice_obj.browse(cr, uid, inv_id, context=ctx)
        self.assertEqual(inv.follow_up_date_due_days, delay_1)
        self.assertEqual(inv.followup_level_id.id, self.level_1_id)
        self.assertEqual(inv.followup_level_date, fields.date.today())
        self.assertTrue(inv.followup_level_handled)
        self.check_and_return_penalisation_invoice_ids(inv_id, 1)

        fee_inv = inv.followup_penalization_invoice_ids[0]
        self.assertEqual(fee_inv.state, 'open')
        level_1 = foll_level_obj.browse(cr, uid, self.level_1_id, context=ctx)
        self.assertEqual(fee_inv.amount_total, level_1.product_id.list_price)

    @skipIf(UNDER_DEVELOPMENT, UNDER_DEVELOPMENT_TEXT)
    def test_pay_original_amount(self):
        """ The amount paid is only the amount of the invoice.
            - In this case, the invoice is reconciled and all the
              dunned invoices are refunded & reconciled.
        """
        cr, uid, ctx = self.cr, self.uid, self.context

        invoice_obj = self.registry('account.invoice')

        # Creates an invoice, to be paid today, and validates it.
        inv_id = self.create_and_open_invoice_due_today()
        self.allow_cancelling_entries_for_journal_of_invoice(inv_id)

        # Moves forward in time for the day *after* the invoice qualifies
        # for the 1st follow-up level.
        delay_1 = self.get_delay_followup_level(self, self.level_1_id)
        datetime.set_now(datetime.now() + timedelta(delay_1 + 1))

        # Sets the follow-up level and handles it.
        invoice_obj.cron_update_invoice_followup_level(cr, uid, context=ctx)
        invoice_obj.do_handle_followup(cr, uid, inv_id, context=ctx)

        # This follow-up level has created a penalisation invoice.
        pen_inv_ids = self.check_and_return_penalisation_invoice_ids(inv_id, 1)
        pen_inv = invoice_obj.browse(cr, uid, pen_inv_ids[0], context=ctx)

        # The user pays:
        # - just the amount of the original invoice.
        inv = invoice_obj.browse(cr, uid, inv_id, context=ctx)
        self.pay_with_bank_statement(
            cr, uid, inv_id, inv.amount_total, context=ctx)

        # - in this case, the original invoice is paid and reconciled;
        #                 the dunned invoice is cancelled.
        inv = invoice_obj.browse(cr, uid, inv_id, context=ctx)
        self.assertEqual(inv.state, 'paid')
        self.assertTrue(inv.reconciled)
        pen_inv = invoice_obj.browse(cr, uid, pen_inv_ids[0], context=ctx)
        self.assertEqual(pen_inv.state, 'cancel')
        self.assertFalse(pen_inv.reconciled)

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
