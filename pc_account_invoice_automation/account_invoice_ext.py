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

from openerp.osv import osv, fields, orm
from openerp.tools.translate import _
from openerp.addons.connector.session import ConnectorSession
from openerp.addons.connector.queue.job import job
from openerp.addons.pc_connect_master.utilities.others import \
    format_exception
from openerp.addons.pc_connect_master.utilities.reports import \
    get_pdf_from_report, associate_ir_attachment_with_object
from AccountInvoiceAutomationResult import AccountInvoiceAutomationResult

import netsvc
import logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


@job
def job_automate_account_invoice(session, model_name, record_id, state):
    """ Account.Invoice Automation Job.
    """
    cr, uid, ctx = session.cr, session.uid, session.context.copy()
    invoice_obj = session.pool.get('account.invoice')

    automation_result = session.pool.get(model_name).automate_account_invoice(
        cr, uid, record_id, state, ctx)

    if automation_result.error:
        raise Warning(_('ERROR in AIA: {0}').format(automation_result.message))

    if not automation_result.next_state:
        message = _('Finished automated process for {0} with ID={1}').format(
            model_name, record_id)
    else:
        prio = invoice_obj.get_priority(cr, uid, record_id, context=ctx)
        next_state = automation_result.next_state

        job_automate_account_invoice.delay(
            session, model_name, record_id, next_state, priority=prio)

        message = _('Moving to state: {0}').format(next_state)
        if type(automation_result.message) is str:
            message = '{0}\n\n{1}'.format(automation_result.message, message)

    logger.debug("Account.Invoice Automation ID={0}: {1}".format(
        record_id, message.replace('\n', '\\n')))

    return message


class account_invoice_ext(osv.Model):
    _inherit = 'account.invoice'

    def write(self, cr, uid, ids, values, context=None):
        ret = super(account_invoice_ext, self).write(
            cr, uid, ids, values, context=context)

        # Checks if we have modified the flag to automate the invoice.
        automate = values.get('automate_invoice_process', False)
        if automate:
            self.enable_automation(cr, uid, ids, context=context)

        return ret

    def create(self, cr, uid, values, context=None):
        invoice_id = super(account_invoice_ext, self).create(
            cr, uid, values, context=context)

        # Checks if we have modified the flag to automate the invoice.
        automate = values.get('automate_invoice_process', False)
        if automate:
            self.enable_automation(cr, uid, invoice_id, context=context)

        return invoice_id

    def copy(self, cr, uid, ids, default=None, context=None):
        if default is None:
            default = {}
        default.update({
            'automate_invoice_process': False,
            'automate_invoice_process_fired': False,
        })
        return super(account_invoice_ext, self).copy(
            cr, uid, ids, default, context=context)

    def get_priority(self, cr, uid, ids, context=None):
        """ Returns the priority of the invoice for the Account.Invoice
            Automation. For the moment it's just the ID, for a FIFO automation.
        """
        if not isinstance(ids, list):
            ids = [ids]
        assert len(ids) == 1, "ids must be a 1-element list."
        return ids[0]

    def enable_automation(self, cr, uid, ids, context=None):
        """ Creates the job to initiate the account.invoice automation,
            but only if the automation was not fired before.
        """
        if context is None:
            context = {}
        if not isinstance(ids, list):
            ids = [ids]

        session = ConnectorSession(cr, uid)
        for invoice in self.browse(cr, uid, ids, context=context):
            if invoice.automate_invoice_process_fired:
                logger.info(_("Account.Invoice Automation was enabled on "
                              "invoice with ID={0}, but it had already been "
                              "enabled in the past.").format(invoice.id))
            else:
                self.write(cr, uid, invoice.id, {
                    'automate_invoice_process_fired': True,
                })
                job_automate_account_invoice.delay(
                    session, 'account.invoice', invoice.id,
                    'aia_validate_and_print_invoice',
                    priority=invoice.get_priority())

        return True

    def automate_account_invoice(self, cr, uid, ids, aia_state, context=None):
        """ Automates an invoice through the Account.Invoice Automation.
        """
        if context is None:
            context = {}
        if not isinstance(ids, list):
            ids = [ids]

        assert len(ids) == 1, "ids must be a 1-element list."

        invoice = self.browse(cr, uid, ids[0], context=context)

        aia_info = AccountInvoiceAutomationResult()
        logger.debug(_("Automating invoice with ID={0}.").format(invoice.id))

        try:
            if invoice.state == 'cancel':
                pass

            elif aia_state == 'aia_validate_and_print_invoice':
                invoice.aia_check_invoice(aia_info)
                if not aia_info.error:
                    invoice.aia_prepare_invoice(aia_info)
                if not aia_info.error:
                    invoice.aia_validate_invoice(aia_info)
                if not aia_info.error:
                    invoice.aia_print_invoice(aia_info)
                if not aia_info.error:
                    aia_info.next_state = 'aia_send_invoice'

            elif aia_state == 'aia_send_invoice':
                invoice.aia_send_invoice(aia_info)

                # End of the AIA: no more states & ending-flag set.
                aia_info.next_state = False
                invoice.write({'automation_finished': True}, context=context)

            else:
                raise Exception(
                    _("State '{0}' is not a valid state for the "
                      "Account.Invoice Automation").format(aia_state))

            # write_log()  # TODO.

        except Exception as e:
            exception_msg = \
                _("An error happened while automating the account.invoice "
                  "with ID={0}\n{1}").format(invoice.id, format_exception(e))
            aia_info.error = True
            aia_info.message = exception_msg
            logger.exception(exception_msg)

            # We inform.
            # write_log()  # TODO.

        return aia_info

    def aia_check_invoice(self, cr, uid, ids, aia_info, context=None):
        """ Checks that the invoice has set all the required parameters for
            the Account.Invoice Automation.
        """
        if context is None:
            context = {}
        if not isinstance(ids, list):
            ids = [ids]
        assert len(ids) == 1, "ids must be a 1-element list."

        inv = self.browse(cr, uid, ids[0], context=context)
        errors = []

        if inv.state != 'draft':
            errors.append("Invoice is not in state draft.")
        if not inv.payment_method_id:
            errors.append("No payment method was set.")
        if inv.payment_method_id and not inv.payment_method_id.payment_term_id:
            errors.append("No payment term was set on the payment method.")
        if not inv.invoice_routing:
            errors.append("No invoice routing was set.")
        if inv.invoice_routing == 'default':
            errors.append("Routing 'default' is useless in the Inv. Automation")

        if errors:
            aia_info.error = True
            aia_info.message = _("The following errors were found when "
                                 "automating invoice with ID={0}:\n"
                                 "{1}").format(inv.id, '\n'.join(errors))

        return True

    def aia_prepare_invoice(self, cr, uid, ids, aia_info, context=None):
        """ Prepares the 'inferred' parameters for the automation.
            Assumes all the required parameters are already set.
        """
        if context is None:
            context = {}
        if not isinstance(ids, list):
            ids = [ids]
        assert len(ids) == 1, "ids must be a 1-element list."

        inv = self.browse(cr, uid, ids[0], context=context)

        to_write = {}

        # Sets the payment term based on the payment method.
        payment_term_id = inv.payment_method_id.payment_term_id.id
        to_write.update({'payment_term': payment_term_id})

        # Sets the reference_type to be 'Free Reference' if there is no
        # reference number set.
        if not inv.reference:
            to_write.update({'reference_type': 'none'})

        if to_write:
            inv.write(to_write)

        return True

    def aia_validate_invoice(self, cr, uid, ids, aia_info, context=None):
        """ Validates the invoice.
        """
        if context is None:
            context = {}
        if not isinstance(ids, list):
            ids = [ids]
        assert len(ids) == 1, "ids must be a 1-element list."

        inv = self.browse(cr, uid, ids[0], context=context)

        if inv.state == 'draft':
            # Is the rounding to 5-cents active? If so, and requires rounding,
            # then we round.
            round_to_5_cents = bool(self.pool.get('ir.model.fields').search(
                cr, uid, [
                    ('model', '=', 'account.invoice'),
                    ('name', '=', 'round_inv_to_05'),
                ], count=True, limit=1, context=context))
            if round_to_5_cents and inv.requires_rounding():
                inv.change_rounding()

            # We update the invoice since stage_discount requires a 'manual'
            # update, and that module may be installed.
            inv.button_reset_taxes()

            # We validate the invoice so that it's opened.
            wf_service = netsvc.LocalService('workflow')
            wf_service.trg_validate(uid, 'account.invoice', inv.id,
                                    'invoice_open', cr)

        else:
            logger.info(_("Call to aia_validate_invoice did nothing because "
                          "the invoice with ID={0} was not in state "
                          "'draft'").format(inv.id))

        return True

    def aia_print_invoice(self, cr, uid, ids, aia_info, context=None):
        """ Prints the invoice with the provided mako-template set in the
            configuration.
        """
        if context is None:
            context = {}
        if not isinstance(ids, list):
            ids = [ids]
        assert len(ids) == 1, "ids must be a 1-element list."

        attachment_obj = self.pool.get('ir.attachment')
        attachment_tag_obj = self.pool.get('ir.attachment.tag')
        conf_obj = self.pool.get('configuration.data')

        conf_data = conf_obj.get(cr, uid, [], context=context)
        report_name = conf_data.aia_report_account_invoice.report_name

        attachment_ids = []
        if report_name:
            inv = self.browse(cr, uid, ids[0], context=context)
            att_name = inv.aia_get_attachment_name_for_invoice()

            if not attachment_obj.search(
                cr, uid, [('res_model', '=', 'account.invoice'),
                          ('res_id', '=', inv.id),
                          ('name', '=', att_name),
                          ], count=True, limit=1, context=context):

                pdf_data = get_pdf_from_report(
                    cr, uid, 'report.' + report_name,
                    {'ids': inv.id, 'model': 'account.invoice'},
                    context=context)
                attach_id = associate_ir_attachment_with_object(
                    self, cr, uid, pdf_data, att_name,
                    'account.invoice', inv.id)

                if attach_id:
                    invoice_tag_id = attachment_tag_obj.get_tag_id(
                        cr, uid, [], 'invoice', context=context)
                    attachment_obj.write(
                        cr, uid, attach_id,
                        {'tags_ids': [(4, invoice_tag_id, False)]},
                        context=context)
                    attachment_ids.append(attach_id)
                else:
                    aia_info.error = True
                    aia_info.message = _("No attachment was generated when "
                                         "printing the report for the invoice "
                                         "with ID={0} in the Account.Invoice "
                                         "Automation").format(inv.id)

        else:  # if not report_name:
            aia_info.error = True
            aia_info.message = _("No report for the Account.Invoice "
                                 "Automation was set for invoices in "
                                 "Post Configuration > Reports.")

        return attachment_ids

    def aia_get_attachment_name_for_invoice(self, cr, uid, ids, context=None):
        """ Gets the name to be used as attachment when printing & attaching
            and invoice in the Account.Invoice Automation.
        """
        if context is None:
            context = {}
        if not isinstance(ids, list):
            ids = [ids]
        assert len(ids) == 1, "ids must be a 1-element list."

        return 'invoice_aia_inv{0}.pdf'.format(ids[0])

    def aia_send_invoice(self, cr, uid, ids, aia_info, context=None):
        """ Sends the invoice, according to the routing set.
        """
        if context is None:
            context = {}
        if not isinstance(ids, list):
            ids = [ids]
        assert len(ids) == 1, "ids must be a 1-element list."

        inv = self.browse(cr, uid, ids[0], context=context)
        routing = inv.invoice_routing

        if routing == 'default':
            # This is the default sending in the PCAP1 project, only used
            # for invoices not being automated by the Invoice Automation,
            # but for another one (maybe the Sale.Order Automation). In other
            # words: no invoice automated by the AIA should have this routing,
            # which is something we check before, but here we raise just
            # in case.
            aia_info.error = True
            aia_info.message = _("The 'default' routing is not intended for "
                                 "the Account.Invoice Automation.")

        elif routing == 'email':
            # Sends the invoice by regular email to the partner of the invoice.
            inv.aia_send_invoice_to_partner(aia_info)

        elif routing == 'docout':
            # Sends the invoice by regular doc-out.
            inv.aia_maybe_send_invoice_to_docout(aia_info)

        elif routing == 'pfgateway':
            # Sends the invoice using the special PostFinance Gateway.
            aia_info.error = True
            aia_info.message = _("Routing 'pfgateway' is not yet implemented.")

        else:
            aia_info.error = True
            aia_info.message = _("'{0}' is not a valid routing.").format(routing)

        return True

    def aia_send_invoice_to_partner(self, cr, uid, ids, aia_info, context=None):
        """ Enqueues the sending of the invoice by email to the partner
            of the invoice.
        """
        if context is None:
            context = {}
        if not isinstance(ids, list):
            ids = [ids]
        assert len(ids) == 1, "ids must be a 1-element list."

        configuration_obj = self.pool.get('configuration.data')
        attachment_obj = self.pool.get('ir.attachment')
        attachment_tag_obj = self.pool.get('ir.attachment.tag')
        mail_template_obj = self.pool.get("email.template")
        mail_mail_obj = self.pool.get('mail.mail')

        inv = self.browse(cr, uid, ids[0], context=context)
        config = configuration_obj.get(cr, uid, [], context=context)

        try:
            # Composes the email with the template provided.
            email_template_id = config.aia_route_email_template_id
            if not email_template_id:
                aia_info.error = True
                aia_info.message = _("An email template is missing for the "
                                     "Invoice Automation with route 'email'.")
            else:
                values = mail_template_obj.generate_email(
                    cr, uid, email_template_id, inv.id, context=context)
                msg_id = mail_mail_obj.create(cr, uid, values, context=context)

                # Adds the attachment of the invoice to the template.
                invoice_tag_id = attachment_tag_obj.get_tag_id(
                    cr, uid, [], 'invoice', context=context)
                attachment_ids = attachment_obj.search(cr, uid, [
                    ('res_model', '=', 'account.invoice'),
                    ('res_id', '=', inv.id),
                    ('tags_ids', 'in', invoice_tag_id),
                ], context=context)
                mail_mail_obj.write(cr, uid, msg_id, {
                    'attachment_ids': [(6, 0, attachment_ids)],
                },context=context)

        except Exception as e:
            aia_info.error = True
            aia_info.message = _("An error happened while sending the invoice "
                                 "with ID={0} by email: {1}").format(inv.id, e)
            pass  # TODO. Log issue, write on the log, raise.

    def aia_maybe_send_invoice_to_docout(self, cr, uid, ids, aia_info, context=None):
        """ Sends the invoice to the doc-out, if it has to.
        """
        if context is None:
            context = {}
        if not isinstance(ids, list):
            ids = [ids]
        assert len(ids) == 1, "ids must be a 1-element list."

        inv = self.browse(cr, uid, ids[0], context=context)
        if inv.check_send_invoice_to_docout():
            inv.mark_invoice_to_be_sent_to_docout(attach_tags=['invoice'])

        return True

    def check_send_invoice_to_docout(self, cr, uid, ids, context=None):
        """ Overridden because the original code assumes that an invoice
            has always a sale.order, but that is not the case for the
            Account.Invoice Automation.
        """
        if context is None:
            context = {}
        if not isinstance(ids, list):
            ids = [ids]
        assert len(ids) == 1, "ids must be a 1-element list."

        inv = self.browse(cr, uid, ids[0], context=context)

        if not inv.sale_ids:
            # If the invoice doens't have a sale.order, that means we are
            # inside the Account.Invoice Automation, so the algorithm to
            # decide if an invoice is sent to the doc-out is simplified.

            is_epaid = inv.payment_method_id.epayment
            send_invoice_to_docout = not is_epaid
            if send_invoice_to_docout:
                # New requirement in t7051: if the BVR is filled with XXXs,
                # then don't send it to the doc-out.
                if not self.show_bvr(cr, uid, ids, context=context):
                    send_invoice_to_docout = False

        else:
            # If the invoice has orders associated to it, that means we are
            # outside the Account.Invoice Automation, and we have to take
            # into account the whole algorithm.

            send_invoice_to_docout = \
                super(account_invoice_ext, self).check_send_invoice_to_docout(
                    self, cr, uid, ids, context=context)

        if not send_invoice_to_docout:
            logger.info("Invoice with ID={0} won't be sent to the "
                        "doc-out.".format(inv.id))

        return send_invoice_to_docout

    def is_epaid(self, cr, uid, ids, context=None):
        """ Overridden because the original code assumes that an invoice
            has always a sale.order, but that is not the case for the
            Account.Invoice Automation. This is overridden because show_bvr()
            calls it.
        """
        if context is None:
            context = {}
        if not isinstance(ids, list):
            ids = [ids]
        assert len(ids) == 1, "ids must be a 1-element list."

        inv = self.browse(cr, uid, ids[0], context=context)

        if not inv.sale_ids:
            is_epaid = inv.payment_method_id.epayment
        else:
            is_epaid = super(account_invoice_ext, self).check_send_invoice_to_docout(
                cr, uid, ids, context=context)

        return is_epaid

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
