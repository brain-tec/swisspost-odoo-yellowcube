# b-*- encoding: utf-8 -*-
##############################################################################
#
#    Copyright (c) 2014 brain-tec AG (http://www.braintec-group.com)
#    Copyright (c) 2017 Camptocamp SA (https://www.camptocamp.com)
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

from openerp.osv import osv, orm, fields
from openerp.tools import float_compare
from openerp.tools import DEFAULT_SERVER_DATETIME_FORMAT
from openerp.tools.translate import _
from utilities import filters
from datetime import datetime
from utilities.others import format_exception


_INVOICE_ROUTING = [
    ('default', 'Default'),
    ('email', 'Email'),
    ('docout', 'Doc-out'),
    ('pfgateway', 'PostFinance Email Gateway'),
]


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

    def is_epaid(self, cr, uid, ids, context=None):
        """ Returns whether an invoice was epaid.
        """
        if context is None:
            context = {}
        if type(ids) is not list:
            ids = [ids]

        invoice = self.browse(cr, uid, ids[0], context=context)
        return bool(
            invoice.sale_ids and
            invoice.sale_ids[0].payment_method_id and
            invoice.sale_ids[0].payment_method_id.epayment) or False

    def show_bvr(self, cr, uid, ids, context=None):
        """ Returns whether the BVR has to be shown for the invoice, in
            the case it's printed, or if it should be for instance
            voided with XXXs.
        """
        if context is None:
            context = {}
        if type(ids) is not list:
            ids = [ids]

        conf = self.pool.get('configuration.data').\
            get(cr, uid, [], context=context)

        invoice = self.browse(cr, uid, ids[0], context=context)

        # Gets if the invoice has a bank account and it is of type BVR.
        has_bank_account_type_bvr = \
            invoice.partner_bank_id and \
            invoice.partner_bank_id.state in ('bvr', 'iban')

        # Gets if the invoice was e-payed.
        epayment = invoice.is_epaid()

        # Gets the condition refering to the state:
        # we don't show BVRs for invoices which are paid EXCEPT if its
        # amount was zero, because in that case after validating it, it's set
        # to paid automatically.
        state_condition = (invoice.state == 'open') or \
                          (invoice.state == 'paid' and
                           invoice.amount_total == 0.0)

        show = bool(has_bank_account_type_bvr and \
                    state_condition and \
                    not epayment and \
                    (invoice.amount_total > 0.0 or
                     conf.invoice_report_show_bvr_when_zero_amount_total))

        return show

    def apply_gift_cards(self, cr, uid, ids, context=None):
        """ Creates a drop-payment for the invoice, one per each gift-card
            associated to the sale order which originated the invoice.
        """
        if context is None:
            context = {}
        if type(ids) is not list:
            ids = [ids]

        gift_card_obj = self.pool.get('gift.card')

        for inv in self.browse(cr, uid, ids, context=context):

            # Gets all the gift cards to apply to the current invoice.
            order_ids = [order.id for order in inv.sale_ids]
            gift_card_ids = gift_card_obj.search(
                cr, uid, [('sale_order_id', 'in', order_ids)], context=context)

            for gift_card in gift_card_obj.browse(
                    cr, uid, gift_card_ids, context=context):
                inv.apply_gift_card(gift_card)

        return True

    def apply_gift_card(self, cr, uid, ids, gift_card, context=None):
        """ Applies a gift-card to an invoice, creating a drop-down payment
            for it. This method basically emulates what happens when you
            press the button 'Register Payment' from an invoice.
        :param cr: 
        :param uid: 
        :param ids: 
        :param gift_card: 
        :param context: 
        :return: 
        """
        if context is None:
            context = {}
        if type(ids) is not list:
            ids = [ids]

        def get_account_type(ttype):
            """ This portion of code was extracted & adapted from the one
                in addons/account_voucher/account_voucher.py, in the method
                recompute_voucher_lines()
            """
            acc_type = None
            if context.get('account_id'):
                acc_type = self.pool['account.account'].browse(
                    cr, uid, context['account_id'], context=context).type
            if ttype == 'payment' and not acc_type:
                acc_type = 'payable'
            elif not acc_type:
                acc_type = 'receivable'
            return acc_type

        move_line_obj = self.pool.get('account.move.line')
        voucher_obj = self.pool.get('account.voucher')
        conf_data = self.pool.get('configuration.data').\
            get(cr, uid, False, context=context)

        gift_journal_id = conf_data.gift_card_journal_id and \
                          conf_data.gift_card_journal_id.id
        gift_date = gift_card.date
        gift_amount = gift_card.amount

        if not gift_journal_id:
            raise orm.except_orm(
                _("Journal for gift cards missing"),
                _("A journal has to be selected in the configuration to "
                  "be applied for gift-cards' payments."))

        for inv in self.browse(cr, uid, ids, context=context):
            currency_id = inv.currency_id.id
            company_id = inv.company_id.id

            vals = inv.invoice_pay_customer()['context']
            vals.update({
                'comment': _('Gift card {0}'.format(gift_card.name)),
            })

            # We have to pass the account.moves of the invoice, because
            # otherwise the code of recompute_voucher_lines() from the
            #  module account_voucher won't be called only over the move.lines
            # of the provided invoice, but over all the account.moves of
            # all the invoices of the partner when the on-change is called.
            # The following block of code was extracted & adapted from the one
            # in addons/account_voucher/account_voucher.py, in the method
            # recompute_voucher_lines(), to determine the account.move.lines
            # that have to be taken into account. I added the option to filter
            # by invoice.
            account_type = get_account_type(vals['default_type'])
            move_line_ids = move_line_obj.search(cr, uid, [
                ('state','=','valid'),
                ('account_id.type', '=', account_type),
                ('reconcile_id', '=', False),
                ('partner_id', '=', vals['default_partner_id']),
                ('invoice', '=', inv.id),
            ], context=context)

            gift_context = context.copy()
            gift_context.update({
                'active_id': inv.id,
                'active_ids': [inv.id],
                'active_model': 'account.invoice',
                'invoice_id': inv.id,
                'journal_type': 'sale',
                'move_line_ids': move_line_ids,
            })

            vals.update(
                voucher_obj.onchange_partner_id(
                    cr, uid, ids=[],
                    partner_id=vals['default_partner_id'],
                    journal_id=gift_journal_id, amount=gift_amount,
                    currency_id=currency_id,
                    ttype=vals['default_type'],
                    date=gift_date, context=gift_context)['value']
            )

            vals.update(
                voucher_obj.onchange_date(
                    cr, uid, ids=[], date=gift_date,
                    currency_id=vals['currency_id'],
                    payment_rate_currency_id=vals['payment_rate_currency_id'],
                    amount=gift_amount, company_id=company_id,
                    context=gift_context)['value']
            )

            vals.update(
                voucher_obj.onchange_amount(
                    cr, uid, ids=[],
                    amount=gift_amount, rate=vals['payment_rate'],
                    partner_id=vals['default_partner_id'],
                    journal_id=gift_journal_id,
                    currency_id=vals['currency_id'],
                    ttype=vals['default_type'], date=gift_date,
                    payment_rate_currency_id=vals['payment_rate_currency_id'],
                    company_id=company_id, context=gift_context)['value']
            )

            vals.update(
                voucher_obj.onchange_journal(
                    cr, uid, ids=[], journal_id=gift_journal_id, line_ids=[],
                    tax_id=False, partner_id=vals['default_partner_id'],
                    date=gift_date, amount=gift_amount,
                    ttype=vals['default_type'],
                    company_id=company_id, context=gift_context)['value']
            )

            gift_context.update(vals)
            del gift_context['line_cr_ids']

            line_cr_ids = vals.pop('line_cr_ids')
            vals['line_cr_ids'] = [(5, False, False)]
            for line_cr_id in line_cr_ids:
                vals['line_cr_ids'].append((0, False, line_cr_id))

            line_dr_ids = vals.pop('line_dr_ids')
            vals['line_dr_ids'] = [(5, False, False)]
            for line_dr_id in line_dr_ids:
                vals['line_dr_ids'].append((0, False, line_dr_id))

            vals.update({
                'account_id': inv.account_id.id,
                'analytic_id': False,
                'comment': 'Write-Off',
                'company_id': inv.company_id.id,
                'date': gift_card.date,
                'is_multi_currency': False,
                'journal_id': gift_journal_id,
                'name': gift_card.name,
                'narration': False,
                'payment_option': 'without_writeoff',
                'reference': False,
                'writeoff_acc_id': False,
                'partner_id': vals['default_partner_id'],
                'amount': gift_amount,
                'currency_id': vals['payment_expected_currency'],
            })

            voucher_id = voucher_obj.create(
                cr, uid, vals, context=gift_context)
            voucher_obj.button_proforma_voucher(
                cr, uid, [voucher_id], context=gift_context)

        return True

    def refund(self, cr, uid, ids, date=None, period_id=None, description=None, journal_id=None, context=None):
        """ Extended so that we keep track of the invoice which was refunded.
        """
        if context is None:
            context = {}

        account_invoice_obj = self.pool.get('account.invoice')

        new_ids = super(account_invoice_ext, self).refund(cr, uid, ids, date=date, period_id=period_id,
                                                          description=description, journal_id=journal_id, context=context)

        refunded_invoice_id = context.get('refunded_invoice_id', False)
        if refunded_invoice_id:
            for invoice_id in new_ids:
                account_invoice_obj.write(cr, uid, invoice_id, {'refunded_invoice_id': refunded_invoice_id}, context=context)

        return new_ids

    def is_last_invoice(self, cr, uid, ids, context=None):
        """ Indicates whether an invoice is the last one that was created for
            a given sale order.

            This method MUST receive just an ID, or a list of just
            one ID, since otherwise just the first element will be used.
        """
        if context is None:
            context = {}
        if type(ids) is not list:
            ids = [ids]

        invoice = self.browse(cr, uid, ids[0], context=context)
        is_last_invoice = False

        if invoice.picking_id:
            # If this invoice comes from the sale order automation, then
            # it'll have field picking_id set, and this is the most reliable
            # way of determining if this is the last invoice according
            # to the automation: to check if this invoice comes from
            # a picking which is not a back-order.
            is_last_invoice = not bool(invoice.picking_id.backorder_id)

        else:
            # We have to search for all the invoices associated to the same
            # origin sale.order and pick the one which was created the
            # last one. If the automation works the way it's intended,
            # with this check it would be enough unless a manual intervention
            # is done (something that we can not discard).
            last_invoice_id = self.search(cr, uid, [
                ('state', '!=', 'cancel'),
                ('id', 'in', [invoice.id for invoice in
                              invoice.sale_ids[0].invoice_ids]),
            ], context=context, order='create_date desc', limit=1)
            if last_invoice_id:
                is_last_invoice = last_invoice_id[0] == invoice.id

        return is_last_invoice

    def update_invoice_lines_from_picking(self, cr, uid, ids, picking, context=None):
        """ Receives a picking object and updates the lines of the invoice with
            the content of the lines of the picking. This can only be done if the
            invoice is in state draft.

            This method expects just one ID.
        """
        if context is None:
            context = {}
        if type(ids) is not list:
            ids = [ids]

        invoice_line_obj = self.pool.get('account.invoice.line')
        stock_picking_obj = self.pool.get('stock.picking')

        invoice = self.browse(cr, uid, ids[0], context=context)

        # First, checks that the invoice is in state draft, since otherwise the invoices can not be updated.
        if invoice.state != 'draft':
            raise orm.except_orm(_("Invoice is not in state draft"),
                                 _("The invoice with ID={0} is not in state draft, thus its lines can not be updated.").format(invoice.id))

        for picking_line in picking.move_lines:
            if picking_line.state != 'cancel' and not picking_line.scrapped:

                # Searches for those invoice's lines which contain this product. For a match
                # to happen, it must have the same product with the same UOM, unit price and taxes.
                # If there is no match, creates a new invoice line.
                invoice_line_ids = invoice_line_obj.search(cr, uid, [('invoice_id', '=', invoice.id),
                                                                     ('product_id', '=', picking_line.product_id.id),
                                                                     ('uos_id', '=', picking_line.product_uom.id),
                                                                     ], limit=1, context=context)

                if invoice_line_ids:
                    # We update the current picking line.
                    invoice_line = invoice_line_obj.browse(cr, uid, invoice_line_ids[0], context=context)
                    invoice_line.write({'quantity': invoice_line.quantity + picking_line.product_qty})
                else:
                    # We create a new invoice line and add it to the existing invoice.
                    # This is inspired by addons/stock/stock.py, method action_invoice_create.
                    group_invoice = False  # We want to do things ourselves in this case.
                    invoice_vals = stock_picking_obj._prepare_invoice(cr, uid, picking, invoice.partner_id, invoice.type, invoice.journal_id, context=context)
                    invoice_line_vals = stock_picking_obj._prepare_invoice_line(cr, uid, group_invoice, picking, picking_line, invoice.id, invoice_vals, context=context)
                    if invoice_line_vals:
                        invoice_line_id = invoice_line_obj.create(cr, uid, invoice_line_vals, context=context)
                        stock_picking_obj._invoice_line_hook(cr, uid, picking_line, invoice_line_id)

        return True

    def invoice_validate(self, cr, uid, ids, context=None):
        """ When an invoice is validated, it checks if any of its products has a cost price
            which has to be computed every time an incoming invoice which contains it
            is validated, because of the average-price option.
        """
        if context is None:
            context = {}
        if type(ids) is not list:
            ids = [ids]

        # Update the average prices of products.
        for invoice in self.browse(cr, uid, ids, context=context):
            for invoice_line in invoice.invoice_line:
                invoice_line._update_average_price_because_of_invoice()

        result = super(account_invoice_ext, self).invoice_validate(cr, uid, ids, context)
        return result

    def requires_rounding(self, cr, uid, ids, context=None):
        ''' Returns whether an invoice requires to be rounded to the Swiss rounding.
            This can happen when its amount is already rounded.

            This method must be called over just one ID.
        '''
        if context is None:
            context = {}
        if type(ids) is not list:
            ids = [ids]

        invoice = self.browse(cr, uid, ids[0], context=context)

        # Invoices without tax lines can not be rounded because of the
        # method change_rounding() in bt_account.
        if not invoice.tax_line:
            do_rounding = False

        else:
            # Computes the quantity rounded, according to the
            # Swiss 0.00 or 0.05 rounding.
            amount_total_rounded = 0.00
            currency_obj = self.pool.get('res.currency')
            currency_round_ids = currency_obj.search(cr, uid, [
                ('name', '=', 'CH5'),
                ('active', '=', False),
            ], limit=1, context=context)
            if currency_round_ids:
                currency_round = currency_obj.browse(
                    cr, uid, currency_round_ids[0], context=context)
                amount_total_rounded = currency_obj.round(
                    cr, uid, currency_round, invoice.amount_total)

            invoice_already_rounded = \
                (invoice.amount_total - amount_total_rounded) == 0

            do_rounding = not invoice_already_rounded

        return do_rounding

    def get_file_name(self, cr, uid, ids, context=None):
        ''' Returns a unique file name for this invoice.
        '''
        if context is None:
            context = {}
        if type(ids) is not list:
            ids = [ids]
        account_invoice = self.browse(cr, uid, ids[0], context=context)
        file_name = 'invoice_{0}_inv{1}.pdf'.format(account_invoice.origin or '', account_invoice.id)
        return file_name

    def is_printed(self, cr, uid, ids, context=None):
        ''' Returns if we have printed the attachment for this invoice.
        '''
        if context is None:
            context = {}
        if type(ids) is not list:
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
        """ Sends the invoices to the partner, by email.
        """
        if context is None:
            context = {}

        ctx = context.copy()

        # Gets the email template to use to send the invoices to the partner.
        # If no email template is indicated, then no invoices are sent.
        configuration_data = self.pool.get('configuration.data').get(cr, uid, None, ctx)
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
            account_invoice_ids = account_invoice_obj.search(cr, uid, [('send_invoice_to_partner', '=', 'to_send')], context=ctx)
            for account_invoice in account_invoice_obj.browse(cr, uid, account_invoice_ids, context=ctx):

                # Gets the name of the attachment of the invoice.
                file_name = account_invoice.get_file_name(context=ctx)

                # Gets the ir.attachment
                ir_attachment_ids = ir_attachment_obj.search(cr, uid, [('res_model', '=', 'account.invoice'),
                                                                       ('res_id', '=', account_invoice.id),
                                                                       ('name', '=', file_name)], context=ctx)

                # Generates the email from the template and adds the attachment.
                if ir_attachment_ids:
                    try:
                        ctx['lang'] = account_invoice.partner_id.lang or False  # If the template has a language indicated, it's taken from there instead.
                        values = mail_template_obj.generate_email(cr, uid, invoice_to_partner_email_template.id, account_invoice.id, context=ctx)
                        msg_id = mail_mail_obj.create(cr, uid, values, context=ctx)
                        mail_mail_obj.write(cr, uid, msg_id, {'attachment_ids': [(6, 0, ir_attachment_ids)]}, context=ctx)
                        successfully_sent_invoice_ids.append(account_invoice.id)

                    except Exception as e:
                        issue_ids = project_issue_obj.find_resource_issues(cr, uid, 'account.invoice', account_invoice.id, tags=['partner'], create=True, reopen=True, context=ctx)
                        error_message = _('Account.invoice with ID={0} could not be sent to the partner: {1}').format(account_invoice.id, format_exception(e))
                        for issue_id in issue_ids:
                            project_issue_obj.message_post(cr, uid, issue_id, error_message, context=ctx)

            # Only those invoices correctly sent are marked as sent.
            self.write(cr, uid, successfully_sent_invoice_ids, {'send_invoice_to_partner': 'sent'}, context=ctx)

        return True

    def get_salutation(self, cr, uid, ids, context=None):
        ''' Returns a salutation for templates.
            The salutation is different depending on if the res.partner is company, has known gender, etc.
        '''
        if context is None:
            context = {}

        if type(ids) is list:
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
        'create_date': fields.datetime('Create Date'),  # Create Date of the record. Redefined just to allow a sorting on a search() call.'

        'picking_id': fields.many2one(
            'stock.picking.out', 'Picking',
            help='The stock.picking.out this invoice comes '
                 'from (if known).', select=True),

        'refunded_invoice_id': fields.many2one('account.invoice', 'Refunded Invoice', help='The invoice this one was refunded from.'),

        'backorder_items_for_invoice_ids': fields.many2many('pc_sale_order_automation.product_pending',
                                                            rel='backorder_items_for_invoice',
                                                            id1='invoice_id', id2='product_pending_id'),

        # Fields for the automation of the invoices.
        'automate_invoice_process': fields.boolean(
            'Automate Invoice Process',
            help='Indicates if the invoice has to be automated using the '
                 'Account Invoice Automation'),
        'automation_finished': fields.boolean(
            'Has Automation Finished?',
            help='Indicates if the Invoice Automation has reached its last '
                 'state and finished.'),
        'automate_invoice_process_fired': fields.boolean(
            'Automate Invoice Process Was Fired',
            help='Non visible field. It indicates if the Account Invoice '
                 'Automation was fired. This  will help us determine if it '
                 'was fired in the past and, if so, prevent a second '
                 'automation over the same invoice. May never be used.'),
        'invoice_routing': fields.selection(
            _INVOICE_ROUTING, string='Invoice Routing',
            help='Indicates where to send the invoice when being automated '
                 'through the Invoice Automation.'),
        'payment_method_id': fields.many2one(
            'payment.method', 'Payment Method', ondelete='restrict',
            help='This is only filled in if the Account.Invoice Automation is '
                 'used, since it is the payment method set on the invoice by '
                 'the external system that sends the invoice.'),

        # The following two fields are for the automation of the invoices also,
        # but if the automation of orders ir running it will take the values
        # from the sale.order instead.
        'carrier_id': fields.many2one(
            'delivery.carrier', 'Carrier',
            states={'done': [('readonly', True)]}),
        'shop_id': fields.many2one(
            'sale.shop', 'Shop',
            states={'done': [('readonly', True)]}),

        # Fields for the new reports required for PF.
        # Of course would have been better to have just a text field and split
        # it into lines according to their returns and then using a constraint
        # but... there were requested three separated titles.
        'title1': fields.char(
            'Title for the PF Report (1st line)',
            help='The title for the invoice report used in PF, 1st line.'),
        'title2': fields.char(
            'Title for the PF Report (2nd line)',
            help='The title for the invoice report used in PF, 2nd line.'),
        'title3': fields.char(
            'Title for the PF Report (3rd line)',
            help='The title for the invoice report used in PF, 3rd line.'),

        'client_invoice_ref': fields.char("Client Invoice Ref"),
    }

    _defaults = {
        'send_invoice_to_partner': 'not_applicable',

        # Fields for the automation of the invoices.
        'automate_invoice_process': False,
        'automation_finished': False,
        'automate_invoice_process_fired': False,
        'invoice_routing': 'default',
    }

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
