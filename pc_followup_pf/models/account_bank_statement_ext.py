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

from openerp.osv import fields, osv
from openerp.tools.translate import _


class account_bank_statement_ext(osv.osv):
    _inherit = 'account.bank.statement'

    def button_confirm_bank(self, cr, uid, ids, context=None):
        """ Overridden to deal with the algorithm of paying invoice which
            are under a follow-up process, which is as follows:
            - If the amount paid for invoice is its amount, then the invoice
              is paid & reconciled (this is done automatically) and the invoice
              with the fee is cancelled (this has to be done in the code).
            - If the amount paid for invoice is its amount plus all its fees,
              then all the invoices (original and penalisations) are paid &
              reconciled (this is done automatically).
            - Otherwise, log an issue informing about it, so that a manual
              intervention can be done if needed.
        """
        if not isinstance(ids, list):
            ids = [ids]
        if context is None:
            context = {}

        inv_obj = self.pool.get('account.invoice')
        voucher_line_obj = self.pool.get('account.voucher.line')
        project_issue_obj = self.pool.get('project.issue')

        # We do everything that has to be done, and the we'll do our work
        # afterwards.
        ret = super(account_bank_statement_ext, self).button_confirm_bank(
            cr, uid, ids, context=context)

        # Gets all the voucher's lines that we have.
        inv_voucher_line_ids = []
        for statement in self.browse(cr, uid, ids, context=context):
            voucher_ids = [
                line.voucher_id.id
                for line in statement.line_ids if line.voucher_id]
            inv_voucher_line_ids.extend(voucher_line_obj.search(cr, uid, [
                ('voucher_id', 'in', voucher_ids),
                ('type', '=', 'cr'),
                ('amount', '>=', 0.0),
            ], context=context))

        # Gets the invoices associated to each of those voucher's lines,
        # that will be paid because of the call to the super()'s own method.
        # We are going to assume an invoice appears in just ONE voucher's line.
        inv_voucher_line_dict = {}
        for voucher_line in voucher_line_obj.browse(
                cr, uid, inv_voucher_line_ids, context=context):
            inv_ids = inv_obj.search(cr, uid, [
                ('move_id.name', '=', voucher_line.name),
                ('move_id.line_id', 'in', voucher_line.move_line_id.id),
            ], limit=1, context=context)
            if inv_ids:
                inv_voucher_line_dict.setdefault(inv_ids[0], []).append(
                    voucher_line.id)

        # If issues have to be created, this dictionary stores the messages
        # to create for each invoice.
        issue_per_invoice = {}

        # Store sthe invoices that have already been processed, either directly
        # or indirectly (e.g. because of being a penalisation invoice being
        # associated to any of the invoices that we have).
        processed_inv_ids = set()
        for inv_id, inv_voucher_line_ids in inv_voucher_line_dict.iteritems():
            inv = inv_obj.browse(cr, uid, inv_id, context=context)

            # If we have marked the invoice to be processed, or the invoice
            # is a penalisation invoice, then we skip it.
            if inv_id in processed_inv_ids or inv.followup_parent_id:
                continue

            # If the invoice is under a follow-up level that has been handled,
            # then we see if their penalisation invoices have been paid or not,
            # but only in the case the invoice have been paid completely,
            # (otherwise we log an issue).
            if inv.followup_level_id and inv.followup_level_handled:

                total_paid_for_inv = voucher_line_obj.get_amount(
                    cr, uid, inv_voucher_line_ids, context=context)

                # If the voucher lines have paid the total amount of the
                # remaining amount to be paid for the invoice, then we
                # search if it had penalisation invoices associated to
                # them, and if they were in the same bank statement that
                # we are processing.
                if total_paid_for_inv == inv.amount_total and not inv.residual:

                    # Total amount to pay because of penalisation invoices.
                    pen_inv_to_pay = 0.0

                    # The amount paid corresponding to penalisation invoices.
                    pen_inv_paid = 0.0

                    for pen_inv in inv.followup_penalization_invoice_ids:
                        pen_inv_to_pay += pen_inv.amount_total

                        if pen_inv.id in inv_voucher_line_dict:
                            pen_inv_voucher_line_ids = \
                                inv_voucher_line_dict[pen_inv.id]
                            pen_inv_paid += voucher_line_obj.get_amount(
                                cr, uid, pen_inv_voucher_line_ids,
                                context=context)

                            # The penalisation invoice was already processed.
                            processed_inv_ids.add(pen_inv.id)

                    if pen_inv_paid == pen_inv_to_pay:
                        # If the amounts are equal, then the penalisation
                        # invoices will be set as 'paid' by the super()
                        # implementation, which is the default behaviour,
                        # so nothing has to be done.
                        pass  # Do nothing in this case.

                    elif pen_inv_paid == 0.0 and pen_inv_to_pay != 0:
                        # If a penalisation had to be paid, but it wasn't,
                        # then the penalisation invoices are cancelled.
                        for pen_inv in inv.followup_penalization_invoice_ids:
                            pen_inv.action_cancel()
                            pen_inv.message_post(
                                _('Was set to cancel because of any of the '
                                  'bank statements with IDs={0}').format(
                                    ','.join(map(str, ids))))

                    elif pen_inv_paid < pen_inv_to_pay:
                        # This happens when the amount paid is more than
                        # the amount for the invoice, but is lower than the
                        # total amount summing the amount of the invoice and
                        # the amounts of all its penalisation invoices.
                        for pen_inv in inv.followup_penalization_invoice_ids:
                            issue_per_invoice.setdefault(pen_inv, []).append(
                                _('The amount paid for the invoice with '
                                  'ID={0} is more than the amount for the '
                                  'invoice, but is lower than the total '
                                  'amount summing the amount of the invoice '
                                  'and the amounts of all its penalisation '
                                  'invoices.').format(pen_inv.id))

                    else:  # if pen_inv_paid > pen_inv_to_pay:
                        # This happens when the amount paid is more than
                        # the sum of the amount of the invoice and the total
                        # amount of all the penalisation invoices.
                        for pen_inv in inv.followup_penalization_invoice_ids:
                            issue_per_invoice.setdefault(pen_inv, []).append(
                                _('The amount paid for the invoice with '
                                  'ID={0} is more than the sum of the amount '
                                  'of the invoice and the total amounts of '
                                  'all the penalisation invoices.').format(
                                    pen_inv))

                else:
                    # The invoice having the follow-up was not paid completely.
                    issue_per_invoice.setdefault(inv_id, []).append(
                        _('The invoice with ID={0}, which is under a '
                          'follow-up process, was not paid completely').format(
                            inv_id))

                issue_per_invoice.setdefault(inv_id, []).append(
                    _('TEST id={0}').format(inv_id))

            # This invoice was already processed.
            processed_inv_ids.add(inv_id)

            # Logs any issues that have to be logged.
            for inv_id, issue_texts in issue_per_invoice.iteritems():
                for issue_text in issue_texts:
                    project_issue_obj.create_issue(cr, uid, 'account.invoice',
                                                   inv_id, issue_text,
                                                   context=context)

        return ret

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
