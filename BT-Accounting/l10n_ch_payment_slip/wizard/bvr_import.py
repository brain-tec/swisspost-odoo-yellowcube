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

from tools.translate import _
from osv import osv, fields
from tools import mod10r
import pooler

from datetime import datetime
from datetime import timedelta
import mx.DateTime as dt

def _reconstruct_invoice_ref(cr, uid, reference, context=None):
    ###
    id_invoice = False
    # On fait d'abord une recherche sur toutes les factures
    # we now search for an invoice
    print "reference", reference
    user_obj = pooler.get_pool(cr.dbname).get('res.users')
    user_current=user_obj.browse(cr, uid, uid)
    partner_bank_obj=pooler.get_pool(cr.dbname).get('res.partner.bank')

    ##
    cr.execute("SELECT inv.id,inv.number, partner_bank_id from account_invoice "
                   "AS inv where inv.company_id = %s and type='out_invoice'",
                   (user_current.company_id.id,))
    cr.execute("SELECT inv.id,bvr_reference, partner_bank_id from account_invoice AS inv where inv.company_id = %s and state = 'open' and type = 'out_invoice' ORDER BY inv.id DESC" ,(user_current.company_id.id,)) #hack by wysi1
    result_invoice = cr.fetchall()
    REF = re.compile('[^0-9]')
    for inv_id,bvr_reference,partner_bank_id in result_invoice:
        #hack jool: create full ref number
        partner_bank_current=partner_bank_obj.browse(cr, uid, partner_bank_id)
        res = ''
        if partner_bank_current.bvr_adherent_num:
            res = partner_bank_current.bvr_adherent_num
        invoice_number = ''
        if bvr_reference:
            #invoice_number = re.sub('[^0-9]', '0', inv_name)
            bvr_reference = re.sub('[^0-9]', '', bvr_reference)
            bvr_reference = bvr_reference.lstrip('0')
            
        print "invoice_number", bvr_reference
        #hack by wysi1:
        if bvr_reference == reference:
            id_invoice = inv_id
            print "BREAK"
            break
            

    if id_invoice:
        # hack jool: added check with date_maturity
#        cr.execute('SELECT l.id ' \
#                    'FROM account_move_line l, account_invoice i ' \
#                    'WHERE l.move_id = i.move_id AND l.reconcile_id is NULL AND date_maturity is not NULL ' \
#                        'AND i.id IN %s',(tuple([id_invoice]),))
        # HACK: 02.06.2014 14:33:52: olivier: order by date_maturity so that the lines to reconcile occure on top
        cr.execute('SELECT l.id ' \
                    'FROM account_move_line l, account_invoice i ' \
                    'WHERE l.move_id = i.move_id AND l.reconcile_id is NULL ' \
                        'AND i.id IN %s order by date_maturity',(tuple([id_invoice]),))
        inv_line = []
        for id_line in cr.fetchall():
            inv_line.append(id_line[0])
        print "line", inv_line
        return inv_line
    else:
        return []
    return True

def _get_account(self, cursor, uid, line_ids, record, context=None):
    """Get account from move line or from property"""
    property_obj = self.pool.get('ir.property')
    move_line_obj = self.pool.get('account.move.line')
    account_id = False
    if line_ids:
        for line in move_line_obj.browse(cursor, uid, line_ids, context=context):
            return line.account_id.id
    if not account_id and not line_ids:
        name = "property_account_receivable"
        if record['amount'] < 0:
            name = "property_account_payable"
        account_id = property_obj.get(cursor, uid, name, 'res.partner', context=context)
        if not account_id:
            raise osv.except_osv(_('Error'),
                             _('The properties account payable account receivable are not set'))
        account_id = account_id.id
    return account_id

def _import(self, cr, uid, data, context=None):

    statement_line_obj = self.pool.get('account.bank.statement.line')
    voucher_obj = self.pool.get('account.voucher')
    voucher_line_obj = self.pool.get('account.voucher.line')
    move_line_obj = self.pool.get('account.move.line')
    property_obj = self.pool.get('ir.property')
    model_fields_obj = self.pool.get('ir.model.fields')
    attachment_obj = self.pool.get('ir.attachment')
    statement_obj = self.pool.get('account.bank.statement')
    property_obj = self.pool.get('ir.property')
    invoice_obj = self.pool.get('account.invoice')
    file = data['form']['file']
    if not file:
        raise osv.except_osv(_('UserError'),
                             _('Please select a file first!'))
    statement_id = data['id']
    records = []
    total_amount = 0
    total_cost = 0
    find_total = False
    #Konto Abschreibungen 420: Sonstige betriebliche Aufwendungen und Abschreibungen: ID 1582
    #account_writeoff_id = 800 #6920
    #TODO set correct account!!!    
    account_writeoff_id = self.pool.get('res.users').browse(cr, uid, uid).company_id.property_bvr_skonto_creditor_account.id
    #Abschreibungsgrund: Skonto: ID 1
    payment_difference_id = 1

    if context is None:
        context = {}

    global partner_id, account_receivable, account_payable, move_id, account_id
    statement = statement_obj.browse(cr, uid, statement_id, context=context)
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
#        print 'amount: ', amount
#        print 'amount_to_pay: ', amount_to_pay

        global payment_option, amountok, delete2, rounding_difference
        payment_option = 'with_writeoff'


        if amount > amount_to_pay:
#            print 'calculate_amounts if1'
            #Differenezen bis CHF 0.50 werden direkt als Rundungsdifferenz ausgebucht
            if (amount-amount_to_pay) <= 0.50:
#                print 'calculate_amounts elif2 if'
                rounding_difference = amount - amount_to_pay
                amount = amount - rounding_difference

#        if amount_to_pay > amount:
#            print 'calculate_amounts if2'
#            #Differenezen bis CHF 0.50 werden direkt als Rundungsdifferenz ausgebucht
#            if (amount_to_pay-amount) <= 0.50:
#                print 'calculate_amounts elif2 if'
#                rounding_difference = amount_to_pay - amount
#                amount = amount + rounding_difference        

        #Totalbetrag wurde bezahlt
        if amount_to_pay == amount:
#            print 'calculate_amounts if'
            amountok = True
            #payment_option = 'without_writeoff'
        #Rechnungsbetrag ist grösser als bezahlter Betrag
        elif amount_to_pay > amount:
#            print 'calculate_amounts elif'
            #Differenezen bis CHF 0.50 werden direkt als Skonto ausgebucht
            if (amount_to_pay-amount) <= 0.50:
#                print 'calculate_amounts elif if'
                payment_option = 'with_writeoff'
                amountok = True

            #wenn Differenz grösser als Euro 1 ist -> offen behalten
            else:
#                print 'calculate_amounts elif else'
                payment_option = 'without_writeoff'
        #bezahlter Betrag ist grösser als Rechnungsbetrag
        else:
#            print 'calculate_amounts else'
            #todo Gutschrift erstellen!!!!
            #im Moment: DELETE!
            delete2 = True
            payment_option = 'without_writeoff'

            #hack jool: wenn eine Rechnung bezahlt wird ohne Skonto, dieser hätte jedoch bezahlt werden müssen, darf amountok nicht ok sein, oder?
            #amountok = True
            amountok = False


    success = 0
    failed = 0
    i = 0
    for lines in base64.decodestring(file).split("\n"):
        # Manage files without carriage return
        while lines:
            (line, lines) = (lines[:128], lines[128:])
            record = {}

            if line[0:3] in ('999', '995'):
                if find_total:
                    raise osv.except_osv(_('Error'),
                            _('Too much total record found!'))
                find_total = True
                if lines:
                    raise osv.except_osv(_('Error'),
                            _('Record found after total record!'))
                amount = float(line[39:49]) + (float(line[49:51]) / 100)
                cost = float(line[69:76]) + (float(line[76:78]) / 100)
                if line[2] == '5':
                    amount *= -1
                    cost *= -1

                if round(amount - total_amount, 2) >= 0.01 \
                        or round(cost - total_cost, 2) >= 0.01:
                    raise osv.except_osv(_('Error'),
                            _('Total record different from the computed!'))
                if int(line[51:63]) != len(records):
                    raise osv.except_osv(_('Error'),
                            _('Number record different from the computed!'))
            else:
                record = {
                    'reference': line[12:39],
                    'amount': float(line[39:47]) + (float(line[47:49]) / 100),
                    'date': time.strftime('%Y-%m-%d',
                        time.strptime(line[71:77], '%y%m%d')),
                    'cost': float(line[96:98]) + (float(line[98:100]) / 100),
                }

                if record['reference'] != mod10r(record['reference'][:-1]):
                    raise osv.except_osv(_('Error'),
                            _('Recursive mod10 is invalid for reference: %s') % \
                                    record['reference'])

                if line[2] == '5':
                    record['amount'] *= -1
                    record['cost'] *= -1
                total_amount += record['amount']
                total_cost += record['cost']
                records.append(record)

    account_receivable = False
    account_payable = False
    statement = statement_obj.browse(cr, uid, statement_id, context=context)

    for record in records:
#        print '#############################################################################################################'
        print 'record: ', record
#################################################################################################################################################
        #überprüfen, ob Rechnungsnummer in String 'zweck' irgendwo vorkommt
        successed = False
        partner_id = False
        account_id = False
        line_ids = False
        move_id = False
        line2reconcile = False
        payment_option = 'without_writeoff'
        comment = 'Skonto'
        amountok = False
        delete2 = False
        rounding_difference = 0

        #values für bank line erstellen
        amount = record['amount']
        date = record['date']
#################################################################################################################################################

        # HACK: 06.07.2015 10:53:35: jool1: we first check if we find an out invoice with the correct the same bvr_reference in invoice
        reference = record['reference'].lstrip('0')
        line_ids = _reconstruct_invoice_ref(cr, uid, reference, None)
        
        # Remove the 11 first char because it can be adherent number        
        # TODO check if 11 is the right number
        reference = record['reference'][11:-1].lstrip('0')
        values = {
            'name': '/',
            'date': record['date'],
            'amount': amount,
            'ref': reference,
            'type': (amount >= 0 and 'customer') or 'supplier',
            'statement_id': statement_id,
        }

        if reference and not line_ids:
            line_ids = move_line_obj.search(cr, uid, [
                ('ref', 'like', reference),
                ('reconcile_id', '=', False),
                ('account_id.type', 'in', ['receivable', 'payable']),
                ], order='date desc', context=context)

#        if not line_ids:
#            reference_2 = record['reference'][18:-1]
#            print 'reference_2: ', reference_2
#            line_ids = move_line_obj.search(cr, uid, [
#                ('ref', '=', reference_2),
#                ('reconcile_id', '=', False),
#                ('account_id.type', 'in', ['receivable', 'payable']),
#                ], order='date desc', context=context)
        partner_id = False
        account_id = False
        print 'line_ids: ', line_ids
        #get move_lines from invoice
#        print 'record[reference]: ',record['reference']
#        print 'values: ', values
        result = 0
        #only do if line_ids is not empty
#        print 'line_ids: ', line_ids

        if line_ids:
#            print 'IF LINE_IDS ---------------------------------------------------------------------'
            move = move_line_obj.browse(cr, uid, line_ids[0], context=context)
            move_id = move.move_id.id
            
            # HACK: 06.07.2015 11:13:25: jool1: set name
            partner_id = move.partner_id.id
            num = move.invoice.number if move.invoice else False
            values['name'] = num if num else values['name']
            values['partner_id'] = partner_id
            
#            print 'move_id: ', move_id
            #get invoice
            invoice_ids = invoice_obj.search(cr, uid, [('move_id','=',move_id)])
#            print 'invoice_ids: ', invoice_ids
            inv = invoice_obj.browse(cr, uid, invoice_ids)[0]
#            print 'inv: ', inv
            inv_move_lines = move_line_obj.search(cr, uid, [('move_id', '=', move_id), ('date_maturity','!=', None)], order='debit DESC, credit DESC')
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
                #move_id = line.move_id.id
    #            if record['amount'] >= 0:
    #                if round(record['amount'] - line.debit, 2) < 0.01:
    ##                    line2reconcile = line.id
    #                    account_id = line.account_id.id
    #                    break
    #            else:
    #                if round(line.credit + record['amount'], 2) < 0.01:
    ##                    line2reconcile = line.id
    #                    account_id = line.account_id.id
    #                    break

                #case1: customer/debitor
                if amount >= 0:
                    account_writeoff_id = statement.company_id.property_bvr_skonto_debitor_account.id
                    #account_writeoff_id = 670 #4900 Gewährte Skonti
                    if inv.invoice_line and inv.invoice_line[0] and inv.invoice_line[0].invoice_line_tax_id and inv.invoice_line[0].invoice_line_tax_id[0].amount == 0.19:
                        account_writeoff_id = statement.company_id.property_bvr_skonto_debitor_account.id
                        #account_writeoff_id = 670 #4900 Gewährte Skonti 19% USt

                    #Zahlung ohne Skonto (hat nur eine Buchung)
                    if count_lines == 1:
                        for ml in inv_move_lines:
                            initialice_voucher(ml)
                            calculate_amounts(ml.debit, amount)

                    #Zahlung mit Skonto (2 Buchungen)
                    elif count_lines == 2:
                        #todo: übeprüfen ob 2. Buchung maximal 4% Skonto hat
                        successed = False
                        for ml in inv_move_lines:
                            initialice_voucher(ml)

                            #Fälligkeitsdatum + 3 Tage rechnen
#                            print 'date: ', date
#                            print 'date_maturity: ', (dt.strptime(ml.date_maturity,'%Y-%m-%d')).strftime('%Y-%m-%d')
#                            print 'date_maturity +3: ', (dt.strptime(ml.date_maturity,'%Y-%m-%d')+dt.RelativeDateTime(days=statement.company_id.property_bvr_delay)).strftime('%Y-%m-%d')
                            #print ml.debit
                            #print amount

                            if not successed:
                                #print 'DT !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!'
                                #if (dt.strptime(ml.date_maturity,'%Y-%m-%d')+dt.RelativeDateTime(days=7)).strftime('%Y-%m-%d') >=  date:
                                if (datetime.strptime(ml.date_maturity,'%Y-%m-%d')+timedelta(days=statement.company_id.property_bvr_delay)).strftime('%Y-%m-%d') >=  date:
#                                    print 'SKONTO OK'
                                #if (datetime.strptime(ml.date_maturity,'%Y-%m-%d')).strftime('%Y-%m-%d') >=  date:
                                    calculate_amounts(ml.debit, amount)
                                    successed = True
                                #Zahlung ist verspätet -> muss vollen Betrag zahlen
                                else:
#                                    print 'SKONTO NOT OK'
                                    calculate_amounts(inv.residual, amount)

                    #alle anderen Fälle müssen Teilzahlung oder Sonerfälle sein
                    else:
                        delete2 = True
                        #for ml in inv_move_lines:
                        #    initialice_voucher(ml)
                        #    if ml.date_maturity:
                        #        calculate_amounts(ml.debit, amount)                                             

                #case2: supplier/creditor
                else:
                    account_writeoff_id = statement.company_id.property_bvr_skonto_creditor_account.id
                    #account_writeoff_id = 641 #3900 Erhaltene Skonti
                    if inv.invoice_line and inv.invoice_line[0] and inv.invoice_line[0].invoice_line_tax_id and inv.invoice_line[0].invoice_line_tax_id[0].amount == 0.19:
                        account_writeoff_id = statement.company_id.property_bvr_skonto_creditor_account.id
                        #account_writeoff_id = 641#3900 Erhaltene Skonti 19% USt



            result = voucher_obj.onchange_partner_id(cr, uid, [], partner_id, journal_id=statement.journal_id.id, amount=abs(amount), currency_id= statement.currency.id, ttype='receipt', date=statement.date ,context=context)

#        print 'result: ', result
        #hack jool: set account_id (needed if invoice is not assignable)
        account_id = statement.journal_id.default_credit_account_id.id
        #hack jool: if invoice is not assignable
        if result:
            print 'result: ', result
            account_id = result.get('account_id', statement.journal_id.default_credit_account_id.id)
        voucher_res = { 'type': 'receipt' ,
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
                         }
#        print 'payment_option2: ', payment_option
#        voucher_res = { 'type': 'receipt' ,
#        
#             'name': values['name'],
#             'partner_id': partner_id,
#             'journal_id': statement.journal_id.id,
#             'account_id': result.get('account_id', statement.journal_id.default_credit_account_id.id),
#             'company_id': statement.company_id.id,
#             'currency_id': statement.currency.id,
#             'date': record['date'] or time.strftime('%Y-%m-%d'),
#             'amount': abs(record['amount']),
#             'period_id': statement.period_id.id
#             }
        voucher_id = voucher_obj.create(cr, uid, voucher_res, context=context)
        #hack jool
        context.update({'partner_id': partner_id})
        #hack by wysi1: ansonsten wird nur die erste Rechnung bezahlt, alle anderen nicht mehr
        #context.update({'move_line_ids': line_ids})

        values['voucher_id'] = voucher_id
        voucher_line_dict =  False


        #Totalbetrag zum Reconcilen bestimmen
        #falls die gesamte Rechnung ausgegelichen werden soll -> Restbetrag wird ausgeglichen
#        print 'amountok: ',amountok
        #print 'inv.residual: ',inv.residual
#        print 'amount: ',amount
        if amountok:
            amount_total = inv.residual
        #nur bezahlter Betrag nehmen -> Rechnung bleibt offen
        else:
            amount_total = amount

        #hack by wysi1:
        #amount_total = abs(amount)
        delete = True

        #hack jool: if invoice is not assignable (result is empty)
        if result:
            if result['value']['line_cr_ids'] or result['value']['line_dr_ids']:
                for line_dict in result['value']['line_cr_ids']+result['value']['line_dr_ids']:
                    move_line = move_line_obj.browse(cr, uid, line_dict['move_line_id'], context)
                    # HACK: 28.05.2013 16:27:46: olivier: check if move is corresponding to account_invoice.followup_parent_id (for fernuni)
                    create_voucher_line = False
                    if move_id == move_line.move_id.id:
                        create_voucher_line = True
                    else:
                        invoice_id = invoice_obj.search(cr, uid, [('move_id','=', move_line.move_id.id)])
                        if invoice_id:
                            invoice = invoice_obj.browse(cr, uid, invoice_id)[0]
                            print 'invoice.amount_total: ', invoice.amount_total
                            cr.execute("SELECT count(*) FROM information_schema.columns WHERE table_name='account_invoice' and column_name='followup_parent_id'")
                            column_followup_parent_id_count = cr.fetchone()[0]
                            if column_followup_parent_id_count > 0 and invoice and invoice.followup_parent_id:
                            #if invoice and invoice.followup_parent_id:
                                if move_id == invoice.followup_parent_id.move_id.id:
                                    create_voucher_line = True
                        
                    if create_voucher_line:
                        #Voucher darf nicht gelöscht werden
                        delete = False
                        voucher_line_dict = line_dict
                        #Beträge zum reconcilen rechnen
                        if amount_total >= voucher_line_dict['amount_unreconciled']:
                            voucher_line_dict['amount'] = voucher_line_dict['amount_unreconciled']
                            amount_total = amount_total - voucher_line_dict['amount_unreconciled']
                        elif amount_total == 0:
                            voucher_line_dict['amount'] = 0
                        else:
                            voucher_line_dict['amount'] = amount_total
                            voucher_line_dict['skonto'] = True
                            amount_total = 0
            
                        voucher_line_dict.update({'voucher_id':voucher_id})
                        voucher_line_obj.create(cr, uid, voucher_line_dict, context=context)
                        #show if invoice is fully paid
            
                        ##hack jool1: because of skonto -> take correct move_line
                        #if round(line_dict['amount_unreconciled'],2)+0.05 > amount_total and round(line_dict['amount_unreconciled'],2)-0.05 < amount_total:
                        # voucher_line_dict = line_dict
            
            
                        ##hack by wysi1 weil die Beträge bei der Zahlung nicht korrekt waren
                        #delete = False
                        #if amount_total - voucher_line_dict['amount_unreconciled'] >= 0:
                        #   voucher_line_dict['amount'] = voucher_line_dict['amount_unreconciled']
                        #   amount_total = amount_total - voucher_line_dict['amount_unreconciled']
                        #else:
                        #   voucher_line_dict['amount'] = amount_total
                        #   amount_total = 0

                if rounding_difference and voucher_line_dict:
                    # hack jool: create line for rounding difference

                    # change by seca1 2017-09-15: if no rounding_difference,
                    #    then we don't need the copy of voucher_line_dict, thus
                    #    I place it inside the if-condition. Also, it may be
                    #    False and in that case it will cause an error, thus I
                    #    added the extra condition in the 'if'.
                    voucher_line_dict_diff = voucher_line_dict.copy()

                    rounding_difference = round(rounding_difference, 2)
                    voucher_line_dict_diff.update({'amount_unreconciled':rounding_difference})
                    voucher_line_dict_diff.update({'amount':rounding_difference})
                    voucher_line_dict_diff.update({'amount_original':rounding_difference})
                    voucher_line_dict_diff.update({'account_id':statement.company_id.property_rounding_difference_cost_account.id})
                    voucher_line_dict_diff.update({'move_line_id':None})
                    voucher_line_dict_diff.update({'voucher_id':voucher_id})
                    rounding_difference -= rounding_difference
                    voucher_line_obj.create(cr, uid, voucher_line_dict_diff, context=context)
                    
                    # HACK: 06.07.2015 09:01:25: jool1: set payment_option to without_writeoff if amount is 0
                    if abs(rounding_difference) < 0.0000000001:
                        voucher_res_update = {
                            'payment_option':'without_writeoff',
                        }
                        voucher_obj.write(cr, uid, [voucher_id], voucher_res_update, context=context)

        #hack by wysi1
        #if voucher_line_dict:
#        if voucher_line_dict and not delete:
#             voucher_line_dict.update({'voucher_id':voucher_id})
#             print 'voucher_line_dict: ', voucher_line_dict
#             voucher_line_obj.create(cr, uid, voucher_line_dict, context=context)                

        #hack by wysi1
        if delete:
            values['voucher_id'] = None

        # HACK: 02.06.2014 11:35:10: olivier: copied method (from newest version OpenERP 7 of this module) to get account_id (because it got every time the bank account (problem pakka)
        account_id = _get_account(self, cr, uid, line_ids, record, context=context)

        if not account_id:
            if amount >= 0:
                account_id = account_receivable
            else:
                account_id = account_payable
        ##If line not linked to an invoice we create a line not linked to a voucher
        if not account_id and not line_ids:
            name = "property_account_receivable"
            if amount < 0:
                name = "property_account_payable"
            prop = property_obj.search(
                        cr,
                        uid,
                        [
                            ('name','=',name),
                            ('company_id','=',statement.company_id.id),
                            ('res_id', '=', False)
                        ]
            )
            if prop:
                value = property_obj.read(cr, uid, prop[0], ['value_reference']).get('value_reference', False)
                if value :
                    account_id = int(value.split(',')[1])
            else :
                raise osv.except_osv(_('Error'),
                    _('The properties account payable account receivable are not set'))
        if not account_id and line_ids:
            raise osv.except_osv(_('Error'),
                _('The properties account payable account receivable are not set'))
        values['account_id'] = account_id
        values['partner_id'] = partner_id
        statement_line_obj.create(cr, uid, values, context=context)
    attachment_obj.create(cr, uid, {
        'name': 'BVR %s'%time.strftime("%Y-%m-%d_%H:%M:%S", time.gmtime()),
        'datas': file,
        'datas_fname': 'BVR %s.txt'%time.strftime("%Y-%m-%d_%H:%M:%S", time.gmtime()),
        'res_model': 'account.bank.statement',
        'res_id': statement_id,
        }, context=context)

    return {}

class bvr_import_wizard(osv.osv_memory):
    _name = 'bvr.import.wizard'
    _columns = {
        'file':fields.binary('BVR File')
    }

    def import_bvr(self, cr, uid, ids, context=None):
        data = {}
        if context is None:
            context = {}
        active_ids = context.get('active_ids', [])
        active_id = context.get('active_id', False)
        data['form'] = {}
        data['ids'] = active_ids
        data['id'] = active_id
        data['form']['file'] = ''
        res = self.read(cr, uid, ids[0], ['file'])
        if res:
            data['form']['file'] = res['file']
        _import(self, cr, uid, data, context=context)
        return {}

bvr_import_wizard()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:             
