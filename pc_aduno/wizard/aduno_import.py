# -*- encoding: utf-8 -*-
##############################################################################
#
#    Author: Nicolas Bessi. Copyright Camptocamp SA
#    Donors: Hasa Sàrl, Open Net Sàrl and Prisme Solutions Informatique SA
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
import base64
import time
import re

from openerp.tools.translate import _
from openerp.osv import osv, fields
from openerp import pooler

from datetime import datetime, timedelta


def _reconstruct_invoice_ref(cr, uid, reference, context=None):
    """
    This method takes a transaction reference, and returns
     the associated invoice lines
    """
    invoice_id = False
    user_obj = pooler.get_pool(cr.dbname).get('res.users')
    user_current = user_obj.browse(cr, uid, uid)

    # First: We search for the transaction_id of the open invoices
    cr.execute("SELECT inv.id, transaction_id "
               "from account_invoice AS inv "
               "where inv.company_id = %s "
               "and state = 'open' "
               "and type = 'out_invoice' "
               "ORDER BY inv.id DESC", (user_current.company_id.id, ))

    result_invoice = cr.fetchone()
    while(result_invoice and not invoice_id):
        inv_id, transaction_id = result_invoice
        if transaction_id:
            transaction_id = re.sub('[^0-9]', '', transaction_id)

        if transaction_id == reference:
            invoice_id = inv_id
        else:
            result_invoice = cr.fetchone()

    # Second: We return the move lines of that invoice
    if invoice_id:
        cr.execute('SELECT l.id '
                   'FROM account_move_line l '
                   'INNER JOIN account_invoice i '
                   'ON l.move_id = i.move_id '
                   'WHERE l.reconcile_id is NULL '
                   'AND i.id = %s order by date_maturity', (invoice_id, ))
        inv_line = [x[0] for x in cr.fetchall()]
        return inv_line
    else:
        return []


def _get_account(self, cursor, uid, line_ids, record, context=None):
    """Get account from move line or from property"""
    property_obj = self.pool.get('ir.property')
    move_line_obj = self.pool.get('account.move.line')

    for line in move_line_obj.browse(cursor, uid, line_ids, context=context):
        return line.account_id.id

    name = "property_account_receivable"
    if record['amount'] < 0:
        name = "property_account_payable"
    account_id = property_obj.get(cursor, uid, name, 'res.partner', context=context)
    if account_id:
        return account_id.id
    raise osv.except_osv(_('Error'),
                         _('The properties account payable account receivable are not set'))


# Here we read the imported Aduno file to reconcile
def _import(self, cr, uid, data, context=None):
    if context is None:
        context = {}

    statement_line_obj = self.pool.get('account.bank.statement.line')
    voucher_obj = self.pool.get('account.voucher')
    voucher_line_obj = self.pool.get('account.voucher.line')
    move_line_obj = self.pool.get('account.move.line')
    attachment_obj = self.pool.get('ir.attachment')
    statement_obj = self.pool.get('account.bank.statement')
    property_obj = self.pool.get('ir.property')
    invoice_obj = self.pool.get('account.invoice')

    _file = data['form']['file']
    if not _file:
        raise osv.except_osv(_('UserError'),
                             _('Please select a file first!'))

    statement_id = data['id']
    statement = statement_obj.browse(cr, uid, statement_id, context=context)

    records = []
    total_amount = 0
    total_commission = 0
    found_total = False
    # Konto Abschreibungen 420: Sonstige betriebliche Aufwendungen und Abschreibungen: ID 1582
    # account_writeoff_id = 800 #6920
    # TODO set correct account!!!
    # mica1 account_writeoff_id = self.pool.get('res.users').browse(cr, uid, uid).company_id.property_aduno_skonto_creditor_account.id
    account_writeoff_id = self.pool.get('res.users').browse(cr, uid, uid, context).company_id.property_bvr_skonto_creditor_account.id
    # Abschreibungsgrund: Skonto: ID 1
    payment_difference_id = statement.profile_id.payment_type_discount_id.id

    global partner_id, account_receivable, account_payable, move_id, account_id
    account_receivable = False
    account_payable = False

    def initialice_voucher(ml):
        global partner_id, account_receivable, account_payable, move_id, account_id
        partner_id = ml.partner_id.id
        account_receivable = ml.partner_id.property_account_receivable.id
        account_payable = ml.partner_id.property_account_payable.id
        move_id = ml.move_id.id
        account_id = ml.account_id.id

    global payment_option, amountok, delete2, rounding_difference

    def calculate_amounts(amount_to_pay, amount):
        global payment_option, amountok, delete2, rounding_difference
        payment_option = 'with_writeoff'

        if amount > amount_to_pay:
            # Differences to CHF 0.50 be booked directly as rounding difference
            if (amount - amount_to_pay) <= 0.50:
                rounding_difference = amount - amount_to_pay
                amount = amount - rounding_difference

        if amount_to_pay == amount:
            # Total amount paid
            amountok = True
        elif amount_to_pay > amount:
            # Invoice amount is greater than the amount paid
            if (amount_to_pay - amount) <= 0.50:
                # Differences to CHF 0.50 be booked directly as discount
                payment_option = 'with_writeoff'
                amountok = True
            else:
                # if the difference is greater than EUR 1, kept open
                payment_option = 'without_writeoff'
        else:
            # Amount paid is greater than the invoice amount
            # TODO: Gutschrift erstellen!!!!
            # im Moment: DELETE!
            delete2 = True
            payment_option = 'without_writeoff'
            amountok = False

    num_wrong_merchant = 0
    total_wrong_merchant = 0
    aduno_file_content = base64.decodestring(_file).splitlines()
    file_merchant_id = aduno_file_content[0].split()[0][12:]
    if file_merchant_id != statement.profile_id.merchant_id:
        raise osv.except_osv(_('Error'),
                             '{2}\n {0}!={1}'.format(file_merchant_id, statement.profile_id.merchant_id,
                                                     _('File and bank statement profile Merchant IDs do not match!')))
    for lines in aduno_file_content:
        # Manage files without carriage return
        while lines:
            (line, lines) = (lines[:250], lines[250:])
            record = {}

            evr_type = line[54:59]
            # Current row is the END row (begin code '999' or '995')
            if evr_type == 'EVR99':
                if found_total:
                    raise osv.except_osv(_('Error'),
                                         _('Too much total record found!'))
                found_total = True
                break

            # Row 'EVR02' - Section start
            elif evr_type == 'EVR02':
                # The posting date should be the one from the section start
                # It's used in records of the EVR07 lines
                posting_date = time.strptime(line[59:67], '%Y%m%d')
                found_section_start = True

            # Row 'EVR04' - Batch start
            elif evr_type == 'EVR04':
                batch_count = int(line[113:119])
                batch_amount_gross = float(float(line[119:130]) / 100)
                batch_amount_net = float(float(line[141:152]) / 100)
                batch_commission = float(float(line[152:163]) / 100) * -1
                commission_per_unit = batch_commission / batch_amount_gross
                batch_index = 0
                sum_batch_amount_net = 0
                sum_batch_commission = 0

            # Row 'EVR07' - Single Transaction
            elif evr_type == 'EVR07':
                if not found_section_start:
                    raise osv.except_osv(_('Error'),
                                         _('No section start (EVR02) found before transaction line (EVR07)'))
                batch_index += 1
                amount_gross = float(float(line[108:119]) / 100)
                commission = round(amount_gross * commission_per_unit, 2)
                amount_net = amount_gross - commission

                # The last batch line is computed with the sum of other lines in the batch
                # This is done to fix 'rounding errors' and get the final sums correctly
                if batch_index == batch_count and batch_index >= 2:
                    commission = batch_commission - sum_batch_commission
                    amount_net = batch_amount_net - sum_batch_amount_net

                sum_batch_amount_net += amount_net
                sum_batch_commission += commission

                total_amount += amount_net
                total_commission += commission

                merchant_subsidiary_id = line.split()[1]
                if merchant_subsidiary_id != statement.profile_id.merchant_subsidiary_id:
                    num_wrong_merchant += 1
                    total_wrong_merchant += amount_net
                    continue
                record = {
                    'reference': line[67:85],
                    'amount': amount_net,
                    'commission': commission,
                    'date': time.strftime('%Y-%m-%d', posting_date),
                    'cost': 0.0,
                }
                records.append(record)

    account_receivable = False
    account_payable = False

    for record in records:
        successed = False
        partner_id = False
        account_id = False
        line_ids = False
        move_id = False
        payment_option = 'without_writeoff'
        # mica1 comment = 'Skonto'
        comment = 'Aduno'
        amountok = False
        delete2 = False
        rounding_difference = 0

        # values für bank line erstellen
        amount = record['amount']
        date = record['date']

        reference = record['reference'].rstrip(' ')
        line_ids = _reconstruct_invoice_ref(cr, uid, reference, None)

        # Remove the 11 first char because it can be adherent number
        # TODO check if 11 is the right number
        reference = record['reference'].rstrip(' ')
        values = {
            'name': '/',
            'date': record['date'],
            'amount': amount,
            'ref': reference,
            'transaction_id': reference,
            'type': (amount >= 0 and 'customer') or 'supplier',
            'statement_id': statement_id,
        }

        if reference and not line_ids:
            line_ids = move_line_obj.search(cr, uid, [('ref', 'like', reference),
                                                      ('reconcile_id', '=', False),
                                                      ('account_id.type', 'in', ['receivable', 'payable']),
                                                      ], order='date desc', context=context)

        partner_id = False
        account_id = False
        result = 0

        if line_ids:
            move = move_line_obj.browse(cr, uid, line_ids[0], context=context)
            move_id = move.move_id.id
            partner_id = move.partner_id.id
            num = move.invoice.number if move.invoice else False
            values['name'] = num if num else values['name']
            values['partner_id'] = partner_id

            invoice_ids = invoice_obj.search(cr, uid, [('move_id', '=', move_id)])
            inv = invoice_obj.browse(cr, uid, invoice_ids)[0]
            inv_move_lines = move_line_obj.search(cr, uid, [('move_id', '=', move_id),
                                                            ('date_maturity', '!=', None)
                                                            ], order='debit DESC, credit DESC')
            count_lines = len(inv_move_lines)
            inv_move_lines = move_line_obj.browse(cr, uid, inv_move_lines, context=context)

            for line in move_line_obj.browse(cr, uid, line_ids, context=context):
                if not successed:
                    if line.partner_id:
                        account_receivable = line.partner_id.property_account_receivable.id
                        account_payable = line.partner_id.property_account_payable.id
                        partner_id = line.partner_id.id
                    else:
                        successed = False

                # case1: customer/debitor
                if amount >= 0:
                    # mica1 account_writeoff_id = statement.company_id.property_aduno_skonto_debitor_account.id
                    account_writeoff_id = statement.company_id.property_bvr_skonto_debitor_account.id

                    # account_writeoff_id = 670 #4900 Gewährte Skonti
                    if inv.invoice_line and inv.invoice_line[0] and inv.invoice_line[0].invoice_line_tax_id and inv.invoice_line[0].invoice_line_tax_id[0].amount == 0.19:
                        # mica1 account_writeoff_id = statement.company_id.property_aduno_skonto_debitor_account.id
                        account_writeoff_id = statement.company_id.property_bvr_skonto_debitor_account.id
                        # account_writeoff_id = 670 #4900 Gewährte Skonti 19% USt

                    # Zahlung ohne Skonto (hat nur eine Buchung)
                    if count_lines == 1:
                        for ml in inv_move_lines:
                            initialice_voucher(ml)
                            calculate_amounts(ml.debit, amount)
                    # Zahlung mit Skonto (2 Buchungen)
                    elif count_lines == 2:
                        # TODO: übeprüfen ob 2. Buchung maximal 4% Skonto hat
                        successed = False
                        for ml in inv_move_lines:
                            initialice_voucher(ml)

                            # Fälligkeitsdatum + 3 Tage rechnen
                            if not successed:
                                if (datetime.strptime(ml.date_maturity, '%Y-%m-%d') + timedelta(days=statement.company_id.property_bvr_delay)).strftime('%Y-%m-%d') >= date:
                                    calculate_amounts(ml.debit, amount)
                                    successed = True
                                # Zahlung ist verspätet -> muss vollen Betrag zahlen
                                else:
                                    calculate_amounts(inv.residual, amount)
                    # alle anderen Fälle müssen Teilzahlung oder Sonerfälle sein
                    else:
                        delete2 = True
                # case2: supplier/creditor
                else:
                    account_writeoff_id = statement.company_id.property_bvr_skonto_creditor_account.id
                    if inv.invoice_line and inv.invoice_line[0] and inv.invoice_line[0].invoice_line_tax_id and inv.invoice_line[0].invoice_line_tax_id[0].amount == 0.19:
                        account_writeoff_id = statement.company_id.property_bvr_skonto_creditor_account.id

            result = voucher_obj.onchange_partner_id(cr, uid, [], partner_id,
                                                     journal_id=statement.journal_id.id,
                                                     amount=abs(amount),
                                                     currency_id=statement.currency.id,
                                                     ttype='receipt',
                                                     date=statement.date,
                                                     context=context)

        account_id = statement.journal_id.default_credit_account_id.id
        if result:
            account_id = result.get('account_id', statement.journal_id.default_credit_account_id.id)
        voucher_res = {
            'type': 'receipt',
            'name': values['name'],
            'partner_id': partner_id,
            'journal_id': statement.journal_id.id,
            'account_id': account_id,
            'company_id': statement.company_id.id,
            'currency_id': statement.currency.id,
            'date': date or time.strftime('%Y-%m-%d'),
            'amount': abs(amount),
            'period_id': statement.period_id.id,
            'payment_option': payment_option,
            'comment': comment,
            'writeoff_acc_id': account_writeoff_id,
            'payment_difference_id': payment_difference_id,
            'commission': record['commission'],
        }

        voucher_id = voucher_obj.create(cr, uid, voucher_res, context=context)
        context.update({'partner_id': partner_id})
        values['voucher_id'] = voucher_id
        voucher_line_dict = False

        # Totalbetrag zum Reconcilen bestimmen
        # falls die gesamte Rechnung ausgegelichen werden soll -> Restbetrag wird ausgeglichen
        if amountok:
            amount_total = inv.residual
        # nur bezahlter Betrag nehmen -> Rechnung bleibt offen
        else:
            amount_total = amount

        amount_total = abs(amount)
        delete = True
        create_voucher_line = False

        if result:
            if result['value']['line_cr_ids'] or result['value']['line_dr_ids']:
                for line_dict in result['value']['line_cr_ids'] + result['value']['line_dr_ids']:
                    move_line = move_line_obj.browse(cr, uid, line_dict['move_line_id'], context)
                    create_voucher_line = False
                    if move_id == move_line.move_id.id:
                        create_voucher_line = True
                    else:
                        invoice_id = invoice_obj.search(cr, uid, [('move_id', '=', move_line.move_id.id)])
                        if invoice_id:
                            invoice = invoice_obj.browse(cr, uid, invoice_id)[0]
                            cr.execute("SELECT count(*) FROM information_schema.columns WHERE table_name='account_invoice' and column_name='followup_parent_id'")
                            column_followup_parent_id_count = cr.fetchone()[0]
                            if column_followup_parent_id_count > 0 and invoice and invoice.followup_parent_id:
                                if move_id == invoice.followup_parent_id.move_id.id:
                                    create_voucher_line = True

                    if create_voucher_line:
                        # Voucher darf nicht gelöscht werden
                        delete = False
                        voucher_line_dict = line_dict
                        # Beträge zum reconcilen rechnen
                        if amount_total >= voucher_line_dict['amount_unreconciled']:
                            voucher_line_dict['amount'] = voucher_line_dict['amount_unreconciled'] - record['commission']
                            amount_total = amount_total - voucher_line_dict['amount_unreconciled']
                        elif amount_total == 0:
                            voucher_line_dict['amount'] = 0
                        else:
                            voucher_line_dict['amount'] = amount_total + record['commission']
                            voucher_line_dict['reconcile'] = True
                            voucher_line_dict['skonto'] = False
                            amount_total = 0

                        voucher_line_dict.update({'voucher_id': voucher_id})
                        voucher_line_obj.create(cr, uid, voucher_line_dict, context=context)
                        # show if invoice is fully paid

                voucher_line_dict_diff = voucher_line_dict.copy()
                if rounding_difference:
                    rounding_difference = round(rounding_difference, 2)
                    voucher_line_dict_diff.update({'amount_unreconciled': rounding_difference})
                    voucher_line_dict_diff.update({'amount': rounding_difference})
                    voucher_line_dict_diff.update({'amount_original': rounding_difference})
                    voucher_line_dict_diff.update({'account_id': statement.company_id.property_rounding_difference_cost_account.id})
                    voucher_line_dict_diff.update({'move_line_id': None})
                    voucher_line_dict_diff.update({'voucher_id': voucher_id})
                    rounding_difference -= rounding_difference
                    voucher_line_obj.create(cr, uid, voucher_line_dict_diff, context=context)

                    if abs(rounding_difference) < 0.0000000001:
                        voucher_res_update = {
                            'payment_option': 'without_writeoff',
                        }
                        voucher_obj.write(cr, uid, [voucher_id], voucher_res_update, context=context)

        if delete:
            values['voucher_id'] = None

        account_id = _get_account(self, cr, uid, line_ids, record, context=context)

        if not account_id:
            if amount >= 0:
                account_id = account_receivable
            else:
                account_id = account_payable

        # If line not linked to an invoice we create a line not linked to a voucher
        if not account_id and not line_ids:
            name = "property_account_receivable"
            if amount < 0:
                name = "property_account_payable"
            prop = property_obj.search(
                cr,
                uid,
                [
                    ('name', '=', name),
                    ('company_id', '=', statement.company_id.id),
                    ('res_id', '=', False)
                ],
                context=context
            )
            if prop:
                value = property_obj.read(cr, uid, prop[0], ['value_reference']).get('value_reference', False)
                if value:
                    account_id = int(value.split(',')[1])
            else:
                raise osv.except_osv(_('Error'),
                                     _('The properties account payable account receivable are not set'))
        if not account_id and line_ids:
            raise osv.except_osv(_('Error'),
                                 _('The properties account payable account receivable are not set'))
        values['account_id'] = account_id
        values['partner_id'] = partner_id
        values['commission'] = record['commission']

        statement_line_id = statement_line_obj.create(cr, uid, values, context=context)
        commission_account_id = statement.profile_id.commission_account_id.id
        commission_info_values = {
            'payment_option': 'with_writeoff',
            'writeoff_acc_id': commission_account_id,
            'payment_difference_id': statement.profile_id.payment_type_commission_id.id,
        }
        voucher_obj.write(cr, uid, [voucher_id], commission_info_values)
    attachment_obj.create(cr, uid, {
        'name': 'Aduno %s' % time.strftime("%Y-%m-%d_%H:%M:%S", time.gmtime()),
        'datas': _file,
        'datas_fname': 'Aduno %s.txt' % time.strftime("%Y-%m-%d_%H:%M:%S", time.gmtime()),
        'res_model': 'account.bank.statement',
        'res_id': statement_id,
    }, context=context)
    # TODO: put this inside a function. Show confirmation wizard
    num_imported = 0
    total_aduno = 0
    total_fees = 0
    num_incorrect = 0
    total_diff_incorrect = 0
    num_mismatched = 0
    total_mismatched = 0

    for st_line in statement.line_ids:
        if st_line.open_amount_invoice != 0 or st_line.writeoff_amount < 0:
            num_incorrect += 1
            total_diff_incorrect += st_line.open_amount_invoice
        elif not st_line.voucher_id:
            num_mismatched += 1
            total_mismatched += st_line.amount
        else:
            num_imported += 1
            total_aduno += st_line.amount
            total_fees += st_line.commission

    summary_file_content = (
        "Number of imported payments: %d \n"
        "    Total of paid invoices: %.2f \n"
        "    Total Aduno payment: %.2f \n"
        "    Total Aduno fees: %.2f \n"
        "\n"
        "Number of matched payments with incorrect amount: %d \n"
        "    Total difference (excl. fees): %.2f \n"
        "\n"
        "Number of mismatched payments: %d \n"
        "    Total mismatched payments (excl. fees): %.2f \n"
        "\n"
        "Number of payments from different sub-merchants: %d \n"
        "    Total payments from different sub-merchants (excl. fees): %.2f \n"
    ) % (num_imported, total_aduno + total_fees, total_aduno, total_fees,
         num_incorrect, total_diff_incorrect,
         num_mismatched, total_mismatched,
         num_wrong_merchant, total_wrong_merchant)
    file_encoded = base64.encodestring(summary_file_content)
    attachment_obj.create(cr, uid, {
        'name': 'Import summary',
        'datas': file_encoded,
        'datas_fname': 'Import_summary_%s.txt' % time.strftime("%Y-%m-%d_%H:%M:%S", time.gmtime()),
        'res_model': 'account.bank.statement',
        'res_id': statement.id,
    }, context=context)

    wizard_id = self.pool.get("confirmation.summary").create(cr, uid, {},
                                                             context=dict(context,
                                                                          summary=summary_file_content))
    view_id = self.pool.get('ir.model.data').get_object(cr, uid, 'pc_aduno', 'confirmation_view').id
    return {
        'name': 'Aduno import successful',
        'type': 'ir.actions.act_window',
        'res_model': 'confirmation.summary',
        'res_id': wizard_id,
        'view_mode': 'form',
        'view_type': 'form',
        'view_id': view_id,
        'target': 'new',
    }


class aduno_import_wizard(osv.osv_memory):
    _name = 'aduno.import.wizard'

    _columns = {
        'state': fields.selection([('all_fields_filled_in', 'all_fields_filled_in'),
                                   ('some_fields_not_filled_in', 'some_fields_not_filled_in'),
                                   ]),
        'file': fields.binary('Aduno EVG File')
    }

    _defaults = {
        'state': 'all_fields_filled_in',
    }

    def default_get(self, cr, uid, fields, context=None):
        """ If either the field merchant_id or merchant_subsidiary_id is missing, we change its default state
            from all_fields_filled_in to some_fields_not_filled_in.
        """
        ret = super(aduno_import_wizard, self).default_get(cr, uid, fields, context=context)

        # If either the field merchant_id or merchant_subsidiary_id is missing, we change its default state.
        account_bank_statement_obj = self.pool.get('account.bank.statement')
        bank_statement = account_bank_statement_obj.browse(cr, uid, context['active_ids'][0], context=context)
        if not bank_statement.profile_id.merchant_id or not bank_statement.profile_id.merchant_subsidiary_id:
            ret['state'] = 'some_fields_not_filled_in'

        return ret

    def import_aduno(self, cr, uid, ids, context=None):
        data = {}
        if context is None:
            context = {}
        else:
            context = context.copy()
        context['bt_payment_difference'] = True
        active_ids = context.get('active_ids', [])
        active_id = context.get('active_id', False)
        data['form'] = {}
        data['ids'] = active_ids
        data['id'] = active_id
        data['form']['file'] = ''
        res = self.read(cr, uid, ids[0], ['file'])
        if res:
            data['form']['file'] = res['file']
        return _import(self, cr, uid, data, context=context)

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
