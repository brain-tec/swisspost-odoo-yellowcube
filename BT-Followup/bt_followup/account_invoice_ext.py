# b-*- encoding: utf-8 -*-
#
#
#    Copyright (c) 2015 brain-tec AG (http://www.brain-tec.ch)
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
#

from tools.translate import _
from osv import fields, osv, orm
from bt_helper.tools import bt_misc
from bt_helper.log_rotate import get_log, write_log, format_exception
from openerp.osv.orm import except_orm
from openerp.tools import DEFAULT_SERVER_DATETIME_FORMAT, DEFAULT_SERVER_DATE_FORMAT
import openerp.addons.decimal_precision as dp
import datetime
# libraries to sort, group and print lists
import operator
import itertools
from report_webkit import report_helper
import base64
from openerp import pooler
logger = get_log("DEBUG")


def get_bank_account(delegate, cr, uid, context=None):
    if context is None:
        context = {}

    company_id = delegate.pool.get(
        'res.users').browse(cr,
                            uid,
                            uid,
                            context=context).company_id.id
    company_obj = delegate.pool.get(
        'res.company').browse(cr,
                              uid,
                              company_id,
                              context=context)

    account_number = None
    if len(company_obj.bank_ids) > 0:
        account_number = company_obj.bank_ids[0].acc_number
    return account_number


class account_invoice_ext(osv.osv):

    _inherit = 'account.invoice'

    def write(self, cr, uid, ids, values, context=None):
        ''' Overrides the write so that the field which stores the virtual due date,
            'follow_up_date_due', is set when the invoice goes to state 'open' (because it depends
            on 'date_due' and when the invoice is in state 'open' its genuine 'due date' won't
            change anymore).

            Also checks that the end date of the dunning block is no set in the past.
        '''

        if context is None:
            context = {}

        # Checks that the end date of the dunning block is not set in the past.
        if 'dunning_block_ending_date' in values:
            date_today_str = datetime.date.today().strftime(DEFAULT_SERVER_DATE_FORMAT)
            if values['dunning_block_ending_date'] and (values['dunning_block_ending_date'] < date_today_str):
                raise orm.except_orm(_('Data Error'),
                                     _('The end of the dunning block can not be set in the past, please change it.'))

        if 'invoice_dunning_block' in values or 'partner_invoice_dunning_block' in values:
            values.update({'dunning_block_date': fields.date.today()})

        if ('state' in values) and (values['state'] == 'open'):
            if type(ids) is list:
                ids = ids[0]
            invoice_obj = self.browse(cr, uid, ids, context)
            values.update({'follow_up_date_due': invoice_obj.date_due})

        return super(account_invoice_ext, self).write(cr, uid, ids, values, context)

    def _get_follow_up_date_due_days(self, cr, uid, ids,
                                     field_name,
                                     args,
                                     context=None):
        result = {}
        if context is None:
            context = {}
        for invoice in self.browse(cr, uid, ids, context):
            if invoice.state == 'proforma2':
                result[invoice.id] = False
                continue
            if not invoice['date_due']:
                result[invoice.id] = 0
                continue
            if not invoice['follow_up_date_due']:
                due_day = datetime.datetime.strptime(
                    invoice.date_due, '%Y-%m-%d').date()
            else:
                due_day = datetime.datetime.strptime(
                    invoice.follow_up_date_due,
                    '%Y-%m-%d').date()
            if not invoice['dunning_block'] or not invoice['dunning_block_date']:
                last_day = datetime.date.today()
            else:
                last_day = datetime.datetime.strptime(
                    invoice.dunning_block_date,
                    '%Y-%m-%d').date()
            result[invoice.id] = (last_day - due_day).days
        return result

    def _update_dunning_block_defered_due_date(self, cr, uid, ids, field, args,
                                               context=None):
        '''
        This function will update the dunning block,
        taking into account defered due date.
        '''
        if context is None:
            context = {}
        result = {}
        logger.debug("_change_on_dunning_block({0}, {1}, {2}, {3}, context={4})"
                     .format(self, cr, uid, ids, context))
        today = datetime.date.today()
        account_pool = self.pool.get('account.invoice')
        for invoice in account_pool.browse(cr, uid, ids, context):
            if 'dunning_block_effect' not in context and invoice.date_due:
                context['dunning_block_effect'] = True
                if not hasattr(invoice, 'follow_up_date_due') or not invoice.follow_up_date_due:
                    '''
                    We take the date_due if we do not have any followup level assigned.
                    '''
                    invoice.follow_up_date_due = invoice.date_due

                if invoice.dunning_block:
                    if invoice.dunning_block_date:
                        date_dunning = datetime.datetime.strptime(
                            invoice.dunning_block_date,
                            '%Y-%m-%d').date()
                    date_due = datetime.datetime.strptime(
                        invoice.follow_up_date_due,
                        '%Y-%m-%d').date()
                    if invoice.dunning_block_date:
                        date_due = date_due + (today - date_dunning)

                    account_pool.write(
                        cr,
                        uid,
                        invoice.id,
                        {'follow_up_date_due': date_due.strftime('%Y-%m-%d')}, context=context)

                del context['dunning_block_effect']
            result[
                invoice.id] = invoice.invoice_dunning_block or invoice.partner_id.dunning_block
        return result

    def _get_partner_invoices(self, cr, uid, partner_ids, context=None):
        ''' Gets the invoices associated to a given partner, AND ALSO
            the invoices associated to any of the res.partners in the same family than the given partner.
        '''
        if context is None:
            context = {}

        res_partner_pool = self.pool.get('res.partner')

        # Gets the IDs of the partners of the family.
        partner_family_ids = set()
        for partner_id in partner_ids:
            partner_family_ids = partner_family_ids.union(res_partner_pool._get_family_partners_ids(cr, uid, partner_id, context))
        partner_family_ids = list(partner_family_ids)

        # Gets the invoices which are associated to those partners.
        invoice_ids = self.pool.get('account.invoice').search(cr, uid, [('partner_id', 'in', partner_family_ids)], context=context)

        return invoice_ids

    def _amount_all_followups(self, cr, uid, ids, field, arg, context=None):

        res = {}.fromkeys(ids, {
            'followup_penalization_amount_untaxed': 0.0,
            'followup_penalization_amount_tax': 0.0,
            'followup_penalization_amount_total': 0.0,
        })

        for followup in self.browse(cr, uid, ids, context=context):
            res[followup.id]['followup_penalization_amount_untaxed'] += followup.amount_untaxed
            res[followup.id]['followup_penalization_amount_tax'] += followup.amount_tax
            res[followup.id]['followup_penalization_amount_total'] += followup.amount_total
            for inv in followup.followup_penalization_invoice_ids:
                res[followup.id]['followup_penalization_amount_untaxed'] += inv.amount_untaxed
                res[followup.id]['followup_penalization_amount_tax'] += inv.amount_tax
                res[followup.id]['followup_penalization_amount_total'] += inv.amount_total

        return res

    _columns = {
        'followup_level_id':
            fields.many2one(
                'followup.level',
                'Follow-up Level',
                readonly=True),
        'followup_level_date': fields.date('Follow-up Handling Date',
                                           readonly=True, states={
                                               'draft': [('readonly', False)]},
                                           help='The date in which the last follow-up handling (i.e., sending email, printing report...) took place.'),
        'followup_level_handled': fields.boolean('Follow-up Level Handled', readonly=True,
                                                 states={
                                                     'draft': [('readonly', False)]},
                                                 help='Indicates if the current follow-up level \
                                                 has already been handled (i.e., email sent, \
                                                 report printed...), preventing so the follow-up \
                                                 level from being handled multiple times'),

        'followup_parent_id': fields.many2one('account.invoice', 'Follow-up Parent Invoice',
                                              readonly=True),

        'followup_penalization_invoice_ids': fields.one2many('account.invoice', 'followup_parent_id',
                                                             'Follow-up Penalization Invoices',
                                                             readonly=True,
                                                             states={
                                                                 'draft': [('readonly', False)]}),
        'followup_penalization_line_ids': fields.related('followup_penalization_invoice_ids', 'invoice_line',
                                                         type="one2many", relation="account.invoice.line",
                                                         readonly=True),
        'followup_penalization_taxline_ids': fields.related('followup_penalization_invoice_ids', 'tax_line',
                                                         type="one2many", relation="account.invoice.tax",
                                                         readonly=True),

        'followup_penalization_amount_untaxed': fields.function(_amount_all_followups, digits_compute=dp.get_precision('Account'),
            store=False,
            multi='all'),
        'followup_penalization_amount_tax': fields.function(_amount_all_followups, digits_compute=dp.get_precision('Account'),
            store=False,
            multi='all'),
        'followup_penalization_amount_total': fields.function(_amount_all_followups, digits_compute=dp.get_precision('Account'),
            store=False,
            multi='all'),

        'followup_ids': fields.one2many('followup', 'followup_parent_id',
                                        'Follow-ups',
                                        readonly=True, states={
                                            'draft': [('readonly', False)]}),

        'followup_email_ids': fields.many2many('mail.mail', 'followup_invoice_mail_rel',
                                               'invoice_id', 'mail_id', 'Mail\'s'),

        # Related field to determine if the followup_skip_email_sending should
        # be shown in the view
        'followup_send_email': fields.related('followup_level_id', 'send_email', type='boolean',
                                              string='Send Follow-up Email'),
        'followup_skip_email_sending':
            fields.boolean('Skip Follow-up Email Sending'),

        'dunning_block': fields.function(
            _update_dunning_block_defered_due_date,
            type='boolean',
            string='Dunning Block',
            readonly=True,
            store={
                'res.partner': (_get_partner_invoices, ['dunning_block'], 10),
                'account.invoice': ((lambda self, cr, uid, x, context: x), ['invoice_dunning_block'], 10)
            }),
        'invoice_followup_notes': fields.text('Invoice Follow-up Notes'),
        'followup_responsible_id': fields.many2one('res.users', ondelete='set null',
                                                   string='Follow-up Responsible',),

        'partner_dunning_block': fields.related(
            'partner_id',
            'dunning_block',
            type='boolean',
            string='Dunning Block (Customer)',
            readonly=True,
            store=False),
        'invoice_dunning_block': fields.boolean('Dunning Block (Invoice)'),
        'follow_up_date_due_days':
            fields.function(
                _get_follow_up_date_due_days,
                string='Due Days',
                type='integer',
                readonly=False),
        'follow_up_date_due': fields.date('Due Date', readonly=False),
        'dunning_block_date': fields.date('Last Dunning Block Update'),
        'dunning_block_ending_date': fields.date('Dunning Block Ending Date'),

    }

    _defaults = {
        'dunning_block': False,
        'followup_skip_email_sending': False,
        'followup_level_handled': False,
    }

    def copy(self, cr, uid, invoice_id, defaults, context=None):
        if context is None:
            context = {}
        if not isinstance(defaults, dict):
            defaults = {}
        defaults['followup_level_id'] = False
        defaults['followup_level_date'] = False
        defaults['followup_level_handled'] = False
        defaults['followup_parent_id'] = False
        defaults['followup_penalization_invoice_ids'] = False
        defaults['followup_ids'] = False
        defaults['followup_email_ids'] = False

        return super(account_invoice_ext, self).copy(cr, uid, invoice_id, defaults, context)

    def check_invoice_conditions_to_update(self, invoice, date_today_str):
        '''
        If there is not followup level => We do not update
        If there is a followup level handled  => We do not update
        If  there is a followup level
            there is not a followup level handled
            AND (
                there is a dunning block active and
                the ending date of the dunning block is less than today
                the ending date is less than today  => We will update
                OR
                there is not dunning block
                ) => We will update
        '''
        if not invoice.followup_level_id:
            return False
        if invoice.followup_level_handled:
            return False
        if invoice.dunning_block:
            if ((invoice.dunning_block_ending_date is None) or
               (invoice.dunning_block_ending_date < date_today_str)):
                return False
        return True

    def check_is_customer_invoice(self, invoice, errors):
        '''
         only customer invoices can be handled
         @param invoice: object account.invoice
         @param errors: list of strings
                If there is an error, it will be set in errors list.
        @rtype: Boolean value: True => There is not errors
                               False => There is an errors
         '''
        if invoice.type != 'out_invoice':
            error_message = _("Handling a follow-up can only be executed for customer's invoices.")
            errors.append((invoice.id, 'Invoice {0}: {1}'.format(invoice.number, error_message)))
            return False
        return True

    def check_exists_email(self, invoice, errors):
        '''
         if the partner has no mail and in invoice follow up level action "Send mail"
         is set a message is logged in errors variable.
        @rtype: Boolean value: True => There is not errors
                               False => There is an errors
        '''
        if (not invoice.partner_id.email or invoice.partner_id.email == '') and invoice.followup_level_id.send_email:
            error_message = _(
                'This follow-up level requires to send an email, but its customer has no email defined.')
            errors.append(
                (invoice.id, 'Invoice {0}: {1}'.format(invoice.number, error_message)))
            return False
        return True

    def check_send_email(self, invoice, errors):
        '''
         If an email must be sent, but it has no email template, then
        an alarm is raised.
        @rtype: Boolean value: True => There is not errors
                               False => There is an errors
        '''
        send_email = invoice.followup_level_id.send_email
        if send_email and not invoice.followup_level_id.email_template_id:
            error_message = _('This follow-up level requires to send an email, but no email template is defined.')
            errors.append((invoice.id, 'Invoice {0}: {1}'.format(invoice.number, error_message)))
            return False

        email_template_id = invoice.followup_level_id.email_template_id
        if send_email and email_template_id and ((not email_template_id.email_to) or (not email_template_id.body_html)):
            error_message = _('This follow-up level requires to send an email, but its content or its destination is empty.')
            errors.append(
                (invoice.id, 'Invoice {0}: {1}'.format(invoice.number, error_message)))
            return False
        return True

    def check_bank_account(self, cr, uid, invoice, errors, context):
        '''
             If there is not any bank account associated, then do not handle the
             follow-up and set an error
             @rtype: Boolean value: True => There is not errors
                               False => There is an errors
        '''
        account_number = get_bank_account(self, cr, uid, context=context)
        if account_number is None:
            error_message = _('The company does not have a bank account defined.')
            errors.append((invoice.id, 'Invoice {0}: {1}'.format(invoice.number, error_message)))
            return False
        return True

    def check_letter(self, invoice, errors):
        '''
        If a letter must be sent, but it has no content, then an error message is shown.
        @rtype: Boolean value: True => There is not errors
                               False => There is an errors
        '''
        if invoice.followup_level_id.send_letter and not invoice.followup_level_id.description:
            error_message = _("This follow-up level requires to send a letter, but no letter's description is written.")
            errors.append((invoice.id, 'Invoice {0}: {1}'.format(invoice.number, error_message)))
            return False
        return True

    def check_all_invoice_restriction(self, cr, uid, invoice, errors, context):
        '''
        @rtype: Boolean value: True => There is not errors
                               False => There is an errors
        '''
        correct = True
        correct = correct and self.check_bank_account(cr, uid, invoice, errors, context)
        return correct

    def check_handle_invoice_restriction(self, invoice, errors):
        '''
        Check restrictions of the followup levels.
        @rtype: Boolean value: True => There is not errors
                               False => There is an errors
        '''
        correct = True
        correct = correct and self.check_is_customer_invoice(invoice, errors)
        correct = correct and self.check_exists_email(invoice, errors)
        correct = correct and self.check_send_email(invoice, errors)
        correct = correct and self.check_letter(invoice, errors)
        return correct

    def _vals_to_write_to_handled_invoice(self, cr, uid, ids, context=None):
        '''
        Helper method for do_handle_followup returning the values to write to an invoice
        to indicate that it is correctly handled.
        @rtype: dict
        '''
        if context is None:
            context = {}

        date_today_str = datetime.date.today().strftime(DEFAULT_SERVER_DATE_FORMAT)
        return {'followup_level_date': date_today_str,
                'followup_level_handled': True}

    def do_handle_followup(self, cr, uid, ids, context=None):
        """Executes the actions configured by current follow up level that is pending to handle.

        Note:
          Method can be called from the button Handle Follow-up on Invoice Form,
          From the method pes_partner.do_handle_followup method or from a server action
          (from the tree view).

          If the method is called from a server action, the ids are specified in the context
          as active_ids.
          If the method is called from a button, the ids are specified in the ids parameter.

        Args:
          ids (list of integers): List of invoices to handle.

        Returns:
          List with the ir.attachment's IDs of the reports generated.

          Moreover, context['ids_not_handled'] = with the ids_not_handled

        """
        # If the method is called from a server action, the ids are specified in the context
        # If the method is called from a button, the ids are specified in the
        # ids parameter
        if context is None:
            context = {}
        if not isinstance(ids, list):
            ids = [ids]

        if context.get('active_ids'):
            ids = context['active_ids']
        ctx = context.copy()
        ctx['active_ids'] = ids

        followup_errors_obj = self.pool.get('followup.errors')

        date_today_str = datetime.date.today().strftime('%Y-%m-%d')
        # Remove all invoices where dunning_block = True
        '''
        errors => We will add errors information in this array.
        new_ids => Used to create penalty invoices.
        ids_not_handled => To store those that are not handled.
        '''
        errors = []
        new_ids = []
        ids_not_handled = set()
        followup_model = self.pool.get('followup')
        for invoice in self.browse(cr, uid, ids, context=context):

            correct = self.check_all_invoice_restriction(cr, uid, invoice, errors, context)
            if correct:
                if self.check_invoice_conditions_to_update(invoice, date_today_str):
                    correct = self.check_handle_invoice_restriction(invoice, errors)
                    if correct:
                        new_ids.append(invoice.id)
                    else:
                        ids_not_handled.add(invoice.id)
                else:
                    ids_not_handled.add(invoice.id)
            else:
                ids_not_handled.add(invoice.id)

        # Send the errors, if any.
        for error_info in errors:
            invoice_id = error_info[0]
            error_message = error_info[1]
            followup_errors_obj.create_error_entry(cr, uid, [], invoice_id, error_message, context=context)

        if not new_ids:
            return []

        reports_printed_ids = []
        ids_with_errors = set()
        for invoice in self.browse(cr, uid, new_ids, context=context):

            cr.execute("SAVEPOINT do_handle_followup;")
            try:
                # send consolidated mails: one per partner and follow-up level
                invoice.do_followup_mail(context=context)

                # print consolidated report: one per partner and follow-up level
                report_printed_id = invoice.do_print_followup_report(context=context)
                reports_printed_ids.extend(report_printed_id)

                # Indicates that the invoice is now correctly handled.
                vals = invoice._vals_to_write_to_handled_invoice()
                self.write(cr, uid, invoice.id, vals, context=context)

                # Removes any previous errors associated to this invoice.
                followup_errors_obj.remove_errors(cr, uid, [], [invoice.id], context=context)

                cr.execute("RELEASE SAVEPOINT do_handle_followup;")
            except Exception as e:
                cr.execute("ROLLBACK TO SAVEPOINT do_handle_followup;")
                ids_with_errors.add(invoice.id)
                ids_not_handled.add(invoice.id)

                # Logs in the table of follow-up errors the error that we had.
                followup_errors_obj.create_error_entry(cr, uid, [], invoice.id, format_exception(e), context=context)
                logger.error("Error handling at do_handle_followup, "
                             "Invoice with ID={0}. "
                             "Message: {1}".format(invoice.id, e))

        # Creates the penalization invoices associated to each invoice and
        # associates them to the follow-up.
        for invoice_id in new_ids:
            if invoice_id not in ids_with_errors:
                penalisation_invoice_id = self._create_penalization_invoice(cr,
                                                                            uid,
                                                                            invoice_id,
                                                                            context)
                invoice_obj = self.browse(cr, uid, invoice_id, context=context)
                # Gets the follow-up associated to a given invoice.
                followup_id = followup_model.search(cr, uid,
                                                    [('followup_parent_id', '=', invoice_id),
                                                     ('followup_level_id', '=', invoice_obj.followup_level_id.id)],
                                                    context=context)
                if not followup_id:
                    continue
                if isinstance(followup_id, list):
                    followup_id = followup_id[0]  # An invoice can only have ONE pending follow-up at a given level.
                followup_model.write(cr,
                                     uid,
                                     followup_id,
                                     {'invoice_followup_id': penalisation_invoice_id,
                                      'followup_handled_date': date_today_str},
                                     context=context)

        context['ids_not_handled'] = list(ids_not_handled)
        return reports_printed_ids

    def get_grouped_invoices(self, cr, uid, ids, context=None):
        """Groups invoices by customer and follow-up level.

        Args:
          ids (list of integers): List of invoices to handle.

        Returns:
          list of customers invoices garouped by level

        """
        if context is None:
            context = {}
        if not isinstance(ids, list):
            ids = [ids]

        invoices = []

        for inv in self.browse(cr, uid, ids, context):
            invoice = {}
            invoice['partner_id'] = inv.partner_id.id
            invoice[
                'company_id'] = inv.company_id and inv.company_id.partner_id and inv.company_id.partner_id.id or False
            invoice[
                'followup_level_id'] = inv.followup_level_id and inv.followup_level_id.id or False
            invoice['invoice_id'] = inv.id

            invoices.append(invoice)

        invoices.sort(key=operator.itemgetter('partner_id'), reverse=False)

        invoices_grouped_by_partner = []
        for key, items in itertools.groupby(invoices, operator.itemgetter('partner_id')):
            invoices_grouped_by_partner.append(list(items))

        inv_grouped_by_partner_and_level = []
        for partner_group in invoices_grouped_by_partner:
            partner_group.sort(
                key=operator.itemgetter(
                    'followup_level_id'),
                reverse=False)

            partner_grouped_by_level = []
            for key, items in itertools.groupby(partner_group, operator.itemgetter('followup_level_id')):
                partner_grouped_by_level.append(list(items))

            inv_grouped_by_partner_and_level.append(partner_grouped_by_level)

        return inv_grouped_by_partner_and_level

    def fill_context_with_wildcards(self, cr, uid, values, partner, context=None):
        '''
        This function will apend in the context
        all the values (wildcards) that will be parsed.

        As third parameter a partner object is set due to the future we
        can use its attributes.
        '''
        if context is None:
            context = {}

        if 'wildcards' not in context:
            context['wildcards'] = []
        for value in values:
            context['wildcards'].append((value, values[value]))

    def do_followup_mail(self, cr, uid, ids, context=None):
        """Sends follow-up mail per customer and follow up level.

        Note:
          do_followup_mail should send an mail per customer and follow up level.
          The mail should contain the text defined in follow up level configuration and
          an table with overdue invoices of the corresponding level.

        Args:
          ids (list of integers): List of invoices to handle.

        Returns:
          Empty dictionary if successful, Exception otherwise.!!!!!!!!!!!!!

        """
        if context is None:
            context = {}
        aux_ctx = context.copy()
        aux_ctx['followup'] = True
        send_exception = context.get('exception', True)
        # partner_ids are res.partner ids
        # If not defined by latest follow-up level, it will be
        # the default template if it can find it
        followup_obj = self.pool.get('followup')
        mtp = self.pool.get('email.template')
        res_lang_pool = self.pool.get('res.lang')

        followup_ids = []

        # group invoices by partner and level
        grouped_invoices = self.get_grouped_invoices(cr, uid, ids, context)
        # for each partner and level create one mail with invoices list
        for partner_invoices in grouped_invoices:
            for level_invoices in partner_invoices:

                customer_level_data = []
                ctx = aux_ctx.copy()
                # Level_invoices is list of dictionaries with invoice data
                # send maiInvoicesl for each level_invoices

                for inv in level_invoices:
                    invoice = self.browse(cr, uid, inv['invoice_id'], context)
                    # check if invoice has to be sent
                    if (invoice.followup_level_id and not invoice.followup_level_handled
                        and invoice.followup_level_id.send_email
                            and not invoice.followup_skip_email_sending):
                        customer_level_data.append(inv)

                # if no invoices to send in mail continue with following group
                if len(customer_level_data) == 0:
                    continue

                ctx['customer_level_data'] = customer_level_data
                ctx['default_type'] = 'email'

                mail_id = False

                partner = invoice.partner_id

                # Gets the format for dates according to the res.partner's language.
                partner_lang_date_format = partner.get_partner_date_format()

                if partner.email and partner.email.strip():
                    level = invoice.followup_level_id
                    ctx['ids'] = [invoice.id]
                    if level and level.send_email and level.email_template_id and level.email_template_id.id:
                        # Sets up the wildcards.
                        num_days = level.delay
                        new_due_date = (datetime.datetime.strptime(invoice.date_due, DEFAULT_SERVER_DATE_FORMAT) + datetime.timedelta(num_days)).strftime(partner_lang_date_format)
                        account_number = get_bank_account(self, cr, uid, context=ctx)

                        # Generates the mail.
                        values = {'{new_due_date}': new_due_date,
                                  '{num_days}': num_days,
                                  '{account_number}': account_number,
                                  '{partner_name}': partner.name,
                                  }
                        self.fill_context_with_wildcards(cr, uid, values, partner, context=ctx)
                        mail_id = mtp.send_mail(cr, uid, level.email_template_id.id, invoice.id, context=ctx)

                    else:
                        mail_template_id = self.pool.get('ir.model.data').get_object_reference(cr, uid, 'bt_followup', 'email_template_invoice_followup_default')
                        mail_id = mtp.send_mail(
                            cr,
                            uid,
                            mail_template_id[1],
                            invoice.id,
                            context=ctx)

                    if mail_id:
                        # assign follow up partner to mail
                        self.pool.get('mail.mail').write(cr, uid, mail_id,
                                                         {'followup_partner_id':
                                                             partner.id},
                                                         context=ctx)

                        # add message to invoice that follow-up mail will be
                        # sent for
                        self.message_post(
                            cr, uid, [invoice.id], body=_('Created follow-up mail'), context=ctx)

                        # add message to the partner form
                        self.pool.get('res.partner').message_post(cr, uid,
                                                                  [invoice.partner_id.id], body=_('Created follow-up mail for invoice '
                                                                                                  + invoice.number), context=ctx)

                        for sent_invoice in customer_level_data:
                            # get current followup
                            followup_ids = followup_obj.search(cr, uid,
                                                               [('followup_parent_id', '=', sent_invoice['invoice_id']),
                                                                ('followup_level_id', '=', sent_invoice['followup_level_id'])], context=context)
                            # assign followup mail to current followup (followup.followup_level_id
                            # = invoice.followup_level_id)
                            # of each invoice

                            for followup_id in followup_ids:
                                self.pool.get(
                                    'followup').write(cr, uid, followup_id,
                                                      {'email_id':
                                                       mail_id},
                                                      context=ctx)

                            # assign each parent invoice to followup mail
                            self.write(cr, uid, sent_invoice['invoice_id'],
                                       {'followup_email_ids': [(4, mail_id)]},
                                       context=ctx)

                else:
                    message_error = _(
                        'Following partner has no email address and the corresponding follow-up level includes action "Send Mail": ') + partner.name
                    if not send_exception:

                        write_log(
                            self,
                            cr,
                            uid,
                            'account.invoice',
                            'Follow-up',
                            invoice.id,
                            'Follow-up error',
                            False,
                            message_error)  # False=error.
                        return {}
                    else:

                        raise except_orm(_('Data Error'), message_error)

        return {}

    def do_print_followup_report(self, cr, uid, ids, context=None):
        """Creates follow-up printout in PDF format per customer and follow up level.

        Note:
          Selects invoices that have to be printed and calls a report service.

        Args:
          ids (list of integers): List of invoices with a follow-up report to print.

        Returns:
          The list of ir.attachment's IDs of the reports printed.
        """
        if context is None:
            context = {}
        invoice_to_print_ids = []

        # The IDs of the ir.attachments generated.
        reports_printed_ids = []

        for invoice in self.browse(cr, uid, ids, context):
            if invoice.followup_level_id and (invoice.followup_level_id.send_letter) and (not invoice.followup_level_handled):

                # Adds the current invoice to the list of invoices to print
                invoice_to_print_ids.append(invoice.id)

                # Adds a message to the invoice indicating that a follow-up
                # report was printed.
                self.message_post(cr, uid,
                                  [invoice.id],
                                  body=_('Printed follow-up report for invoice ') + invoice.number,
                                  context=context)

                # Adds a message to the partner indicating that a follow-up
                # report was printed.
                self.pool.get('res.partner').message_post(cr, uid,
                                                          [invoice.partner_id.id],
                                                          body=_('Printed follow-up report for invoice ') + invoice.number,
                                                          context=context)

                # Saves the follow-up report as an attachment, attached to the
                # invoice.
                followup_report = invoice.get_followup_report()
                pdf_data = bt_misc.get_pdf_from_report(
                    cr,
                    uid,
                    followup_report,
                    {'ids': invoice.id,
                     'model': 'account.invoice'},
                    context=context)
                followup_report_name = 'handle_followup_invoice{0}_delay{1}.pdf'.format(
                    invoice.internal_number.replace('/', '-'), invoice.followup_level_id.delay)
                report_printed_id = bt_misc.associate_ir_attachment_with_object(self,
                                                                                cr,
                                                                                uid,
                                                                                pdf_data,
                                                                                followup_report_name,
                                                                                'account.invoice',
                                                                                invoice.id)
                reports_printed_ids.append(report_printed_id)

        return reports_printed_ids

    def get_followup_report(self, cr, uid, ids, context=None):
        """ Allows to overridde the name of the action-report to use to
            generate the report for follow-ups.
        """
        return 'report.invoice_followup_report'

    def do_partner_manual_action(self, cr, uid, invoice_ids, context=None):
        ''' Sets next action, responsible id and next action date for each partner
            in follow up process and sends a message to the responsible person.

            Note:
               Group invoices by partner and follow up level.
               For each partner searches the maximum follow-up level and executes only it.

            Args:
               invoice_ids (list of integers): List of invoices to handle.
        '''
        if context is None:
            context = {}
        if 'do_partner_manual_action_flag' in context:
            return True
        context['do_partner_manual_action_flag'] = True

        def _descendants_have_next_action(cr, uid, partner_id, context=None):
            ''' Checks if any of the descendants of the res.partner have a next action associated to it.
            '''
            if context is None:
                context = {}
            res_partner_pool = self.pool.get('res.partner')
            descendants_ids = res_partner_pool.get_descendants(cr, uid, partner_id, context)
            for descendant_id in descendants_ids:
                descendant_obj = res_partner_pool.browse(cr, uid, descendant_id, context)
                if descendant_obj.followup_payment_next_action and (descendant_obj.followup_payment_next_action.strip() != ''):
                    return True
            return False

        res_partner_pool = self.pool.get('res.partner')
        invoice_pool = self.pool.get('account.invoice')
        followup_level_pool = self.pool.get('followup.level')
        date_today_str = datetime.date.today().strftime('%Y-%m-%d')

        # Gets the invoices of the partner, and all the invoices of its family.
        invoices_to_consider = set()
        for invoice_id in invoice_ids:
            invoice_obj = invoice_pool.browse(cr, uid, invoice_id, context)
            partner_family_ids = res_partner_pool._get_family_partners_ids(cr, uid, invoice_obj.partner_id.id, context)
            invoices_of_family = invoice_pool.search(cr, uid, [('partner_id', 'in', partner_family_ids)], context=context)
            invoices_to_consider = invoices_to_consider.union(invoices_of_family)
        invoices_to_consider = list(invoices_to_consider)

        # Group invoices by partner and level.
        grouped_invoices = self.get_grouped_invoices(cr, uid, invoices_to_consider, context)

        # For each partner, sets (if needed) its manual action.
        for partner_invoices in grouped_invoices:

            max_delay = -1
            followup_payment_next_action = ''
            followup_responsible_id = False
            followup_payment_next_action_date = False

            # Gets the maximum level (maximum delay days) with manual action for this partner
            for level_invoices in partner_invoices:

                invoice_id = level_invoices[0]['invoice_id']
                followup_level_id = level_invoices[0]['followup_level_id']
                if followup_level_id:
                    followup_level = followup_level_pool.browse(cr, uid, followup_level_id, context)
                    invoice_obj = invoice_pool.browse(cr, uid, invoice_id, context)

                    if followup_level.manual_action and (followup_level.delay > max_delay) and (invoice_obj.state == 'open'):
                        max_delay = followup_level.delay
                        followup_payment_next_action_date = date_today_str
                        followup_payment_next_action = followup_level.manual_action_note
                        followup_responsible_id = followup_level.manual_action_responsible_id \
                            and followup_level.manual_action_responsible_id.id or False

            # If manual action is defined, propagates its values.
            # If not, default values will clear out any existing value.
            partner = res_partner_pool.browse(cr, uid, partner_invoices[0][0]['partner_id'], context)
            res_partner_pool.write(cr, uid, [partner.id], {'followup_payment_next_action_date': followup_payment_next_action_date,
                                                           'followup_payment_next_action': followup_payment_next_action.strip(),
                                                           'followup_responsible_id': followup_responsible_id}, context)

        # Once the manual actions have been set for all the partners, warns the parents about its children (if needed)
        # We do this over all the partners of the family tree.
        for partner_invoices in grouped_invoices:
            partner = res_partner_pool.browse(cr, uid, partner_invoices[0][0]['partner_id'], context)
            partner_family_ids = partner._get_family_partners_ids()
            for partner_in_family_id in partner_family_ids:
                partner_in_family = res_partner_pool.browse(cr, uid, partner_in_family_id, context)
                if partner_in_family.child_ids and _descendants_have_next_action(cr, uid, partner_in_family.id, context):
                    if partner_in_family.followup_payment_next_action:
                        warning_message = _('(In addition to this next action, some of his/her children also have next actions to perform.)')
                        if warning_message not in partner_in_family.followup_payment_next_action:
                            parents_followup_payment_next_action = '{0}\n{1}'.format(partner_in_family.followup_payment_next_action, warning_message)
                        else:
                            parents_followup_payment_next_action = partner_in_family.followup_payment_next_action
                    else:
                        parents_followup_payment_next_action = _('(This partner does not have next actions, but some of his/her children do have.)')
                    res_partner_pool.write(cr, uid, partner_in_family.id, {'followup_payment_next_action': parents_followup_payment_next_action}, context)

        if context['do_partner_manual_action_flag']:
            del context['do_partner_manual_action_flag']

        return True

    def __warn_responsibles_of_followup_levels(self, cr, uid, ids, context=None):
        ''' For every res.user which has to do some manual action, an email is sent listing
            the invoices which require a manual action.
        '''
        if context is None:
            context = {}

        res_users_obj = self.pool.get('res.users')
        mail_template_obj = self.pool.get("email.template")
        mail_mail_obj = self.pool.get('mail.mail')
        ir_model_data_obj = self.pool.get('ir.model.data')

        # Gets all res.users which are the responsible of some invoice, and sends him/her an email.
        cr.execute('''SELECT DISTINCT followup_responsible_id
                      FROM account_invoice
                      WHERE state='open'
                      AND followup_level_id IS NOT NULL
                      and followup_responsible_id IS NOT NULL;''')
        res_users_ids = [x[0] for x in cr.fetchall()]

        email_template_id = ir_model_data_obj.get_object_reference(cr, uid, 'bt_followup', 'email_template_warn_user_responsible_of_followups')[1]
        for res_user_id in res_users_ids:
            try:
                values = mail_template_obj.generate_email(cr, uid, email_template_id, res_user_id, context=context)
                mail_mail_obj.create(cr, uid, values, context=context)
            except Exception as e:
                logger.error(format_exception(e))

    def get_manual_action(self, cr, uid, ids, context=None):
        ''' Returns the manual action to be taken by this invoice, or '' if it does not have any.
                This depends on the follow-up level this invoice is under.
        '''
        if context is None:
            context = {}
        if type(ids) is not list:
            ids = [ids]

        manual_action = ''

        invoice = self.browse(cr, uid, ids[0], context=context)
        if invoice.followup_level_id and invoice.followup_level_id.manual_action:
            manual_action = invoice.followup_level_id.manual_action_note

        return manual_action

    # TODO: Consider to remove.
    def propagate_responsible(self, cr, uid, table, field, context=None):
        '''
        This function is overwritten.
        We change responsible for different follow-up processes to the
        company responsible
        '''
        if context is None:
            context = {}
        the_pool = self.pool.get(table)
        for the_item in the_pool.browse(cr, uid, the_pool.search(cr, uid, [], context=context), context=context):
            responsible = self.get_responsible(the_item[field])
            if responsible.id != the_item[field].id:
                the_pool.write(
                    cr,
                    uid,
                    the_item.id,
                    {field: responsible.id},
                    context=context)
        return True

    # TODO: Consider to remove, since the responsible is not the partner, but that indicated in the follow-up level.
    def get_responsible(self, partner):
        '''
        Returns the responsible of the account.invoice
        By default is the partner.
        Take into account that partner is an object of res.partner
        '''
        return partner

    def update_dunning_block_partner(self, cr, uid, date_today, context=None):
        '''
        Updates the dunning block of partners.
        '''
        if context is None:
            context = {}
        partner_ids = self.pool.get(
            "res.partner").search(cr,
                                  uid,
                                  [('dunning_block',
                                   '=',
                                    True),
                                   ('dunning_block_date',
                                   '<',
                                    date_today)],
                                  context=context)
        logger.debug(
            "Updating dunning block of {0} partners".format(partner_ids))
        self.pool.get(
            "res.partner").write(cr,
                                 uid,
                                 partner_ids,
                                 {'dunning_block': False},
                                 context)

    def update_dunning_block_invoices(self, cr, uid, date_today, context):
        # Updates the dunning block of invoices.
        invoices_to_update_ids = self.pool.get(
            "account.invoice").search(cr,
                                      uid,
                                      [('invoice_dunning_block',
                                          '=',
                                          True),
                                          ('dunning_block_ending_date',
                                           '<',
                                           date_today)],
                                      context=context)
        logger.debug(
            "Updating dunning block of {0} invoices".format(invoices_to_update_ids))
        self.write(cr,
                   uid,
                   invoices_to_update_ids,
                   {'invoice_dunning_block': False},
                   context=context)

    def update_dunning_blocks(self, cr, uid, date_today, context):
        self.update_dunning_block_partner(cr, uid, date_today, context=context)
        self.update_dunning_block_invoices(cr, uid, date_today, context=context)

    # TODO: Consider to remove this method.
    def without_followup_level(self, cr, uid, ids, context=None):
        if context is None:
            context
        if not isinstance(ids, list):
            ids = [ids]
        invoice = self.browse(cr, uid, ids[0], context=context)
        return (invoice.followup_level_id is None) or (not invoice.followup_level_id)

    def get_delay(self, invoice, date_str, followup_level):
        if invoice.without_followup_level():
            return True
        else:
            return invoice.followup_level_id.delay < followup_level.delay

    def single_update_followup(self, cr, uid, ids, date_today, followup_levels, context=None):
        ''' Updates the follow-up levels of the invoices. Only the IDs of the invoices which
            are candidates to be updated are received, but that does not mean that they must
            be updated (e.g. it can happen that an invoice qualifies for an update but its
            quantity is zero, thus no follow-up is created).
                Returns the list of IDs of the invoices the follow-up level of which were
            actually updated.
        '''
        if context is None:
            context
        if type(ids) is not list:
            ids = [ids]

        followup_obj = self.pool.get('followup')

        # Stores the IDs of the invoices which were actually updated.
        invoices_updated_ids = []

        # Converts the date of today to a string.
        date_today_str = date_today.strftime(DEFAULT_SERVER_DATETIME_FORMAT)

        # The following structure is used to speed up the process of setting a follow-up level for the invoices.
        # By grouping the follow-up level and making a simultaneous write on several invoinces instead of making a write call
        # per invoice, a speed up of about x7 is gained (when measuring the time in local).
        #    It stores a 2-elements tuple per follow-up level. First element contains the information to be store over each invoice
        # which has the follow-up level applied to it, while the second element contains the list of invoice's ids to apply the level to.
        invoices_to_update_per_followup_level = {}
        for followup_level in followup_levels:
            date_str = (date_today - datetime.timedelta(days=followup_level.delay)).strftime(DEFAULT_SERVER_DATETIME_FORMAT)
            invoices_to_update_per_followup_level[followup_level.id] = [{'followup_level_id': followup_level.id,
                                                                         'followup_level_handled': False,
                                                                         'follow_up_date_due': date_str}, []]

        # Iterates over all the invoices.
        for invoice in self.browse(cr, uid, ids, context=context):

            if (invoice.dunning_block_ending_date is not None) and (invoice.dunning_block_ending_date > date_today_str):
                continue

            # I can happen that the follow_up_date_due is not set. In this case, what happens is that the first time this
            # method is executed over an invoice, its follow-up level is not set (because the next if-sentence ---not this one---
            # does not find the attribute.
            if not hasattr(invoice, 'follow_up_date_due') or not invoice.follow_up_date_due:
                invoice.follow_up_date_due = invoice.date_due
                invoice.write({'follow_up_date_due': invoice.date_due})  #TODO: Remove?

            if invoice.follow_up_date_due and (invoice.follow_up_date_due <= date_today_str) and (invoice.amount_total > 0.0):
                without_followup_level = invoice.without_followup_level()

                # We only consider the invoice if it does not have a follow-up level yet (because it may qualify for a new one)
                # OR if it has a follow-up level and it has been handled (because the next follow-up level may be ready to be applied).
                if without_followup_level or (not without_followup_level and invoice.followup_level_handled):

                    # Looks for the follow-up level to apply to the invoice.
                    for followup_level in followup_levels:
                        date_str = (date_today - datetime.timedelta(days=followup_level.delay)).strftime(DEFAULT_SERVER_DATETIME_FORMAT)
                        if invoice.follow_up_date_due > date_str:
                            continue  # TODO: Remove the continue: get the follow-up level to apply and store it in a variable.

                        if self.get_delay(invoice, date_str, followup_level):
                            invoices_updated_ids.append(invoice.id)  # This invoice will be updated.
                            invoices_to_update_per_followup_level[followup_level.id][-1].append(invoice.id)

                            # Create a follow-up entry on each level change.
                            followup_values = {'followup_create_date': date_today_str,
                                               'followup_level_id': followup_level.id,
                                               'followup_parent_id': invoice.id,
                                               'followup_partner_id': self.get_responsible(invoice.partner_id).id,
                                               }
                            followup_obj.create(cr, uid, followup_values, context=context)
                            break

        # Makes the massive writing.
        for followup_level_key in invoices_to_update_per_followup_level:
            invoice_ids_to_write = invoices_to_update_per_followup_level[followup_level_key][-1]
            if invoice_ids_to_write:
                values_to_store = invoices_to_update_per_followup_level[followup_level_key][0]
                self.write(cr, uid, invoice_ids_to_write, values_to_store, context=context)

        return invoices_updated_ids

    def cron_update_invoice_followup_level(self, cr, uid, context=None):
        """Includes new invoices in follow-up process assigning them a corresponding follow-up level.

        Note:
          Gives to all open, not blocked for follow up, customer invoices and with
          difference(current date, number of delay days) < due date corresponding follow-up level.
          In the context we can set 'active_ids' to update only specific account invoices
        Returns:
          True.

        """
        if context is None:
            context = {}

        # Keeps the date of today, just in case we change day within the
        # execution of this code
        date_today = datetime.date.today()
        logger.debug("Update invoice follow-up level")
        self.update_dunning_blocks(cr, uid, date_today, context=context)

        company_ids = self.pool.get('res.company').search(cr, uid, [], context=context)
        for company_id in company_ids:
            conditions = [('company_id', '=', company_id),
                          ('type', '=', 'out_invoice'),
                          ('state', '=', 'open'),
                          ('dunning_block', '=', False),
                          ]
            if 'active_ids' in context:
                conditions.append(('id', 'in', context['active_ids']))

            invoice_ids = self.search(cr, uid, conditions, context=context)

            followup_config_obj = self.pool.get('followup.config')
            followup_level_obj = self.pool.get('followup.level')
            followup_config_ids = followup_config_obj.search(cr,
                                                             uid,
                                                             [('company_id', '=', company_id)],
                                                             context=context)

            # there is a constraint that do not allow more then one configuration per company
            # so this search will return maximal one config_id
            if followup_config_ids:
                followup_config_id = followup_config_ids[0]
            else:
                logger.warning('You need to configure the follow-up for your company')
                continue

            followup_level_ids = followup_level_obj.search(cr,
                                                           uid,
                                                           [('followup_config_id', '=', followup_config_id), ], context=context,
                                                           order='delay ASC')
            followup_levels = followup_level_obj.browse(cr, uid, followup_level_ids, context=context)

            # TODO: Consider to remove, since I'm not sure if it's correct --- I don't think so.
            self.propagate_responsible(cr, uid, 'followup', 'followup_partner_id', context=context)
            self.propagate_responsible(cr, uid, 'mail.mail', 'followup_partner_id', context=context)

            # We check each open invoice for follow ups.
            invoices_updated_ids = self.single_update_followup(cr, uid, invoice_ids, date_today, followup_levels, context=context)

            # We do the manual action-related stuff only over those invoices which were updated.
            if invoices_updated_ids:
                self.process_manual_action(cr, uid, invoices_updated_ids, followup_levels, context)

        return True

    def process_manual_action(self, cr, uid, invoice_ids, followup_levels, context=None):
        if context is None:
            context = {}

        # Once the follow-up level has been determined, executes the manual action if needed.
        self.do_partner_manual_action(cr, uid, invoice_ids, context)

        # Stores the responsible for each follow-up level, if required.
        # In order to speed up the writing, we do just one writing per follow-up level.
        # (to do that, we use the following structure, which stores a 2-elements tuple per each follow-up level:
        # the first element is the ID of the responsible, while the second one stores the list of invoices which
        # has that follow-up level).
        responsible_id_per_followup_level = {}
        for followup_level in followup_levels:
            followup_responsible_id = False
            if followup_level.manual_action and followup_level.manual_action_responsible_id:
                followup_responsible_id = followup_level.manual_action_responsible_id.id
            responsible_id_per_followup_level[followup_level.id] = ({'followup_responsible_id': followup_responsible_id}, [])
        for invoice in self.browse(cr, uid, invoice_ids, context=context):
            followup_level_id = invoice.followup_level_id.id
            if followup_level_id in responsible_id_per_followup_level:
                responsible_id_per_followup_level[followup_level_id][-1].append(invoice.id)

        # Makes the massive writing using the previous structure.
        for followup_level_key in responsible_id_per_followup_level:
            invoice_ids_to_write = responsible_id_per_followup_level[followup_level_key][-1]
            if invoice_ids_to_write:
                values_to_store = responsible_id_per_followup_level[followup_level_key][0]
                self.write(cr, uid, invoice_ids_to_write, values_to_store, context=context)

        # The manual action may require some action by the responsible. So we warn the responsibles about this.
        if invoice_ids:
            self.__warn_responsibles_of_followup_levels(cr, uid, invoice_ids, context=context)

    def _vals_to_create_penalization_invoice(self, cr, uid, ids, context=None):
        '''
        Helper method for _create_penalization_invoice returning the values to create a penalization invoice
        @rtype: dict
        '''
        if context is None:
            context = {}
        if type(ids) is not list:
            ids = [ids]

        invoice = self.browse(cr, uid, ids[0], context=context)

        # Stores the date of today, just in case it changes during the
        # execution of this method.
        date_today = datetime.date.today()
        return {'name': '{0} {1}'.format(_('Penalization for Unpaid Invoice'), invoice.number),
               'followup_level_id': False,
               'followup_level_date': False,
               'followup_parent_id': invoice.id,
               'dunning_block': False,
               'origin': invoice.number or '',  # invoice.origin or ''
               'type': 'out_invoice',
               'state': 'proforma2',
               'account_id': invoice.account_id.id,
               'journal_id': invoice.journal_id.id,
               'partner_id': invoice.partner_id.id,
               'currency_id': invoice.currency_id.id,
               'date_invoice': date_today.strftime('%Y-%m-%d'),
               'follow_up_date_due':
                   (date_today + datetime.timedelta(
                       days=invoice.followup_level_id.delay)).strftime(
                           '%Y-%m-%d'),
               'date_due':
                   (date_today + datetime.timedelta(
                       days=invoice.followup_level_id.delay)).strftime(
                           '%Y-%m-%d'),
               'user_id': invoice.user_id.id,
               'payment_term':
                   invoice.payment_term and invoice.payment_term.id or False,
               'fiscal_position':
                   invoice.partner_id.property_account_position.id,
               }

    def _create_penalization_invoice(self, cr, uid, invoice_id, context=None):
        """Creates a pro-forma penalisation invoice.

        Note:
          do_followup_mail should send an mail per customer and follow up level.
          The mail should contain the text defined in follow up level configuration and
          an table with overdue invoices of the corresponding level.

        Args:
          ids (list of integers): List of invoices to handle.

        Returns:
          Empty dictionary if successful, Exception otherwise.!!!!!!!!!!!!!

        """
        if context is None:
            context = {}
        # Stores the date of today, just in case it changes during the
        # execution of this method.
        date_today = datetime.date.today()

        invoice_line_obj = self.pool.get('account.invoice.line')
        invoice_obj = self.pool.get('account.invoice')

        invoice = self.browse(cr, uid, invoice_id, context=context)
        new_invoice_id = False

        if invoice.followup_level_id.product_id:

            if invoice.followup_level_id.product_id.list_price:

                # account_id =
                # invoice.partner_id.property_account_receivable.id
                inv_vals = invoice._vals_to_create_penalization_invoice()
                new_invoice_id = invoice_obj.create(cr, uid, inv_vals, context=context)

                if invoice.followup_level_id.product_id.property_account_income:
                    account_id = invoice.followup_level_id.product_id.property_account_income.id
                elif invoice.followup_level_id.product_id.categ_id.property_account_income_categ:
                    account_id = invoice.followup_level_id.product_id.categ_id.property_account_income_categ.id

                invoice_line_values = {
                    'product_id': invoice.followup_level_id.product_id.id,
                    'name': invoice.followup_level_id.product_id.name,
                    'quantity': 1,
                    'uos_id': False,
                    'price_unit':
                        invoice.followup_level_id.product_id.list_price,
                    'discount': 0,
                    'account_id': account_id,
                    'account_analytic_id':
                        invoice.company_id.followup_analytic_account_id and invoice.company_id.followup_analytic_account_id.id or False,
                    'invoice_id': new_invoice_id,
                }

                invoice_line_obj.create(
                    cr,
                    uid,
                    invoice_line_values,
                    context=context)

        return new_invoice_id

    def get_logo_bt_followup(self, cr=None, uid=None, ids=None, context=None):
        """Returns report_logo image.

        Note:
          if no webkit logo with name "report_logo" introduced, the report will
          be printed too

        Args:
          ids (list of integers): List of invoices to handle.

        Returns:
          report_logo image, &nbsp; otherwise.!!!!!!!!!!!!!

        """
        helper = report_helper.WebKitHelper(
            cr,
            uid,
            "followup_rml_parser",
            context=context)
        try:
            image = helper.embed_logo_by_name('report_logo')
        except:
            image = '''<span>&nbsp;</span>'''

        return image

    def get_invoice_followup_table_html(self, cr, uid, ids, context=None):
        """Returns the html table with all invoices in ids

        Note:
          Build the html table with invoice to follow up to be included
          in email send to partners in invoice follow up process.

        Args:
          ids: [id] of the invoice to follow up.

        Returns:
          html table
        """
        assert len(ids) == 1
        if context is None:
            context = {}

        partner = self.pool.get(
            'account.invoice').browse(cr,
                                      uid,
                                      ids[0],
                                      context=context).partner_id

        context = dict(context, lang=partner.lang)

        company = self.pool.get(
            'res.users').browse(cr,
                                uid,
                                uid,
                                context=context).company_id

        followup_table = '''
                <table width=100%%  style="font-size:8pt;border-collapse:collapse;">
                <tr>
                    <td style="border-top: solid 1px #000; border-bottom: solid 1px #000;padding-top:5px; padding-bottom:5px;">''' + _("Invoice No.") + '''</td>
                    <td style="border-top: solid 1px #000; border-bottom: solid 1px #000;padding-top:5px; padding-bottom:5px;">''' + _("Date") + '''</td>
                    <td style="border-top: solid 1px #000; border-bottom: solid 1px #000;padding-top:5px; padding-bottom:5px;">''' + _("Due Date") + '''</td>
                    <td style="border-top: solid 1px #000; border-bottom: solid 1px #000;padding-top:5px; padding-bottom:5px;">''' + _("Amount") + " (%s)" % (company.currency_id.symbol) + '''</td>
                    <td style="border-top: solid 1px #000; border-bottom: solid 1px #000;padding-top:5px; padding-bottom:5px;">''' + _("Unpaid") + " (%s)" % (company.currency_id.symbol) + '''</td>
                    <td style="border-top: solid 1px #000; border-bottom: solid 1px #000;padding-top:5px; padding-bottom:5px;">''' + _("Dunning Level") + '''</td>
                    <td style="border-top: solid 1px #000; border-bottom: solid 1px #000;padding-top:5px; padding-bottom:5px;">''' + _("Dunning Charge") + '''</td>
                    <td style="border-top: solid 1px #000; border-bottom: solid 1px #000;padding-top:5px; padding-bottom:5px;">''' + _("Total") + '''</td>
                </tr>'''

        total = 0
        for inv_id in ids:

            invoice = self.pool.get('account.invoice').browse(cr, uid, inv_id,
                                                              context)

            penalization_total = 0
            for penalization_invoice in invoice.followup_penalization_invoice_ids:
                penalization_total += penalization_invoice.amount_total

            followup_total = penalization_total + invoice.residual

            total = total + followup_total

            from .report import invoice_followup_report
            rml_parse = invoice_followup_report.invoice_followup_report(
                cr, uid, "followup_rml_parser", context=context)

            # todo get currency from invoice
            followup_table += '''
                    <tr>
                        <td style="padding-top:5px; padding-bottom:5px;">''' + (invoice.number or '-') + '''</td>
                        <td style="padding-top:5px; padding-bottom:5px;">''' + (invoice.date_invoice or '-') + '''</td>
                        <td style="padding-top:5px; padding-bottom:5px;">''' + (invoice.date_due or '-') + '''</td>
                        <td style="padding-top:5px; padding-bottom:5px;">''' + rml_parse.formatLang(invoice.amount_total) + '''</td>
                        <td style="padding-top:5px; padding-bottom:5px;">''' + rml_parse.formatLang(invoice.residual) + '''</td>
                        <td style="padding-top:5px; padding-bottom:5px;">''' + (invoice.followup_level_id.name or '-') + '''</td>
                        <td style="padding-top:5px; padding-bottom:5px;">''' + rml_parse.formatLang(penalization_total) + '''</td>
                        <td style="padding-top:5px; padding-bottom:5px;">''' + rml_parse.formatLang(followup_total) + '''</td>
                    </tr>
                    '''

        currency = invoice.currency_id.symbol if invoice.currency_id else ''
        followup_table += '''

                        <tr>
                            <td colspan = "7"  style="border-top: solid 1px #000;font-size:8pt;padding-top:5px;">''' + _("Total") + '''</td>
                            <td  style="border-top: solid 1px #000;font-size:8pt;padding-top:5px;" >''' + rml_parse.formatLang(total) + '''&nbsp;''' + currency + '''</td>
                        </tr>
                </table>
                '''

        return followup_table

    def send_email_to_followup_responsible(self, cr, uid, responsible, invoice, context=None):
        if context is None:
            context = {}
        mail_message_obj = self.pool.get('mail.mail')
        ir_attachment_obj = self.pool.get('ir.attachment')

        email_to = self.pool.get(
            'res.users').browse(cr,
                                uid,
                                responsible,
                                context=context).email
        email_from = self.pool.get(
            'res.users').browse(cr,
                                uid,
                                uid,
                                context=context).email
        subject = 'Invoice FollowUp Reminder Email'

        data_to_send = 'Invoice that needs manual handling is \n' + \
            invoice.number

        attachment_data = {
            'name': 'Invoice Followup Handle Reminder',
                    'datas_fname': 'Followup_Information.txt',
                    'datas': base64.b64encode(data_to_send),
                    'res_model': None,
                    'res_id': None,
        }
        attachment_ids = [
            ir_attachment_obj.create(
                cr,
                uid,
                attachment_data,
                context=context)]

        msg_id = mail_message_obj.create(cr,
                                         uid,
                                         {'subject': subject,
                                          'email_from': email_from,
                                          'email_to': email_to,
                                          'subject': subject,
                                          'body_html':
                                              "There is an invoice that needs followup manual handling",
                                          'model': '',
                                          'auto_delete': True,
                                          # 'subtype':'html',
                                          },
                                         context=context)
        mail_message_obj.write(
            cr, uid, msg_id, {'attachment_ids': [(6, 0, attachment_ids)]}, context=context)

        mail_message_obj.send(cr, uid, [msg_id], context=context)
        logger.debug('send invoice handle folloup reminder email')
        return True

    # MAKO FILE FUNCTIONS

    def get_email_from(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        if not isinstance(ids, list):
            ids = [ids]
        if not ids:
            raise except_orm(_('Error'),
                             _('We must receive an invoice'))
        invoice_obj = self.pool.get(
            'account.invoice').browse(cr,
                                      uid,
                                      ids,
                                      context=context)[0]
        if not invoice_obj.partner_id:
            raise except_orm(_('Error'),
                             _('The invoice should have a partner'))
        if not invoice_obj.partner_id.email:
            raise except_orm(_('Error'),
                             _('The partner should contain an email'))
        return invoice_obj.partner_id.email

    def get_partner_email(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        if not isinstance(ids, list):
            ids = [ids]
        if not ids:
            raise except_orm(_('Error'),
                             _('We must receive an invoice'))
        invoice_obj = self.browse(cr, uid, ids, context)[0]
        if not invoice_obj.partner_id:
            raise except_orm(_('Error'),
                             _('The invoice should have a partner'))
        if not invoice_obj.partner_id.email:
            raise except_orm(_('Error'),
                             _('The partner should contain an email'))
        return invoice_obj.partner_id.email

    def get_lang(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        if not isinstance(ids, list):
            ids = [ids]
        if not ids:
            raise except_orm(_('Error'),
                             _('We must receive an invoice'))
        invoice_obj = self.pool.get(
            'account.invoice').browse(cr,
                                      uid,
                                      ids,
                                      context=context)[0]
        return invoice_obj.partner_id.lang

    _constraints = [(do_partner_manual_action, _('Updating the fields related with the manual action failed.'), ['state']),
                    ]

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
