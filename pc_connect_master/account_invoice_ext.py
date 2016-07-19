# b-*- encoding: utf-8 -*-
##############################################################################
#
#    Copyright (c) 2014 brain-tec AG (http://www.brain-tec.ch)
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

from openerp.osv import osv, fields
from openerp.tools import float_compare
from openerp.tools import DEFAULT_SERVER_DATETIME_FORMAT
from openerp.tools.translate import _
from utilities import filters
from datetime import datetime
from utilities.misc import format_exception


class account_invoice_ext(osv.Model):
    _inherit = 'account.invoice'

    # BEGIN OF THE CODE WHICH DEFINES THE NEW FILTERS TO ADD TO THE OBJECT.
    def _replace_week_placeholders(self, cr, uid, args, context=None):
        return filters._replace_week_placeholders(self, cr, uid, args, context=context)

    def _replace_quarter_placeholders(self, cr, uid, args, context=None):
        return filters._replace_quarter_placeholders(self, cr, uid, args, context=context)

    def search(self, cr, uid, args, offset=0, limit=None, order=None, context=None, count=False):
        return filters.search(self, cr, uid, args, account_invoice_ext, offset=offset, limit=limit, order=order, context=context, count=count)

    def read_group(self, cr, uid, domain, fields, groupby, offset=0, limit=None, context=None, orderby=False):
        return filters.read_group(self, cr, uid, domain, fields, groupby, account_invoice_ext, offset=offset, limit=limit, context=context, orderby=orderby)
    # END OF THE CODE WHICH DEFINES THE NEW FILTERS TO ADD TO THE OBJECT.

    def requires_rounding(self, cr, uid, ids, context=None):
        ''' Returns whether an invoice requires to be rounded to the Swiss rounding.
            This can happen when its amount is already rounded.

            This method must be called over just one ID.
        '''
        if context is None:
            context = {}
        if not isinstance(ids, list):
            ids = [ids]

        invoice = self.browse(cr, uid, ids[0], context=context)

        # Computes the quantity rounded, according to the Swiss 0.00 or 0.05 rounding.
        amount_total_rounded = 0.00
        currency_obj = self.pool.get('res.currency')
        currency_round_ids = currency_obj.search(cr, uid, [('name', '=', 'CH5'), ('active', '=', False)])
        if currency_round_ids:
            currency_round = currency_obj.browse(cr, uid, currency_round_ids[0], context=context)
            amount_total_rounded = currency_obj.round(cr, uid, currency_round, invoice.amount_total)

        invoice_already_rounded = ((invoice.amount_total - amount_total_rounded) == 0)

        return (not invoice_already_rounded)

    def get_file_name(self, cr, uid, ids, context=None):
        ''' Returns a unique file name for this invoice.
        '''
        if context is None:
            context = {}
        if not isinstance(ids, list):
            ids = [ids]
        account_invoice = self.browse(cr, uid, ids[0], context=context)
        file_name = 'invoice_{0}_inv{1}.pdf'.format(account_invoice.origin or '', account_invoice.id)
        return file_name

    def is_printed(self, cr, uid, ids, context=None):
        ''' Returns if we have printed the attachment for this invoice.
        '''
        if context is None:
            context = {}
        if not isinstance(ids, list):
            ids = [ids]

        ir_attachment_obj = self.pool.get('ir.attachment')

        invoice_id = ids[0]
        file_name = self.get_file_name(cr, uid, invoice_id, context=context)

        attachment_count = ir_attachment_obj.search(cr, uid, [('res_model', '=', 'account.invoice'),
                                                              ('res_id', '=', invoice_id),
                                                              ('name', '=', file_name),
                                                              ], context=context, count=True)
        return (attachment_count > 0)

    def cron_send_invoices_to_partner(self, cr, uid, context=None):
        ''' Sends the invoices to the partner, by email.
        '''
        if context is None:
            context = {}

        # Gets the email template to use to send the invoices to the partner.
        # If no email template is indicated, then no invoices are sent.
        configuration_data = self.pool.get('configuration.data').get(cr, uid, None, context)
        invoice_to_partner_email_template = configuration_data.invoice_to_partner_email_template_id

        if invoice_to_partner_email_template:
            account_invoice_obj = self.pool.get('account.invoice')
            ir_attachment_obj = self.pool.get('ir.attachment')
            mail_template_obj = self.pool.get("email.template")
            mail_mail_obj = self.pool.get('mail.mail')
            project_issue_obj = self.pool.get('project.issue')

            # List of invoices which were successfully sent to the partners.
            successfully_sent_invoice_ids = []

            # Looks for all the invoices which are pending to be sent to the partners.
            account_invoice_ids = account_invoice_obj.search(cr, uid, [('send_invoice_to_partner', '=', 'to_send')], context=context)
            for account_invoice_id in account_invoice_ids:

                # Gets the name of the attachment of the invoice.
                file_name = account_invoice_obj.get_file_name(cr, uid, account_invoice_id, context=context)

                # Gets the ir.attachment
                ir_attachment_id = ir_attachment_obj.search(cr, uid, [('res_model', '=', 'account.invoice'),
                                                                      ('res_id', '=', account_invoice_id),
                                                                      ('name', '=', file_name)], context=context)

                # Generates the email from the template and adds the attachment.
                try:
                    values = mail_template_obj.generate_email(cr, uid, invoice_to_partner_email_template.id, account_invoice_id, context=context)
                    msg_id = mail_mail_obj.create(cr, uid, values, context=context)
                    mail_mail_obj.write(cr, uid, msg_id, {'attachment_ids': [(6, 0, ir_attachment_id)]}, context=context)
                    successfully_sent_invoice_ids.append(account_invoice_id)

                except Exception as e:
                    issue_ids = project_issue_obj.find_resource_issues(cr, uid, 'account.invoice', account_invoice_id, tags=['partner'], create=True, reopen=True, context=context)
                    error_message = _('Account.invoice with ID={0} could not be sent to the partner: {1}').format(account_invoice_id, format_exception(e))
                    for issue_id in issue_ids:
                        project_issue_obj.message_post(cr, uid, issue_id, error_message, context=context)

            # Only those invoices correctly sent are marked as sent.
            self.write(cr, uid, successfully_sent_invoice_ids, {'send_invoice_to_partner': 'sent'}, context=context)

        return True

    def get_salutation(self, cr, uid, ids, context=None):
        ''' Returns a salutation for templates.
            The salutation is different depending on if the res.partner is company, has known gender, etc.
        '''
        if context is None:
            context = {}

        if isinstance(ids, list):
            ids = ids[0]

        invoice = self.browse(cr, uid, ids, context)
        return invoice.partner_id.get_salutation()

    def check_tax_lines(self, cr, uid, inv, compute_taxes, ait_obj):
        ''' This method complements a missing functionality in bt_account
        '''
        company_currency = self.pool['res.company'].browse(cr, uid, inv.company_id.id).currency_id
        if not inv.tax_line:
            for tax in compute_taxes.values():
                ait_obj.create(cr, uid, tax)
        else:
            tax_key = []
            for tax in inv.tax_line:
                if tax.manual:
                    continue
                # The analytic_id is not part of standard Odoo, and should be used in this method for comparision
                analytic_id = False
                if 'account_analytic_id' in tax:
                    analytic_id = tax['account_analytic_id'] and tax['account_analytic_id'].id or False
                key = (tax.tax_code_id.id, tax.base_code_id.id, tax.account_id.id, analytic_id)
                print key

                # Ported pull #807 to v7.
                # Comment there: The code will accept taxes defined by core functionality and BT-Accounting.
                if key not in compute_taxes:
                    key = key[:3]

                tax_key.append(key)
                if key not in compute_taxes:

                    raise osv.except_osv(_('Warning!'), _('Global taxes defined, but they are not in invoice lines !'))
                base = compute_taxes[key]['base']
                precision = self.pool.get('decimal.precision').precision_get(cr, uid, 'Account')
                if float_compare(abs(base - tax.base), company_currency.rounding, precision_digits=precision) == 1:
                    raise osv.except_osv(_('Warning!'), _('Tax base different!\nClick on compute to update the tax base.'))
            for key in compute_taxes:
                if key not in tax_key:
                    raise osv.except_osv(_('Warning!'), _('Taxes are missing!\nClick on compute button.'))

    def action_cancel(self, cr, uid, ids, context=None):
        ''' Overwritten so that when the invoice is set to cancel, we store its current time.
        '''
        if context is None:
            context = {}
        self.write(cr, uid, ids, {'date_cancel': fields.datetime.now()}, context=context)
        return super(account_invoice_ext, self).action_cancel(cr, uid, ids, context)

    _columns = {
        # This field 'sale_ids' is copied from the 'Sale Automatic Workflow' module. We need this field, but do not need the
        # dependency to that module. In the original code it is commented that it would be good to have this field in the 'account'
        # module, so watch out when this happens so that this duplicated field can be removed then.
        'sale_ids': fields.many2many('sale.order', 'sale_order_invoice_rel',
                                     'invoice_id', 'order_id', string='Sale Orders'),
        # Indicates if the invoice needs to be sent to the res.partner.
        'send_invoice_to_partner': fields.selection([('not_applicable', 'Not Applicable'),
                                                     ('to_send', 'To Send'),
                                                     ('sent', 'Sent')], 'Send to Partner',
                                                    help='Indicates whether the invoice was sent to the partner by email.'),
        'date_cancel': fields.datetime('Cancel Date', help='The date in which the invoice was set to cancel.'),
    }

    _defaults = {
        'send_invoice_to_partner': 'not_applicable',
    }

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
