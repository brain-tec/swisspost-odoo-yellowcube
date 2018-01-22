# b-*- encoding: utf-8 -*-
##############################################################################
#
#    Copyright (c) 2016 brain-tec AG (http://www.braintec-group.com)
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
import openerp
import logging
from datetime import timedelta, datetime
from openerp.osv import osv, fields
from openerp.tools.translate import _
from openerp.addons.pc_generics import generics
from openerp.addons.pc_generics.generics import report_ext
from openerp.addons.pc_log_data.log_data import write_log
from openerp.addons.pc_connect_master.utilities.others import \
    format_exception
from openerp.tools import DEFAULT_SERVER_DATETIME_FORMAT, DEFAULT_SERVER_DATE_FORMAT

logger = logging.getLogger(__name__)


@generics.has_mako_header()
class account_invoice_ext(osv.Model):
    _inherit = 'account.invoice'

    def _fun_epayment(self, cr, uid, ids, field_name, args, context=None):
        if context is None:
            context = {}
        result = {}
        for invoice in self.browse(cr, uid, ids, context=context):
            result[invoice.id] = False
            if invoice.sale_ids:
                result[invoice.id] = invoice.sale_ids[0].payment_method_id.epayment
        return result

    def _fun_responsible_id(self, cr, uid, ids, field_name, args, context=None):
        result = {}
        for invoice in self.browse(cr, uid, ids, context):
            result[invoice.id] = self.get_responsible(invoice.partner_id).id
        return result

    def _sto_child_related_partners(self, cr, uid, ids, context=None):
        if not isinstance(ids, list):
            ids = [ids]
        # Let 0 because of possible empty list
        ids = [str(x) for x in ids] + ['0']
        cr.execute('SELECT id FROM account_invoice WHERE partner_id IN ({0})'.format(','.join(ids)))
        return [x[0] for x in cr.fetchall()]

    _columns = {
        # Functional fields needed for the outlook view of the invoices.
        'partner_invoice_dunning_block': fields.related('partner_id', 'dunning_block', type='boolean', readonly=True, string="Partner's Dunning Block", help='Does the partner has a dunning block?'),
        'partner_dunning_block_ending_date': fields.related('partner_id', 'dunning_block_date', type='date', readonly=True, string="Partner's Dunning Block's Ending Date", help="Ending block for the partner's dunning block."),
        'epayment': fields.function(_fun_epayment, type='boolean', string='Payment Method has Epayment?', help='Does the payment method has epayment?'),

        'responsible_id': fields.function(_fun_responsible_id,
                                          type="many2one",
                                          relation="res.partner",
                                          string='Responsible of the invoice',
                                          store={'res.partner': (_sto_child_related_partners, ['parent_id'], 10)}),
    }

    def get_responsible(self, partner):
        while partner.parent_id and partner.id != partner.parent_id.id:
            partner = partner.parent_id
        return partner

    def update_dunning_blocks(self, cr, uid, date_today, context):
        cr.execute("SAVEPOINT update_dunning_blocks")
        try:
            ret = super(account_invoice_ext, self).update_dunning_blocks(cr, uid, date_today, context)
            cr.execute("RELEASE update_dunning_blocks")
            return ret
        except Exception as e:
            text = format_exception(e)
            logger.error(text)
            cr.execute("ROLLBACK TO SAVEPOINT update_dunning_blocks")
            write_log(self, cr, uid, 'res.users', 'Follow-up: update_dunning_blocks', uid, text, correct=False)

    def single_update_followup(self, cr, uid, ids, date_today, followup_levels, context=None):
        cr.execute("SAVEPOINT single_update_followup")
        try:
            ret = super(account_invoice_ext, self).single_update_followup(cr, uid, ids, date_today, followup_levels, context=context)
            cr.execute("RELEASE single_update_followup")
            return ret
        except Exception as e:
            text = format_exception(e)
            logger.error(text)
            cr.execute("ROLLBACK TO SAVEPOINT single_update_followup")
            for _id in ids:
                write_log(self, cr, uid, 'account.invoice', 'Follow-up: single_update_followup', _id, text, correct=False)

    def do_partner_manual_action(self, cr, uid, invoice_ids, context=None):
        cr.execute("SAVEPOINT do_partner_manual_action")
        try:
            ret = super(account_invoice_ext, self).do_partner_manual_action(cr, uid, invoice_ids, context=context)
            cr.execute("RELEASE do_partner_manual_action")
            return ret
        except Exception as e:
            text = format_exception(e)
            logger.error(text)
            cr.execute("ROLLBACK TO SAVEPOINT do_partner_manual_action")
            for _id in invoice_ids:
                write_log(self, cr, uid, 'account.invoice', 'Follow-up: do_partner_manual_action', _id, text, correct=False)

    def cron_send_followups_to_doc_out(self, cr, uid, context=None):
        ''' Sends the follow-ups to the doc-out.
        '''
        if context is None:
            context = {}

        ir_attachment_obj = self.pool.get('ir.attachment')
        config_data = self.pool.get('configuration.data').get(cr, uid, None, context)

        # Common configuration to any option.
        file_type = 'followup'
        sending_option = config_data.docout_followup_sending_option

        # Do we want to send the files to an email address?
        if config_data.docout_followup_activate_send_to_email:
            email_template_id = config_data.docout_followup_email_template_to_docout_id
            email_address = config_data.docout_followup_email_address
            attachment_ids = ir_attachment_obj.search(cr, uid, [('name', 'ilike', '%.pdf'),
                                                                ('docout_file_type', '=', file_type),
                                                                ('docout_state_email', '=', 'to_send'),
                                                                ], order='create_date DESC', context=context)
            if attachment_ids:
                ir_attachment_obj.send_pending_files_to_docout_email(cr, uid, attachment_ids, file_type, sending_option, email_template_id, email_address, context=context)

        # Do we want to send the files to a remote folder?
        if config_data.docout_followup_activate_send_to_server:
            connect_transport = config_data.docout_followup_connect_transport_id
            remote_folder = config_data.docout_followup_folder
            attachment_ids = ir_attachment_obj.search(cr, uid, [('name', 'ilike', '%.pdf'),
                                                                ('docout_file_type', '=', file_type),
                                                                ('docout_state_remote_folder', '=', 'to_send'),
                                                                ], order='create_date DESC', context=context)
            if attachment_ids:
                ir_attachment_obj.send_pending_files_to_docout_folder(cr, uid, attachment_ids, file_type, sending_option, connect_transport, remote_folder, context=context)

        return True

    def cron_handle_invoice_followup_action(self, cr, uid, context=None):
        '''
        Stores the date of today, just in case it changes
        during the execution of this method.
        '''
        if context is None:
            context = {}
        logger.debug("POST: Handle invoice follow-up action")
        date_today_str = datetime.now().strftime(DEFAULT_SERVER_DATETIME_FORMAT)

        partner_ids = self.pool.get("res.partner").search(cr,
                                                          uid,
                                                          [('dunning_block', '=', True),
                                                           ('dunning_block_date', '<', date_today_str)],
                                                          context=context)
        self.pool.get("res.partner").write(cr, uid, partner_ids, {'dunning_block': False}, context=context)

        company_ids = self.pool.get('res.company').search(cr, uid, [], context=context)
        for company_id in company_ids:
            invoice_ids = self.search(cr, uid, [('company_id', '=', company_id),
                                                ('type', '=', 'out_invoice'),
                                                ('state', '=', 'open'),
                                                ('dunning_block', '=', False),
                                                ('followup_level_handled', '=', False),
                                                ('followup_level_id', '!=', None),
                                                ], context=context)

            # Removes those invoices which have a follow-up
            # which require a manual action.
            invoice_ids_without_manual_action = []
            for id_ in invoice_ids:
                invoice = self.browse(cr, uid, id_, context=context)
                requires_manual_action = invoice.followup_level_id.manual_action
                if requires_manual_action:
                    # Log an issue.
                    self.do_partner_manual_action(cr, uid, [id_], context)
                    logger.info(_('Manual action required. Invoice {0} (with id={1}) requires manual action.').format(id_, invoice.number))
                    write_log(self, cr, uid, 'account.invoice', 'Follow-up', id_, _('Manual action required'), _('Invoice {0} (with id={1}) requires manual action.').format(id_, invoice.number))
                else:
                    invoice_ids_without_manual_action.append(id_)

            self.pool.get('account.invoice').do_handle_followup(cr, uid, invoice_ids_without_manual_action, context=context)

        return True

    def fill_context_with_wildcards(self, cr, uid, values, partner, context=None):
        '''
        Adding partner first name
        '''
        if context is None:
            context = {}

        # Gets the format for dates according to the res.partner's language.
        res_lang = self.pool.get('res.lang')
        partner_lang_id = res_lang.search(cr, uid, [('code', '=', partner.lang)], context=context, limit=1)[0]
        partner_lang = res_lang.browse(cr, uid, partner_lang_id, context=context)

        values['{yesterday}'] = (datetime.now() + timedelta(-1)).strftime(partner_lang.date_format)
        values['{partner_firstname}'] = partner.firstname
        values['{partner_lastname}'] = partner.lastname
        super(account_invoice_ext, self).fill_context_with_wildcards(cr, uid, values, partner, context=context)

    def get_email_servicedesk_followups(self, cr, uid, ids, context=None):
        ''' Returns the email defined as the service-desk email for follow-ups, or the empty
            string if it is not defined.
        '''
        if context is None:
            context = {}
        config_data = self.pool.get('configuration.data').get(cr, uid, [], context=context)
        email = config_data.followup_servicedesk_email_address
        if not email:
            email = ''
        return email

    def _vals_to_write_to_handled_invoice(self, cr, uid, ids, context=None):
        ''' Overridden so that we add the comment of the invoice.
        '''
        if context is None:
            context = {}
        if type(ids) is not list:
            ids = [ids]

        invoice = self.browse(cr, uid, ids[0], context=context)

        vals = super(account_invoice_ext, self)._vals_to_write_to_handled_invoice(cr, uid, ids, context=context)
        vals.update({'comment': _('{0}\nThis invoice is under a follow-up process.').format(invoice.comment)})
        return vals

    def _vals_to_create_penalization_invoice(self, cr, uid, ids, context=None):
        ''' Overridden so that we add the comment of the invoice.
        '''
        if context is None:
            context = {}
        if type(ids) is not list:
            ids = [ids]

        invoice = self.browse(cr, uid, ids[0], context=context)

        vals = super(account_invoice_ext, self)._vals_to_create_penalization_invoice(cr, uid, ids, context=context)
        vals.update({'comment': _('This is a follow-up pro-forma invoice which comes from invoice {0}.').format(invoice.number)})
        return vals

    def do_handle_followup(self, cr, uid, ids, context=None):
        ''' This method is intended to be used over invoices which are under a follow-up level which has not been handled yet.
                 - If the method is called from a server action, the ids are specified in the context
                 - If the method is called from a button, the ids are specified in the ids parameter
        '''
        if context is None:
            context = {}
        if not isinstance(ids, list):
            ids = [ids]

        context['ids_not_handled'] = []
        context['exception'] = False
        ir_attachment_ids = super(account_invoice_ext, self).do_handle_followup(cr, uid, ids, context)

        ir_attach_obj = self.pool.get('ir.attachment')

        if context.get('do_default_docout_followup_sending', True):
            # If we generated attachments, we prepare them for the sending
            # to the doc-out unless we are explicitly told to not do so
            # in the context.
            for attach in ir_attach_obj.browse(cr, uid, ir_attachment_ids, context=context):
                docout_filename = self.get_docout_filename_followups(
                    cr, uid, attach.res_id, context=context)
                ir_attach_obj.write(cr, uid, attach.id, {
                    'docout_state_email': 'to_send',
                    'docout_state_remote_folder': 'to_send',
                    'docout_file_type': 'followup',
                    'docout_exported_file_name_email': docout_filename,
                    'docout_exported_file_name_remote_folder': docout_filename,
                }, context=context)

        # Sends a summary email with the list of follow-ups which were correctly handled, and
        # those which resulted in some error while handling them.
        ids_correctly_handled = list(set(ids) - set(context['ids_not_handled']))
        self.send_summary_email(cr, uid, ids_correctly_handled, list(context['ids_not_handled']), context=context)

        return ir_attachment_ids

    def get_docout_filename_followups(self, cr, uid, ids, context=None):
        """ Gets the file name for the doc-out of follow-ups.
        """
        if not isinstance(ids, list):
            ids = [ids]

        inv = self.browse(cr, uid, ids[0], context=context)
        account_invoice_yyyymmdd = datetime.strptime(
            inv.date_invoice, DEFAULT_SERVER_DATE_FORMAT).strftime('%Y%m%d')

        docout_filename = '{database}_FU_{invoice_number}_{yymmdd}.pdf'.format(
            database=cr.dbname,
            invoice_number=inv.number.replace('/', ''),
            yymmdd=account_invoice_yyyymmdd)

        return docout_filename

    def do_followup_mail(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        context['exception'] = False
        return super(account_invoice_ext, self).do_followup_mail(cr, uid, ids, context=context)

    def get_list_of_invoices_with_followup_handled(self, cr, uid, ids, context=None):
        ''' Creates an HTML list with the invoices which where handled (either correctly or incorrectly), with its follow-up level.
                The list of invoices correctly handled must be passed in the context as 'ids_correctly_handled'.
        '''
        if context is None:
            context = {}
        return self._get_list_of_invoices(cr, uid, context.get('ids_correctly_handled', []), context=context)

    def get_list_of_invoices_with_error_while_handling_followup(self, cr, uid, ids, context=None):
        ''' Creates an HTML list with the invoices which where incorrectly handled, with its follow-up level.
                The list of invoices incorrectly handled must be passed in the context as 'ids_incorrectly_handled'.
        '''
        if context is None:
            context = {}
        return self._get_list_of_invoices(cr, uid, context.get('ids_incorrectly_handled', []), context=context)

    def _get_list_of_invoices(self, cr, uid, ids, context=None):
        ''' Creates an HTML list with the invoices and its follow-up level.
        '''
        if context is None:
            context = {}
        if type(ids) is not list:
            ids = [ids]

        invoices_list_html = ''
        if ids:
            invoices_list_html = '{0}<ul>\n'.format(invoices_list_html)
            for invoice in self.browse(cr, uid, ids, context=context):
                invoices_list_html = '{current_html}   <li>{invoice} ({followup_level})</li>\n'.format(current_html=invoices_list_html, invoice=invoice.number, followup_level=invoice.followup_level_id.name)
            invoices_list_html = '{0}</ul>\n'.format(invoices_list_html)
        return invoices_list_html

    def send_summary_email(self, cr, uid, ids_correctly_handled, ids_not_handled, context=None):
        ''' Sends a summary email to the follow-up service desk, listing those invoices
            which had to be handled because of being in a follow-up process.
                Lists the invoices which were correctly handled, and those which were
            not correctly handled (if any). If no invoices were handled, then no email is
            sent.
        '''
        if context is None:
            context = {}

        followup_errors_obj = self.pool.get('followup.errors')

        config_data = self.pool.get('configuration.data').get(cr, uid, None, context)
        all_ids = ids_correctly_handled + ids_not_handled

        email_template = config_data.followup_servicedesk_email_template_id
        email_address = config_data.followup_servicedesk_email_address
        if email_address and email_template and (len(all_ids) > 0):
            try:
                ctx = context.copy()
                ctx['ids_correctly_handled'] = ids_correctly_handled
                ctx['ids_incorrectly_handled'] = ids_not_handled
                ctx['default_type'] = 'email'
                values = self.pool.get("email.template").generate_email(cr, uid, email_template.id, all_ids[0], context=ctx)
                self.pool.get('mail.mail').create(cr, uid, values, context=ctx)

            except Exception as e:
                error_message = _('It was not possible to send an email to inform about the handling of the follow-ups.')
                logger.warning(error_message)
                for invoice_id in all_ids:
                    followup_errors_obj.create_error_entry(cr, uid, [], invoice_id, error_message, context=context)

                # Logs an issue in the project manager.
                write_log(self, cr, uid, 'account.invoice', 'Follow-up', all_ids[0],
                          'Follow-up error: Error sending the emails', False, error_message)  # False=error.

        return True

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
