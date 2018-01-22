##OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2009 Tiny SPRL (<http://tiny.be>).
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

import time
from osv import osv, fields
from tools.translate import _
import decimal_precision as dp
from bt_helper.tools import bt_format

global voucher
global voucher_type
global voucher_amount
global amount_total_paid_voucher
global company_currency
global current_currency
global current_currency_invoice
global context_multi_currency
global name
global move_pool, move_line_pool, currency_pool, tax_obj, seq_obj, account_pool, voucher_line_pool, invoice_obj
global debit, credit, line_total
global invoice_line_ids, skonto_line_ids, gutschrift_line_ids
global paid_to_much, paid_not_enough
global payment_option, voucher_writeoff_amount, writeoff_acc_id, payment_difference_id, writeoff_comment, writeoff_analytic_id
global diff_currency_correct_dict
global move_id
#TODO: needed?
global all_line_ids
global line_type_debit
global voucher_line
global move_line_id_of_write_off
global writeoff_amount
global last_move_line_id
global invoice_account_id
global voucher_line_type
global diff_currency_correct
global gutschriften_added
global rec_list_ids
global count_ids

global move_line_netto_dict
global move_line_vat_dict
global rounding_differences
global context_multi_currency_special
global amount_residual_total_without_skonto


class account_voucher_extended(osv.osv):
    _inherit = 'account.voucher'

    def _comunicate_globals(self, dic, write=True):
        """
        This method makes it possible to write, and read globals between scripts
        """
        _globals = globals()
        ret = {}
        for k in dic:
            if write:
                _globals[k] = dic[k]
            elif k in _globals:
                ret[k] = _globals[k]
        return dic if write else ret

    #hack jool
    def _get_type_bank_statement(self, cr, uid, context=None):
        if context is None: context = {}
        return context.get('line_type', False)

    #hack jool
    def _get_account_id_bank_statement(self, cr, uid, context=None):
        if context is None: context = {}
        return context.get('line_account_id', False)

    def refresh_voucher(self, cr, uid, ids):
        return True
    
    def cancel_voucher(self, cr, uid, ids, context=None):
#        print 'EXTENDED account_voucher cancel_voucher'
#        print 'account_voucher cancel_voucher ids: ', ids
        reconcile_pool = self.pool.get('account.move.reconcile')
        move_pool = self.pool.get('account.move')

        for voucher in self.browse(cr, uid, ids, context=context):
            recs = []
            #print 'voucher: ', voucher
            for line in voucher.move_ids:
                #print 'line: ', line
                if line.reconcile_id:
                    #recs += [line.reconcile_id.id]
                    #print 'line.reconcile_partial_id: ', line.reconcile_partial_id.id
                    #hack jool: just unlink account.move.reconcile if there are no other account_move_lines which refere to this id
                    cr.execute("SELECT count(*) from account_move_line AS line where line.reconcile_id = %s" ,(line.reconcile_id.id,))
                    result = cr.dictfetchall()
                    
                    # Get number of affected statement_ids
                    cr.execute("SELECT distinct(statement_id) as statement_ids from account_move_line AS line where line.reconcile_id = %s and statement_id is not null" ,(line.reconcile_id.id,))
                    result_statement_ids = cr.dictfetchall()
#                    print 'account_voucher cancel_voucher result: ', result[0]['count']
                    if line.reconcile_id.id not in recs:
                        recs += [line.reconcile_id.id]
                    
                    # If only one statement id is affected, it's a full cancel of the account.move.reconcile
                    # Otherwise it has to create a partial reconcile entry
                    if result[0]['count'] > 2 and len(result_statement_ids) > 1:
                        #unlink all and reset reconcile_partial_id for all other lines
                        cr.execute("SELECT id from account_move_line AS line where (statement_id != %s or statement_id is null) and line.reconcile_id = %s" ,(line.statement_id.id, line.reconcile_id.id,))
                        result = cr.dictfetchall()
                        #merges = unmerges =  []
                        merges = []
                        for r in result:
                            merges.append(r['id'])
                        
                        r_id = reconcile_pool.create(cr, uid, {
                            'type': 'auto',
#                            'line_partial_ids': map(lambda x: (4,x,False), merges+unmerges)
                            'line_partial_ids': map(lambda x: (4,x,False), merges)
                        })
                if line.reconcile_partial_id:
                    #print 'line.reconcile_partial_id: ', line.reconcile_partial_id.id
                    #hack jool: just unlink account.move.reconcile if there are no other account_move_lines which refere to this id
                    cr.execute("SELECT count(*) from account_move_line AS line where line.reconcile_partial_id = %s" ,(line.reconcile_partial_id.id,))
                    result = cr.dictfetchall()
                    #print 'account_voucher cancel_voucher result: ', result[0]['count']
                    if result[0]['count'] <=2:
                        if line.reconcile_partial_id.id not in recs:
                            recs += [line.reconcile_partial_id.id]

#            print 'account_voucher cancel_voucher recs:', recs
            reconcile_pool.unlink(cr, uid, recs)
            #print 'voucher.move_id: ', voucher.move_id
            if voucher.move_id:
                #print 'if before button_cancel'
                move_pool.button_cancel(cr, uid, [voucher.move_id.id])
                move_pool.unlink(cr, uid, [voucher.move_id.id])
                
            # hack by gafr1
            inv_obj = self.pool.get('account.invoice')
            inv_ids = inv_obj.search(cr, uid, [('state', '=', 'paid')])
            invoice_idx = []

            if voucher.line_ids:
                for voucher_line in voucher.line_ids:
                    if voucher_line.reconcile or voucher_line.amount != 0:
                        for inv in inv_obj.browse(cr, uid, inv_ids):
                            if voucher_line.move_line_id and voucher_line.move_line_id.move_id.id == inv.move_id.id:
                                if inv not in invoice_idx:
                                    invoice_idx.append(inv)

                if invoice_idx:
                    # Get the workflow id for 'account.invoice'
                    sqlQuery = "SELECT id \
                            FROM wkf \
                            WHERE osv = 'account.invoice' \
                            LIMIT 1"
                    cr.execute(sqlQuery)
                    wkfId = cr.fetchone()[0]

                    if not wkfId:
                        print "ERROR: Workflow 'account.invoice' not found!"
                        continue
                        
                    # Get the activity id of the state 'open' in the account.invoice workflow
                    sqlQuery = "SELECT id \
                            FROM wkf_activity \
                            WHERE wkf_id = %s AND wkf_activity.name = 'open' \
                            LIMIT 1" % wkfId
                    cr.execute(sqlQuery)
                    activityId = cr.fetchone()[0]

                    if not activityId:
                        print "ERROR: Activity 'open' in workflow 'account.invoice' not found!"
                        continue

                    # Change the workflow state of all involved invoices to 'open' and add some triggers (move lines)
                    for invoice in invoice_idx:
                        # Get the instance id of the given invoice
                        sqlQuery = "SELECT id \
                                FROM wkf_instance \
                                WHERE wkf_id = %s AND res_id = %s \
                                LIMIT 1" % (wkfId, invoice.id)
                        cr.execute(sqlQuery)
                        instanceId = cr.fetchone()[0]

                        if not instanceId:
                            print "ERROR: Instance for invoice (id: %s) not found!" % invoice.id
                            continue

                        # Get the workitem id of the given invoice
                        sqlQuery = "SELECT id \
                                FROM wkf_workitem \
                                WHERE inst_id = %s \
                                LIMIT 1" % instanceId
                        cr.execute(sqlQuery)
                        workitemId = cr.fetchone()[0]

                        if not workitemId:
                            print "ERROR: Workitem for invoice (id: %s, instance_id: %s) not found!" % (invoice.id, instanceId)
                            continue

                        # Update the workflow state of the given invoice to 'open'
                        sqlQuery = "UPDATE wkf_workitem \
                            SET act_id = %s \
                            WHERE inst_id = %s" % (activityId, instanceId)
                        cr.execute(sqlQuery)

                        # Get all move lines of the given invoice and add entries to the table wkf_triggers
                        moveline_obj = self.pool.get('account.move.line')
                        moveline_ids = moveline_obj.search(cr, uid, [('move_id', '=', invoice.move_id.id)])
                        for ml in moveline_obj.browse(cr, uid, moveline_ids):
                            # Filter the move lines
                            #hack jool: also consider refunds!!
                            if ((invoice.type == 'in_invoice' or invoice.type == 'out_refund') and ml.credit) or ((invoice.type == 'out_invoice'  or invoice.type == 'in_refund') and ml.debit):
                                # Add an entry to the wkf_triggers table for each move line
                                sqlQuery = "INSERT INTO wkf_triggers (instance_id, workitem_id, model, res_id) \
                                    VALUES (%s, %s, 'account.move.line', %s)" % (instanceId, workitemId, ml.id)
                                cr.execute(sqlQuery)

                        # Set the invoice state to 'open'
                        inv_obj.write(cr, uid, [invoice.id], {'state':'open'})
                        
        res = {
            'state':'cancel',
            'move_id':False,
        }
        self.write(cr, uid, ids, res)
        return True
        return super(account_voucher_extended, self).cancel_voucher(cr, uid, ids, context)
   
    def _compute_writeoff_amount(self, cr, uid, line_dr_ids, line_cr_ids, amount, type):
        print '_compute_writeoff_amount account_voucher/account_voucher.py'
        debit = credit = 0.0
        sign = type == 'payment' and -1 or 1
        for l in line_dr_ids:
            debit += l['amount']
        for l in line_cr_ids:
            credit += l['amount']
#        print 'amount ', amount
#        print 'credit ', credit
#        print 'debit ', debit
        #hack jool: wrong calculation
        #return abs(amount - abs(credit - debit))
        
        
        #return abs(credit - debit) - amount
        return sign * (credit - debit) - amount
        
        return super(account_voucher_extended, self)._compute_writeoff_amount(self, cr, uid, ids, line_dr_ids, line_cr_ids, amount, type)
   
    def _get_writeoff_amount_extended(self, cr, uid, ids, name, args, context=None):
        print '_get_writeoff_amount extended'
        if not ids: return {}
        res = {}
        for voucher in self.browse(cr, uid, ids, context=context):
            debit = credit = 0.0
            for l in voucher.line_dr_ids:
                debit += l.amount
            for l in voucher.line_cr_ids:
                credit += l.amount
            #hack jool: wrong calculation
            #res[voucher.id] =  abs(voucher.amount - abs(credit - debit))
#            print '_get_writeoff_amount: ', abs(credit - debit) - voucher.amount

            # HACK: 25.02.2014 11:28:36: olivier: return "+ amount" if amount in voucher < 0 -> means here we want to reconcile a supplier refund (we get money from a supplier)
            if voucher.amount < 0:
                res[voucher.id] =  abs(credit - debit) + voucher.amount
            else:
                res[voucher.id] =  abs(credit - debit) - voucher.amount
        return res
   
    def onchange_line_ids(self, cr, uid, ids, line_dr_ids, line_cr_ids, amount, voucher_currency, type, context=None):
        context = context or {}
        if not line_dr_ids and not line_cr_ids:
            return {'value':{}}
        line_osv = self.pool.get("account.voucher.line")
        for line in line_cr_ids:
            if line[1] and line[2]:
                account_voucher_line = line_osv.browse(cr, uid, line[1])
                move_line_id = account_voucher_line.move_line_id
                line[2]['move_line_id'] = move_line_id.id
        line_dr_ids = resolve_o2m_operations(cr, uid, line_osv, line_dr_ids, ['amount'], context)
        line_cr_ids = resolve_o2m_operations(cr, uid, line_osv, line_cr_ids, ['amount'], context)

        #loop into the lines to see if there is an amount allocated on a voucher line with a currency different than the voucher currency
        is_multi_currency = False
        for voucher_line in line_dr_ids+line_cr_ids:
            if voucher_line.get('currency_id',False) != voucher_currency:
                is_multi_currency = True
                break
            
        # HACK: 06.07.2015 09:01:25: jool1: set payment_option to without_writeoff if amount is 0
        writeoff_amount = self._compute_writeoff_amount(cr, uid, line_dr_ids, line_cr_ids, amount, type)
        if abs(writeoff_amount) < 0.0000000001:
            return {'value': {'writeoff_amount': writeoff_amount,
                              'payment_option': 'without_writeoff',
                              'open_amount_invoice': self._get_open_amount_invoice_get(cr, uid, ids, line_dr_ids, line_cr_ids, context=None) }}
        return {'value': {'writeoff_amount': writeoff_amount,
                          'open_amount_invoice': self._get_open_amount_invoice_get(cr, uid, ids, line_dr_ids, line_cr_ids, context=None) }}
        return super(account_voucher_extended, self).onchange_line_ids(self, cr, uid, ids, line_dr_ids, line_cr_ids, amount, voucher_currency, type, context)
    
    def _get_open_amount_invoice_get(self, cr, uid, ids, line_dr_ids, line_cr_ids, context=None):
#        print '_get_open_amount_invoice_get'
        if not ids: return 0
        res = {}
        invoice_obj = self.pool.get('account.invoice')
        account_move_line_obj = self.pool.get('account.move.line')
        total = 0.0
        total_voucher = 0.0
        is_other_currency = False
        inv_ids = []
        for line in self.browse(cr, uid, ids, context=context):
            if line.line_ids:
#             print 'line.line_ids: ', line.line_ids
                for voucher_line in line.line_ids:
                    voucher_line_amount = voucher_line.amount
                    for line_dr in line_dr_ids:
                        if 'move_line_id' in line_dr and line_dr['move_line_id'] == voucher_line.move_line_id.id:
                            voucher_line_amount = line_dr['amount']
    #                        print 'voucher_line_amount dr: ', voucher_line_amount
                    for line_cr in line_cr_ids:
                        if 'move_line_id' in line_cr and line_cr['move_line_id'] == voucher_line.move_line_id.id:
                            voucher_line_amount = line_cr['amount']
    #                        print 'voucher_line_amount cr: ', voucher_line_amount
                            
    #                print 'voucher_line_amount: ', voucher_line_amount
                    total_voucher += voucher_line_amount
                    if voucher_line.move_line_id:
                        invoice_ids = invoice_obj.search(cr, uid, [('move_id','=',voucher_line.move_line_id.move_id.id)])
                        for invoice in invoice_obj.browse(cr,uid, invoice_ids,context=context):
    #                       print 'invoice.id: ', invoice.id
    #                       print 'invoice.reconciled: ', invoice.reconciled
                            if not invoice.id in inv_ids and not invoice.reconciled:
                                inv_ids.append(invoice.id)
        
                                #set current invoice, company and current currency
                                company_currency = line.journal_id.company_id.currency_id.id
                                current_currency = line.currency_id.id
                                current_currency_invoice = invoice.currency_id.id
        #                        print 'company_currency:', company_currency
        #                        print 'current_currency:', current_currency
        #                        print 'current_currency_invoice:', current_currency_invoice
                                #hack jool: if currency is equal to current currency - get amount from invoice, otherwise get amount from move_lines
                                if current_currency_invoice == current_currency:
                                    #total += invoice.amount_total
                                    total += invoice.residual
                                else:
                                    is_other_currency = True
                                    account_move_line_ids = account_move_line_obj.search(cr, uid, [('move_id','=',voucher_line.move_line_id.move_id.id)])
                                    for move_line in account_move_line_obj.browse(cr,uid, account_move_line_ids,context=context):
                                        if abs(move_line.amount_currency) == invoice.amount_total:
                                            if move_line.amount_currency < 0:
                                                total += round(move_line.credit,2)
                                            else:
                                                total += round(move_line.debit,2)

#            print 'line.amount: ', line.amount
            if line.amount:
#                print 'total:', total
#                print 'total_voucher:', total_voucher
#                print 'line.writeoff_amount:', line.writeoff_amount
                total = round(total,2) - round(total_voucher,2)

            #hack jool: if invoice of payment is in another currency than the bank statment and the total is not 0 then set -1
            if is_other_currency and total <> 0:
                return -1
                #res[line.id] = -1
            else:
                return round(total,2)
                #res[line.id] = round(total,2)
            total = total_voucher = 0.0
            inv_ids = []
        return res
        
    def _open_amount_invoice_get(self, cr, uid, ids, name, args, context=None):
        print '_open_amount_invoice_get'
        if not ids: return {}
        res = {}
        invoice_obj = self.pool.get('account.invoice')
        account_move_line_obj = self.pool.get('account.move.line')
        total = 0.0
        total_voucher = 0.0
        is_other_currency = False
        inv_ids = []
        for line in self.browse(cr, uid, ids, context=context):
            if line.line_ids:
                for voucher_line in line.line_ids:
                    total_voucher += voucher_line.amount
                    if voucher_line.move_line_id:
                        invoice_ids = invoice_obj.search(cr, uid, [('move_id','=',voucher_line.move_line_id.move_id.id)])
                        for invoice in invoice_obj.browse(cr,uid, invoice_ids,context=context):
                            if not invoice.id in inv_ids:
                                inv_ids.append(invoice.id)
        
                                #set current invoice, company and current currency
                                company_currency = line.journal_id.company_id.currency_id.id
                                current_currency = line.currency_id.id
                                current_currency_invoice = invoice.currency_id.id
                                #hack jool: if currency is equal to company currency - get amount from invoice, otherwise get amount from move_lines
                                if current_currency_invoice == current_currency:
                                    #total += invoice.amount_total
                                    total += invoice.residual
                                else:
                                    is_other_currency = True
                                    account_move_line_ids = account_move_line_obj.search(cr, uid, [('move_id','=',voucher_line.move_line_id.move_id.id)])
                                    for move_line in account_move_line_obj.browse(cr,uid, account_move_line_ids,context=context):
                                        if abs(move_line.amount_currency) == invoice.amount_total:
                                            if move_line.amount_currency < 0:
                                                total += round(move_line.credit,2)
                                            else:
                                                total += round(move_line.debit,2)

            if line.amount:
                total = round(total,2) - round(total_voucher,2)

            #hack jool: if invoice of payment is in another currency than the bank statment and the total is not 0 then set -1
            if is_other_currency and total <> 0:
                res[line.id] = -1
            else:
                res[line.id] = round(total,2)
            total = total_voucher = 0.0
            inv_ids = []
        print 'RES: ', res
        return res
        
    def _get_currency(self, cr, uid, ids, field_name, arg, context=None):
        result = {}
        for rec in self.browse(cr, uid, ids, context=context):
            if rec.journal_id.currency:
                result[rec.id] = rec.journal_id.currency.id
            else:
                result[rec.id] = rec.company_id.currency_id.id
        return result
    
    _columns = {
        'payment_difference_id':fields.many2one('payment.difference.type', 'Payment difference', required=False, readonly=True, select=True, states={'draft':[('readonly',False)]}),
        'open_amount_invoice': fields.function(_open_amount_invoice_get, type='float', readonly=True, string='Open Amount Invoice'),
        'writeoff_amount': fields.function(_get_writeoff_amount_extended, string='Difference Amount', type='float', readonly=True, help="Computed as the difference between the amount stated in the voucher and the sum of allocation on the voucher lines."),
        #hack jool
        'type_bank_statement': fields.selection([
            ('supplier','Supplier'),
            ('customer','Customer'),
            ('general','General')
            ], 'Type', required=False),
        'account_id_bank_statement': fields.many2one('account.account','Account',
            required=False),
        'currency_id': fields.function(_get_currency, type='many2one', relation='res.currency', string='Currency'),
#        'currency_id': fields.related('journal_id','currency', type='many2one', relation='res.currency', string='Currency', readonly=True),
    }
    
    
    _defaults = {
        #hack jool
        'type_bank_statement': _get_type_bank_statement,
        'account_id_bank_statement': _get_account_id_bank_statement,
    }
    
    
    def get_amount_total_paid_voucher(self, cr, uid, line_ids, context=None):
        global voucher_type
        global amount_total_paid_voucher
        global current_currency_invoice
        voucher_line_pool = self.pool.get('account.voucher.line')
        
        for line in voucher_line_pool.browse(cr, uid, line_ids, context=context):
            #set current_currency_invoice
            if line.move_line_id:
                current_currency_invoice = line.move_line_id.currency_id.id <> False and line.move_line_id.currency_id.id or company_currency
            #set amount_total_paid_voucher
            
            # HACK: 28.03.2014 06:51:24: olivier: check as well amount_unreconcile, because we should not consider these amounts with 0.0 in amount_total_paid_voucher
            if not line.amount and line.amount_unreconciled != 0:
                continue
            if voucher_type == 'receipt':
                if line.type == 'cr':
                    amount_total_paid_voucher += line.amount_unreconciled
                else:
                    amount_total_paid_voucher -= line.amount_unreconciled
            else:
                if line.type == 'cr':
                    amount_total_paid_voucher -= line.amount_unreconciled
                else:
                    amount_total_paid_voucher += line.amount_unreconciled

    def set_voucher_infos(self, cr, uid, context=None):
        global voucher
        global voucher_type
        global voucher_amount
        global amount_total_paid_voucher
        global company_currency
        global current_currency
        global current_currency_invoice
        global context_multi_currency
        global name
        global ref
        global move_pool, move_line_pool, currency_pool, tax_obj, seq_obj, account_pool, voucher_line_pool, invoice_obj
        global invoice_line_ids, skonto_line_ids, gutschrift_line_ids
        #TODO: needed?
        global all_line_ids
        global paid_to_much, paid_not_enough
        global payment_option, voucher_writeoff_amount, writeoff_acc_id, payment_difference_id, writeoff_comment, writeoff_analytic_id
        context_multi_currency = context.copy()
        context_multi_currency.update({'date': voucher.date})
        company_currency = voucher.journal_id.company_id.currency_id.id
#        current_currency = voucher.journal_id.currency.id
        current_currency = voucher.currency_id.id
        voucher_amount = voucher.amount
        
        #get name
        if voucher.number:
            name = voucher.number
        elif voucher.journal_id.sequence_id:
            name = seq_obj.get_id(cr, uid, voucher.journal_id.sequence_id.id)
        else:
            raise osv.except_osv(_('Error !'), _('Please define a sequence on the journal !'))
        #get ref
        if not voucher.reference:
            ref = name.replace('/','')
        else:
            ref = voucher.reference
            
        #voucher_type (receipt,payment)
        voucher_type = voucher.type
        #get all voucher_line id's
        all_line_ids = [x.id for x in voucher.line_ids]
        
        #get voucher_line id's depending on voucher_type
        invoice_line_ids = skonto_line_ids = gutschrift_line_ids = [] # HACK: 25.02.2014 11:37:40: olivier: set empty
        if voucher_type == 'receipt':
            #get voucher_line id's of all "Invoice lines"
            invoice_line_ids = [x.id for x in voucher.line_cr_ids if x.skonto == False]
            #get voucher_line id's of all "Skonto lines"
            skonto_line_ids = [x.id for x in voucher.line_cr_ids if x.skonto == True]
            #get voucher_line id's of all "Gutschriften lines"
            gutschrift_line_ids = [x.id for x in voucher.line_dr_ids] 
        if voucher_type == 'payment':
            #get voucher_line id's of all "Invoice lines"
            invoice_line_ids = [x.id for x in voucher.line_dr_ids if x.skonto == False]
            #get voucher_line id's of all "Skonto lines"
            skonto_line_ids = [x.id for x in voucher.line_dr_ids if x.skonto == True]
            #get voucher_line id's of all "Gutschriften lines"
            gutschrift_line_ids = [x.id for x in voucher.line_cr_ids]

        #paid to much
        paid_to_much = 0
        paid_not_enough = False
        currency_difference_writeoff_less_than_0_5 = 0
        #TODO: Delete
        #book_tolerance_as_skonto = False
        self.get_amount_total_paid_voucher(cr, uid, invoice_line_ids + gutschrift_line_ids, context)
        if voucher_amount > amount_total_paid_voucher:
            paid_to_much = voucher_amount - amount_total_paid_voucher
        ##TODO: Delete
        #if voucher_amount < amount_total_paid_voucher:
        #    paid_to_less = amount_total_paid_voucher - voucher_amount
        
        payment_option = voucher.payment_option
        voucher_writeoff_amount = voucher.writeoff_amount
        writeoff_acc_id = voucher.writeoff_acc_id
        payment_difference_id = voucher.payment_difference_id
        writeoff_comment = voucher.comment
        writeoff_analytic_id = voucher.analytic_id
          
    def create_move_id(self, cr, uid, context=None):
        global voucher
        global name
        global ref
        global move_pool, move_line_pool, currency_pool, tax_obj, seq_obj, account_pool, voucher_line_pool, invoice_obj
        move = {
            'name': name,
            'journal_id': voucher.journal_id.id,
            'narration': voucher.narration,
            'date': voucher.date,
            'ref': ref,
            'period_id': voucher.period_id and voucher.period_id.id or False
        }
        return move_pool.create(cr, uid, move)
    
    def create_first_move_line(self, cr, uid, move_id, context=None):
        global voucher
        global voucher_type
        global voucher_amount
        global name
        global ref
        global move_pool, move_line_pool, currency_pool, tax_obj, seq_obj, account_pool, voucher_line_pool, invoice_obj
        global company_currency
        global current_currency
        global current_currency_invoice
        global context_multi_currency
        global debit, credit, line_total, line_total
        global sign
        #set debit and credit
        debit = 0.0
        credit = 0.0
        if voucher_type in ('sale', 'receipt'):
            debit = round(currency_pool.compute(cr, uid, current_currency, company_currency, voucher_amount, context=context_multi_currency, round=False),2)
        elif voucher_type in ('purchase', 'payment'):
            credit = round(currency_pool.compute(cr, uid, current_currency, company_currency, voucher_amount, context=context_multi_currency, round=False),2)
        if debit < 0:
            credit = -debit
            debit = 0.0
        if credit < 0:
            debit = -credit
            credit = 0.0
        
        #set line_total
        line_total = round(debit,2) - round(credit,2)
        #TODO Ask Silvan -> where can I set the tax_amount???
        if voucher_type == 'sale':
            line_total = line_total - round(currency_pool.compute(cr, uid, voucher.currency_id.id, company_currency, voucher.tax_amount, context=context_multi_currency, round=False),2)
        elif voucher_type == 'purchase':
            line_total = line_total + round(currency_pool.compute(cr, uid, voucher.currency_id.id, company_currency, voucher.tax_amount, context=context_multi_currency, round=False),2)
        line_total = round(line_total,2)

        #set amount for sign_voucher_amount - if current_currency_invoice is not like current_currency
        amount = voucher_amount
        if current_currency <> current_currency_invoice:
            amount = round(currency_pool.compute(cr, uid, current_currency, current_currency_invoice, amount, context=context_multi_currency, round=False),2)
        sign = round(debit,2) - round(credit,2) < 0 and -1 or 1
        if current_currency <> company_currency:
            sign_voucher_amount = sign * voucher_amount
        else:
            sign_voucher_amount = sign * amount
        sign_voucher_amount = (str(round(sign_voucher_amount,2)))
        #create the first line of the voucher
        move_line = {
            'name': voucher.name or '/',
            'debit': (str(round(debit,2))),
            'credit': (str(round(credit,2))),
            'account_id': voucher.account_id.id,
            'move_id': move_id,
            'journal_id': voucher.journal_id.id,
            'period_id': voucher.period_id.id,
            'partner_id': voucher.partner_id.id,
            'currency_id': company_currency <> current_currency and current_currency or False,
            'amount_currency': company_currency <> current_currency and sign_voucher_amount or 0.0,
            'date': voucher.date,
            'date_maturity': voucher.date_due,
            'bank_statement_line_id': self.pool.get('account.bank.statement.line').search(cr, uid, [('voucher_id','=',voucher.id)], context=context) and self.pool.get('account.bank.statement.line').search(cr, uid, [('voucher_id','=',voucher.id)], context=context)[0] or False,
        }
        print '####################################################################################'
        print 'first move_line: ', move_line
        move_line_pool.create(cr, uid, move_line)
#        print 'line_total1: ', line_total
        print '####################################################################################'
    
    def calculate_currency_differences(self, cr, uid, line, context=None):
#        global context_multi_currency
#        global sign
        #get type of invoice (supplier or customer)
#        account_bank_statement_line_pool = self.pool.get('account.bank.statement.line')
#        bank_statement_line_id = account_bank_statement_line_pool.search(cr, uid, [('voucher_id','=',voucher.id)])[0]
#        bank_statement_line_type = account_bank_statement_line_pool.browse(cr,uid, bank_statement_line_id,context=context).type
                
        #get all payments of line.move_line_id
        #account_move_line_ids = move_line_pool.search(cr, uid, [('move_id','=',voucher_line.move_line_id.move_id.id)])
#        print 'GET PAYMENTS'
        #print 'line.move_line_id.id: ', line.move_line_id.id
        #print 'line.move_line_id.move_id.id: ', line.move_line_id.move_id.id
        #print 'line.move_line_id.reconcile_partial_id: ', line.move_line_id.reconcile_partial_id
        
        context_multi_currency_ausgleich = context_multi_currency.copy()
        context_multi_currency_ausgleich.update({'date': line.move_line_id.date})  
        
        total_payments = 0
        partial_payment = False
        #if foreign currency paid over CHF journal -> set amount_original as to_pay
        if current_currency != current_currency_invoice and company_currency == current_currency:
            payments= []
            if line.move_line_id.reconcile_partial_id:
                payments = move_line_pool.search(cr, uid, [('id','!=',line.move_line_id.id),('reconcile_partial_id','=',line.move_line_id.reconcile_partial_id.id)])
            for payment in move_line_pool.browse(cr,uid, payments,context=context):
                total_payments += payment['debit']
                total_payments -= payment['credit']
            
            total_payments = abs(total_payments)
#            print 'total_payments: ', total_payments
#            print 'line.amount: ', line.amount
            #convert line.amount to eur and back to chf
            #first convert line.amount to current_currency_invoice
            line_amount = round(currency_pool.compute(cr, uid, current_currency, current_currency_invoice, line.amount, context=context_multi_currency, round=False),2)
#            print 'line_amount1: ', line_amount
            #then convert it back to current_currency
            line_amount = round(currency_pool.compute(cr, uid, current_currency_invoice, current_currency, line_amount, context=context_multi_currency_ausgleich, round=False),2)
#            print 'line_amount2: ', line_amount
#                        print 'line_amount 3: ', line_amount
            
#                            diff_currency_correct = (abs(diff_currency_correct) + 0.01)*sign
#                        elif round(abs(amount_pay_in_chf-amount_residual_total_without_skonto),2) == round((abs(diff_currency_correct) -0.01),2):
#                            diff_currency_correct = (abs(diff_currency_correct) - 0.01)*sign
            
#                        if abs(line.amount_original) - (line.amount+total_payments) == 0:

#            print 'round(abs(line.amount_original),2): ', round(abs(line.amount_original),2)
#            print 'round((line_amount+total_payments),2): ', round((line_amount+total_payments),2) 
#            print 'round((line_amount+total_payments + 0.01),2): ', round((line_amount+total_payments + 0.01),2)
#            print 'round((line_amount+total_payments - 0.01),2): ', round((line_amount+total_payments - 0.01),2)
#
#            print 'if 1: ', round(abs(line.amount_original),2) - round((line_amount+total_payments),2) == 0
#            print 'if 2', round(abs(line.amount_original),2) - round((line_amount+total_payments + 0.01),2) == 0
#            print 'if 3: ', round(abs(line.amount_original),2) - round((line_amount+total_payments - 0.01),2) == 0
            
            if bt_format.check_if_zero(round(abs(line.amount_original),2) - round((line_amount+total_payments),2)) or bt_format.check_if_zero(round(abs(line.amount_original),2) - round((line_amount+total_payments + 0.01),2)) or bt_format.check_if_zero(round(abs(line.amount_original),2) - round((line_amount+total_payments - 0.01),2)):
#                print 'Keine Teilzahlung - Restzahlung'
                line_amount = abs(line.amount_original)
                amount_pay = line_amount
            else:
#                print 'Teilzahlung'
                #set partial_payment to True if there was already a partial_payment on this invoice
                if total_payments != 0:
                    partial_payment = True
                line_amount = line.amount
            
                #hacko jool: TEST if ok!!!!
                #first convert line.amount to current_currency_invoice
#                        amount_pay = currency_pool.compute(cr, uid, current_currency, current_currency_invoice, line.amount, context=context_multi_currency)
                amount_pay = round(currency_pool.compute(cr, uid, current_currency, current_currency_invoice, line_amount, context=context_multi_currency, round=False),2)
                #then convert it back to current_currency
                amount_pay = round(currency_pool.compute(cr, uid, current_currency_invoice, current_currency, amount_pay, context=context_multi_currency_ausgleich, round=False),2)
                sign_amount_pay = sign * amount_pay
                sign_amount_pay = (str(round(sign_amount_pay,2)))
                to_pay = sign_amount_pay
                
            to_pay = amount_pay
#            print 'to_pay: ',to_pay
            
#                        to_pay = line.amount_original
        else:
#                        print 'TEEEEEEST line: ', line
#                        print 'TEEEEEEST line.amount: ', line.amount
#                        print 'TEEEEEEST line.amount_original: ', line.amount_original
#                        print 'TEEEEEEST line.amount_unreconciled: ', line.amount_unreconciled
#                        print 'context_multi_currency_ausgleich: ', context_multi_currency_ausgleich
#                        print 'amount_residual_total_without_skonto: ', amount_residual_total_without_skonto
            
            #hack jool
            #Teilzahlung?
            payments = []
            if line.move_line_id.reconcile_partial_id:
                payments = move_line_pool.search(cr, uid, [('id','!=',line.move_line_id.id),('reconcile_partial_id','=',line.move_line_id.reconcile_partial_id.id)])
#           print 'payments: ', payments
            
            for payment in move_line_pool.browse(cr, uid, payments, context=context):
                total_payments += abs(payment['amount_currency'])
            #total_payments -= payment['credit']
            
#            print 'total_payments: ', total_payments
            
            if bt_format.check_if_zero(abs(line.amount_original) - (line.amount + total_payments)):
#                print 'Keine Teilzahlung - Restzahlung'
                #if reconcile is set -> get debit and credit from move_line
                if not line.reconcile:
                    line_amount = abs(line.amount_original)
            else:
#                print 'Teilzahlung'
                #set partial_payment to True if there was already a partial_payment on this invoice
                if total_payments != 0:
                    partial_payment = True
                line_amount = line.amount
                
            if line.reconcile:
                to_pay = abs(line.move_line_id.credit - line.move_line_id.debit)
            else:
                to_pay = round(currency_pool.compute(cr, uid, current_currency, company_currency, line_amount, round=False, context=context_multi_currency_ausgleich),2)
#        print 'to_pay 1: ', to_pay
        if line.move_line_id.reconcile_partial_id:
#            print 'TEEEEST'
#            print 'line.amount_unreconciled: ', line.amount_unreconciled
#            print 'line.amount: ', line.amount
#            print 'line.amount_original: ', line.amount_original
            
            #if foreign currency paid over CHF journal -> set amount_original as to_pay
            if current_currency != current_currency_invoice and company_currency == current_currency:
                #first convert line.amount to current_currency_invoice
#                        amount_pay = currency_pool.compute(cr, uid, current_currency, current_currency_invoice, line.amount, context=context_multi_currency)
                line_amount = round(currency_pool.compute(cr, uid, current_currency, current_currency_invoice, line.amount, context=context_multi_currency, round=False),2)
#                print 'line_amount 2: ', line_amount
                #then convert it back to current_currency
                line_amount = round(currency_pool.compute(cr, uid, current_currency_invoice, current_currency, line_amount, context=context_multi_currency_ausgleich, round=False),2)
#                print 'line_amount 3: ', line_amount
                
#                            if abs(line.amount_original) - (line_amount+total_payments) == 0:
                if bt_format.check_if_zero(round(abs(line.amount_original),2) - round((line_amount+total_payments),2)) or bt_format.check_if_zero(round(abs(line.amount_original),2) - round((line_amount+total_payments + 0.01),2)) or bt_format.check_if_zero(round(abs(line.amount_original),2) - round((line_amount+total_payments - 0.01),2)):
                    payments = move_line_pool.search(cr, uid, [('id','!=',line.move_line_id.id),('reconcile_partial_id','=',line.move_line_id.reconcile_partial_id.id),('currency_difference','=',False)])
                else:
                    payments = move_line_pool.search(cr, uid, [('id','!=',line.move_line_id.id),('reconcile_partial_id','=',line.move_line_id.reconcile_partial_id.id)])
            else:
                #if line.amount_unreconciled - line.amount == 0:
                if bt_format.check_if_zero(abs(line.amount_original) - (line.amount+total_payments)):
                    payments = move_line_pool.search(cr, uid, [('id','!=',line.move_line_id.id),('reconcile_partial_id','=',line.move_line_id.reconcile_partial_id.id),('currency_difference','=',False)])
                else:
                    payments = move_line_pool.search(cr, uid, [('id','!=',line.move_line_id.id),('reconcile_partial_id','=',line.move_line_id.reconcile_partial_id.id)])
            #print 'payments: ', payments
            if len(payments) > 0 and not partial_payment:
#                print 'HAS PAYMENTS'
                #print 'payments: ', payments
                for payment in move_line_pool.browse(cr,uid, payments,context=context):
#                                print 'payment: ', payment
#                                print 'payment debit: ', payment.debit
#                                print 'payment credit: ', payment.credit
#                                print 'payment.amount_currency: ', payment.amount_currency
                    if payment.amount_currency < 0:
                        to_pay -= payment.credit
                        to_pay += payment.debit
                    else:
                        to_pay += payment.credit
                        to_pay -= payment.debit
#                    print 'to_pay 2: ', to_pay    
                #    print 'payment.move_id.id: ', payment.move_id.id
                    #get kursdifferenzen already booked out
                    payment_lines = move_line_pool.search(cr, uid, [('move_id','=',payment.move_id.id),('currency_difference','=',True),('reconcile_partial_id','=',line.move_line_id.reconcile_partial_id.id)])
                #    print 'payment_lines: ', payment_lines
                    for payment_line in move_line_pool.browse(cr,uid, payment_lines,context=context):
#                                    print 'payment_line: ', payment_line
#                                    print 'payment_line debit: ', payment_line.debit
#                                    print 'payment_line credit: ', payment_line.credit
#                                    print 'payment_line.amount_currency: ', payment_line.amount_currency
                        if payment.amount_currency < 0:
                            to_pay -= payment_line.credit
                            to_pay += payment_line.debit
                        else:
                            to_pay += payment_line.credit
                            to_pay -= payment_line.debit
#                        print 'to_pay 3: ', to_pay
        
#                    print 'line.amount_unreconciled: ', line.amount_unreconciled
#                    print 'line.amount: ', line.amount
        
        #set line_amount_unreconciled
        #decide if it is "Restzahlung" or "Teilzahlung"
        #Teilzahlung?
        
        #JOOL todo: test if this is needed?????
#                    if line.amount_unreconciled - line.amount == 0:
#                        print 'Keine Teilzahlung (Restzahlung)'
#                        if abs(line.amount_original) - abs(line.amount) == 0:
#                            line_amount_unreconciled = line.amount
#                        else:
#                            line_amount_unreconciled = line.amount_unreconciled
#                    else:
#                        print 'Teilzahlung'
##                        line_amount_unreconciled = line.amount_unreconciled
#                        line_amount_unreconciled = line.amount

#        print 'line.amount_unreconciled a: ', line.amount_unreconciled
#        print 'line.amount a: ', line.amount_unreconciled
        if bt_format.check_if_zero(line.amount_unreconciled - line.amount):
#            print 'Keine Teilzahlung (Restzahlung)'
            line_amount_unreconciled = line.amount
        else:
#            print 'Teilzahlung'
#                        line_amount_unreconciled = line.amount_unreconciled
            line_amount_unreconciled = line.amount
#        print 'line_amount_unreconciled b: ', line_amount_unreconciled    
#                    print 'line_amount_unreconciled1: ', line_amount_unreconciled
#                    print 'context_multi_currency: ', context_multi_currency
        if not (current_currency != current_currency_invoice and company_currency == current_currency):
            line_amount_unreconciled = round(currency_pool.compute(cr, uid, current_currency, company_currency, line_amount_unreconciled, context=context_multi_currency, round=False),2)
        #get total difference
#        print 'to_pay 4: ', to_pay
        
        diff_total = to_pay - line_amount_unreconciled
#        print 'diff_total: ', diff_total
#        print 'line_amount_unreconciled2: ', line_amount_unreconciled
#        print 'line.amount: ', line.amount
        
        #Faktorberechnung der Kursdifferenz if foreign currency paid over CHF journal 
        if current_currency != current_currency_invoice and company_currency == current_currency:
#             if line_amount_unreconciled == 0.0 => diff_currency_correct must be 0 (instead of division by zero)
            if line_amount_unreconciled:
                diff_factor = diff_total/line_amount_unreconciled*line.amount
                print '-------------------diff_factor if: ', diff_factor
                diff_currency_correct = diff_factor
            else:
                print '-------------------diff_factor if: (line_amount_unreconciled = 0.0)', 0
                diff_currency_correct = 0
        else:
            print '-------------------diff_total else: ', diff_total
            diff_currency_correct = diff_total
        return diff_currency_correct
    
    def calculate_amount_pay_in_chf(self, cr, uid, line, context=None):
        global line_amount_compare, line_amount_unreconciled_compare, amount_pay_in_chf, paid_not_enough
        ##paid to much
        if round(line_amount_compare,2) > round(line_amount_unreconciled_compare,2):
#            print '1if - paid to much'
            #if paid to much - set line_amount to line.amount_unreconciled
            context_multi_currency_ausgleich = context_multi_currency.copy()
            #calculate amount_pay_in_chf from invoice date if this line is the skonto
            if line.skonto:
                context_multi_currency_ausgleich.update({'date': line.move_line_id.date})  
            line_amount = line_amount_unreconciled_compare
            #set line_amount to amount_unreconciled if foreign currency paid over CHF journal
            if current_currency != current_currency_invoice and company_currency == current_currency:
                line_amount = line_amount_unreconciled_compare
            else:
                line_amount = line_amount_compare
            amount_pay_in_chf = round(currency_pool.compute(cr, uid, current_currency, company_currency, line_amount, context=context_multi_currency_ausgleich, round=False),2)
            context_multi_currency_ausgleich = context_multi_currency.copy()
            context_multi_currency_ausgleich.update({'date': line.move_line_id.date})  
            #set amount_pay_in_chf after calculation
            if current_currency != current_currency_invoice and company_currency == current_currency:
                line_amount = line_amount_compare
                amount_pay_in_chf = round(currency_pool.compute(cr, uid, current_currency, company_currency, line_amount, context=context_multi_currency_ausgleich, round=False),2)
        #paid not enough
        elif round(line_amount_compare,2) < round(line_amount_unreconciled_compare,2):
#            print '2elif - paid not enough'
            paid_not_enough = True
            #calculate amounts for currency difference from date of invoice and not from date of voucher
            context_multi_currency_ausgleich = context_multi_currency.copy()
            #calculate amount_pay_in_chf from invoice date if this line is the skonto
            if line.skonto:
                context_multi_currency_ausgleich.update({'date': line.move_line_id.date})  
            #set line_amount to amount_unreconciled if foreign currency paid over CHF journal
            if current_currency != current_currency_invoice and company_currency == current_currency:
                line_amount = line_amount_unreconciled_compare
            else:
                line_amount = line_amount_compare
            amount_pay_in_chf = round(currency_pool.compute(cr, uid, current_currency, company_currency, line_amount, context=context_multi_currency_ausgleich, round=False),2)
            context_multi_currency_ausgleich = context_multi_currency.copy()
            context_multi_currency_ausgleich.update({'date': line.move_line_id.date})  
            #set amount_pay_in_chf after calculation
            if current_currency != current_currency_invoice and company_currency == current_currency:
                line_amount = line_amount_compare
                amount_pay_in_chf = round(currency_pool.compute(cr, uid, current_currency, company_currency, line_amount, context=context_multi_currency_ausgleich, round=False),2)
        else:
#            print '3else - '
            #calculate amounts for currency difference from date of invoice and not from date of voucher
            context_multi_currency_ausgleich = context_multi_currency.copy()
            #calculate amount_pay_in_chf from invoice date if this line is the skonto
            if line.skonto:
                context_multi_currency_ausgleich.update({'date': line.move_line_id.date})
#                    print 'context_multi_currency_ausgleich: ', context_multi_currency_ausgleich
#                    print 'line.untax_amount: ', line.untax_amount
#                    print 'line_amount_compare: ', line_amount_compare
            #set line_amount to amount_unreconciled if foreign currency paid over CHF journal
            if current_currency != current_currency_invoice and company_currency == current_currency:
                line_amount = line_amount_unreconciled_compare
            else:
                line_amount = line_amount_compare
            
            if line.skonto:
                amount_pay_in_chf = line.move_line_id.amount_residual
            else:
                amount_pay_in_chf = round(currency_pool.compute(cr, uid, current_currency, company_currency, line.untax_amount or line_amount, context=context_multi_currency_ausgleich, round=False),2)
            context_multi_currency_ausgleich = context_multi_currency.copy()
            context_multi_currency_ausgleich.update({'date': line.move_line_id.date})  
            #set amount_pay_in_chf after calculation
            if current_currency != current_currency_invoice and company_currency == current_currency:
                line_amount = line_amount_compare
                amount_pay_in_chf = round(currency_pool.compute(cr, uid, current_currency, company_currency, line.untax_amount or line_amount, context=context_multi_currency_ausgleich, round=False),2)
        
    def calculate_currency_correct(self, cr, uid, diff_currency_correct, line, context=None):
        global amount_pay_in_chf, voucher_type, diff_currency_correct_dict, amount_residual_total_without_skonto
        print 'diff_currency_correct calculate_currency_correct: ', diff_currency_correct
        sign = diff_currency_correct < 0 and -1 or 1
        if round(abs(amount_pay_in_chf-amount_residual_total_without_skonto),2) == round((abs(diff_currency_correct) + 0.01),2):
            diff_currency_correct = (abs(diff_currency_correct) + 0.01)*sign
        elif round(abs(amount_pay_in_chf-amount_residual_total_without_skonto),2) == round((abs(diff_currency_correct) -0.01),2):
            diff_currency_correct = (abs(diff_currency_correct) - 0.01)*sign
        print 'diff_currency_correct 3: ', diff_currency_correct
        
        if voucher_type in ('purchase', 'payment'):
            if line.type == 'cr':
                diff_currency_correct = diff_currency_correct*-1
        elif voucher_type in ('sale', 'receipt'):
            if line.type == 'dr':
                diff_currency_correct = diff_currency_correct*-1
        
        print 'CURRENCY_DIFFERENCE NEW: ', diff_currency_correct
        if diff_currency_correct <> 0:
            #TODO test the "if" (with more than one line!!)
#            print 'LINE.TYPE: ', line.type
            if line.move_line_id.move_id in diff_currency_correct_dict:
                #IS ALREADY IN DICT
                diff = diff_currency_correct_dict[line.move_line_id][1]
                diff += round(diff_currency_correct,2)
                print 'diff diff_currency_correct: ', diff
                #diff_currency_correct_dict[line.move_line_id.move_id][1] += round(diff_currency_correct,2)
                diff_currency_correct_dict[line.move_line_id][1] += diff
            else:
                #IS NEW IN DICT
                dict = {
                        'type': line.type,
                        'is_gutschrift': line.id in gutschrift_line_ids, 
                        'diff_currency_correct': round(diff_currency_correct,2),
                        }
#                        diff_currency_correct_dict[line.move_line_id] = round(diff_currency_correct,2)
                diff_currency_correct_dict[line.move_line_id] = dict

    def calculate_amount_currency(self, cr, uid, line, context=None):
        amount_currency = 0
            
        #hack jool: if invoice has another currency than the current - set amount_currency
        if line.move_line_id and current_currency <> current_currency_invoice:
#                    print '###############################################################################################################'
#                    print 'current_currency is different from invoice_currency'
            #amount_currency = line.move_line_id.amount_currency * -1
            #print 'line.move_line_id.currency_id.id: ', line.move_line_id.currency_id.id
            if bt_format.check_if_zero(line.move_line_id.debit):
                amount_currency = line.move_line_id.amount_currency * -1
            else:
                amount_currency = line.move_line_id.amount_currency
#            print 'amount_currency: ', amount_currency
            #calculate amount_currency
        return amount_currency
    
    def create_move_line(self, cr, uid, line, amount_currency, context=None):
        global voucher
        global move_id
        global amount_pay_in_chf
        global line_total
        global gutschriften_added
        global rec_list_ids
        global move_line_id_of_write_off
        global voucher_writeoff_amount
        global writeoff_amount
        global last_move_line_id
        global invoice_account_id
        global count_ids
        global sign
        #save account_id to book currency difference
        invoice_account_id = line.account_id.id
        move_line = {
            'journal_id': voucher.journal_id.id,
            'period_id': voucher.period_id.id,
            'name': line.name and line.name or '/',
            'account_id': line.account_id.id,
            'move_id': move_id,
            'partner_id': voucher.partner_id.id,
            'currency_id': company_currency <> current_currency_invoice and current_currency_invoice or False,
            'amount_currency': 0.0,
            'analytic_account_id': line.account_analytic_id and line.account_analytic_id.id or False,
            'quantity': 1,
            'credit': 0.0,
            'debit': 0.0,
            'date': voucher.date,
            'bank_statement_line_id': self.pool.get('account.bank.statement.line').search(cr, uid, [('voucher_id','=',voucher.id)], context=context) and self.pool.get('account.bank.statement.line').search(cr, uid, [('voucher_id','=',voucher.id)], context=context)[0] or False,
        }
        
        #if leading sign of amount_pay_in_chf is negativ -> make it positiv and invert line.type
        if amount_pay_in_chf < 0:
            amount_pay_in_chf = -amount_pay_in_chf
            if line.type == 'dr':
                line.type = 'cr'
            else:
                line.type = 'dr'

        #save debit and credit into varialbes because of calculation problems
        move_line_debit = 0
        move_line_credit = 0
#        print '###############################################################################################################'
#        print 'line_total before calculating debit or credit: ', line_total
#        print 'line.type: ', line.type
        #get debit or credit for move_line and calculate line_total
        if (line.type=='dr'):
            line_total += round(amount_pay_in_chf,2)
            move_line['debit'] = (str(round(amount_pay_in_chf,2)))
            move_line_debit = round(amount_pay_in_chf,2)
        else:
            line_total -= round(amount_pay_in_chf,2)
            move_line['credit'] = (str(round(amount_pay_in_chf,2)))
            move_line_credit = round(amount_pay_in_chf,2)

#        print 'move_line_debit: ', move_line_debit
#        print 'move_line_credit: ', move_line_credit
#        print 'line_total after calculating debit or credit: ', line_total
        
        if voucher.tax_id and voucher.type in ('sale', 'purchase'):
            move_line.update({
                'account_tax_id': voucher.tax_id.id,
            })
        if move_line.get('account_tax_id', False):
            tax_data = tax_obj.browse(cr, uid, [move_line['account_tax_id']], context=context)[0]
            if not (tax_data.base_code_id and tax_data.tax_code_id):
                raise osv.except_osv(_('No Account Base Code and Account Tax Code!'),_("You have to configure account base code and account tax code on the '%s' tax!") % (tax_data.name))
        #calcultate sign because of calculation problems
        sign = (move_line_debit - move_line_credit) < 0 and -1 or 1
        #hack jool:
#        print '###############################################################################################################'
#        print '1 current_currency_invoice: ', current_currency_invoice
#        print '2 current_currency: ', current_currency
        if current_currency_invoice <> current_currency:
            #--------------------------------------------------------------------------------------------
            #hack jool: Berechne ob Zahlbetrag (Kurs vom Datum der Erstellung) mit dem amount_currency uebereinstimmt, d.h. der ganze Betrag wurde bezahlt
#                    print '--------------------------------------------------------------------------------------------'
#            print 'TRUE current_currency_invoice <> current_currency'
#                    print 'line.move_line_id.date: ', line.move_line_id.date
            context_currency = context_multi_currency.copy()
            if line.skonto:
                context_currency.update({'date': line.move_line_id.date})
#                    print 'context_currency: ', context_currency
#                    print 'line.amount: ', line.amount
#                    print 'line.move_line_id.amount_residual: ', line.move_line_id.amount_residual
            amount_pay = round(currency_pool.compute(cr, uid, current_currency, current_currency_invoice, line.amount, context=context_currency, round=False),2)
            #amount_pay = currency_pool.compute(cr, uid, current_currency, current_currency_invoice, line.move_line_id.amount_residual, context=context_currency)
            #der volle Betrag wurde bezahlt
#            print '3 amount_pay: ', amount_pay
#            print '4 amount_currency: ', amount_currency
            sign_amount_currency = sign * amount_currency
            sign_amount_currency = (str(round(sign_amount_currency,2)))
            
            
            #if paid_not_enough:
            #    line_amount = voucher.amount
            #else:
            #    line_amount = line.amount
            if amount_currency != 0:
                if abs(amount_pay-amount_currency) <= 0.05:
                    move_line['amount_currency'] = sign_amount_currency
                #nur Teilbetrag wurde bezahlt
                else:
                    amount_pay = round(currency_pool.compute(cr, uid, current_currency, current_currency_invoice, line.amount, context=context_multi_currency, round=False),2)
                    sign_amount_pay = sign * amount_pay
                    sign_amount_pay = (str(round(sign_amount_pay,2)))
                    move_line['amount_currency'] = sign_amount_pay
#            print 'XXXXXXXXXXXXXXXXXXX move_line[amount_currency]: ', move_line['amount_currency']
#                    print 'line.amount: ', line.amount
#                    print 'amount_currency: ', amount_currency
            
        else:
#            print 'FALSE current_currency_invoice <> current_currency'
#                    print 'paid_not_enough: ', paid_not_enough
#                    print 'voucher.amount: ', voucher.amount
            
            if paid_not_enough:
                line_amount = voucher.amount
            else:
                line_amount = line.amount
                
#            print 'line.amount_unreconciled: ', line.amount_unreconciled
            if round(line_amount,2) > round(line.amount_unreconciled,2):
                line_amount = line.amount_unreconciled
                sign_line_amount = sign * line_amount
            else:
                #plus gutschriften
                sign_line_amount = sign * line_amount
                #TODO: add Gutschriften?? when??
#                for voucher_line_gs in voucher_line_pool.browse(cr, uid, gutschrift_line_ids, context=context):
#                    if line.id != voucher_line_gs.id:
#                        #just add to sign_line_amount if not already added to another payment line!
#                        if voucher_line_gs.id not in gutschriften_added:
#                            sign_line_amount += voucher_line_gs.amount
#                            gutschriften_added.append(voucher_line_gs.id)

            sign_line_amount = (str(round(sign_line_amount,2)))
            move_line['amount_currency'] = company_currency <> current_currency and sign_line_amount or 0.0
#                move_line['amount_currency'] = company_currency <> current_currency and sign * line.amount or 0.0
        #print 'move_line[amount_currency]', move_line['amount_currency']
        #print 'move_line[debit]: ', move_line['debit']
        #print 'move_line[credit]: ', move_line['credit']
        #print 'company_currency: ', company_currency 
        #print 'current_currency:', current_currency
        #print 'sign: ', sign
        #print 'line.amount: ', line.amount
        #print 'voucher.currency_id.id: ', voucher.currency_id.id
        print '####################################################################################'
        print 'move_line: ', move_line
        print 'line_total2: ', line_total
        print '####################################################################################'
        voucher_line = move_line_pool.create(cr, uid, move_line)
        
#                print 'count_ids: ', count_ids
#                
#        print 'voucher.writeoff_amount:', voucher_writeoff_amount
#        print 'amount_pay_in_chf: ', amount_pay_in_chf
#        print 'DO SET move_line_id_of_write_off 1'
        if round(voucher_writeoff_amount,2) == round(amount_pay_in_chf,2):
#            print 'SET move_line_id_of_write_off 1'
            move_line_id_of_write_off = line.move_line_id.id
        last_move_line_id = line.move_line_id.id
        #hack jool: writeoff_amount is everytime the voucher.writeoff_amount?? is this ok?? 
        #NO!! if count_ids are 2 (means second line is the skonto) take just this amount as writeoff_amount
        #writeoff_amount = voucher.writeoff_amount
        
        if current_currency == current_currency_invoice and company_currency != current_currency:
            writeoff_amount = voucher_writeoff_amount
        else:
            if count_ids == 2:
                writeoff_amount = amount_pay_in_chf
            else:
                writeoff_amount = voucher.writeoff_amount
        
#        print 'writeoff_amount: ', writeoff_amount
        if line.move_line_id.id:
            rec_ids = [voucher_line, line.move_line_id.id]
            rec_list_ids.append(rec_ids)
    
    def create_move_lines(self, cr, uid, context=None):
        global voucher
        global voucher_type
        global voucher_amount
        global amount_total_paid_voucher
        global company_currency
        global current_currency
        global current_currency_invoice
        global context_multi_currency
        global name
        global move_pool, move_line_pool, currency_pool, tax_obj, seq_obj, account_pool, voucher_line_pool, invoice_obj
        global debit, credit, line_total
        global invoice_line_ids, skonto_line_ids, gutschrift_line_ids
        global paid_to_much, paid_not_enough
        global payment_option, voucher_writeoff_amount, writeoff_acc_id, payment_difference_id, writeoff_comment, writeoff_analytic_id
        global diff_currency_correct, amount_residual_total_without_skonto, voucher_line_type
        
        global line_amount_compare, line_amount_unreconciled_compare, diff_currency_correct_dict, gutschriften_added, rec_list_ids, line_type_debit, voucher_line
        ########################################################################################################
        #print all important infos
#        print 'voucher_type:                 ', voucher_type
#        print 'invoice_line_ids:             ', invoice_line_ids
#        print 'skonto_line_ids:              ', skonto_line_ids
#        print 'gutschrift_line_ids:          ', gutschrift_line_ids
#        print 'voucher_amount:               ', voucher_amount
#        print 'amount_total_paid_voucher:    ', amount_total_paid_voucher
#        print 'company_currency:             ', company_currency
#        print 'current_currency:             ', current_currency
#        print 'current_currency_invoice:     ', current_currency_invoice
#        print 'context_multi_currency:       ', context_multi_currency
#        print 'payment_option:               ', payment_option
#        print 'voucher_writeoff_amount:      ', voucher_writeoff_amount
#        print 'writeoff_acc_id:              ', writeoff_acc_id
#        print 'payment_difference_id:        ', payment_difference_id
#        print 'writeoff_comment:             ', writeoff_comment
#        print 'writeoff_analytic_id:         ', writeoff_analytic_id
        
        #invoice_line_ids
        for line in voucher_line_pool.browse(cr, uid, invoice_line_ids, context=context):
            # HACK: 28.03.2014 06:51:24: olivier: check as well amount_unreconcile, because it should be possible to set 0.0 invoices as reconciled
            #create one move line per voucher line where amount is not 0.0
            if not line.amount and line.amount_unreconciled != 0:
                continue
            #set voucher_line_type at the first time / then compare them with the next voucher_lines -> if they are equal they are still invoices, if not they are credits 
            if not voucher_line_type:
                voucher_line = line
                voucher_line_type = line.type
                if line.move_line_id:
                    amount_residual_total_without_skonto = line.move_line_id.amount_residual
                else:
                    #get name and ref from account_bank_statement_line of current voucher
                    account_bank_statement_line_pool = self.pool.get('account.bank.statement.line')
                    bank_statement_line_id = account_bank_statement_line_pool.search(cr, uid, [('voucher_id', '=', voucher.id)])[0]
                    bank_statement_line = account_bank_statement_line_pool.browse(cr, uid, bank_statement_line_id, context=context)
                    raise osv.except_osv(_('Error !'), _('Voucher of "%s" is not correct, please recreate voucher and edit it again!') % (bank_statement_line.name + ' - ' + bank_statement_line.ref))
                
            else:
                if voucher_line_type == line.type:
                    if line.move_line_id:
                        amount_residual_total_without_skonto += line.move_line_id.amount_residual
                    else:
                        #get name and ref from account_bank_statement_line of current voucher
                        account_bank_statement_line_pool = self.pool.get('account.bank.statement.line')
                        bank_statement_line_id = account_bank_statement_line_pool.search(cr, uid, [('voucher_id', '=', voucher.id)])[0]
                        bank_statement_line = account_bank_statement_line_pool.browse(cr, uid, bank_statement_line_id, context=context)
                        raise osv.except_osv(_('Error !'), _('Voucher of "%s" is not correct, please recreate voucher and edit it again!') % (bank_statement_line.name + ' - ' + bank_statement_line.ref))
                else:
                    if line.move_line_id:
                        amount_residual_total_without_skonto = line.move_line_id.amount_residual
                    else:
                        #get name and ref from account_bank_statement_line of current voucher
                        account_bank_statement_line_pool = self.pool.get('account.bank.statement.line')
                        bank_statement_line_id = account_bank_statement_line_pool.search(cr, uid, [('voucher_id', '=', voucher.id)])[0]
                        bank_statement_line = account_bank_statement_line_pool.browse(cr, uid, bank_statement_line_id, context=context)
                        raise osv.except_osv(_('Error !'), _('Voucher of "%s" is not correct, please recreate voucher and edit it again!') % (bank_statement_line.name + ' - ' + bank_statement_line.ref))
                    
            #set current_currency_invoice
            current_currency_invoice = company_currency
            if line.move_line_id:
                current_currency_invoice = line.move_line_id.currency_id.id <> False and line.move_line_id.currency_id.id or company_currency
            
            #hack jool: just ignore skonto lines if payment_difference is set!
            currency_difference_correct  = 0
            if company_currency != current_currency_invoice:
                currency_difference_correct = self.calculate_currency_differences(cr, uid, line, context)
                
#            print 'diff_currency_correct 1: ', diff_currency_correct
            line_amount_compare = abs(line.amount)
            line_amount_unreconciled_compare = abs(line.amount_unreconciled)
            
            self.calculate_amount_pay_in_chf(cr, uid, line, context)
            self.calculate_currency_correct(cr, uid, currency_difference_correct, line, context)
            amount_currency = self.calculate_amount_currency(cr, uid, line, context)
            self.create_move_line(cr, uid, line, amount_currency, context)
            
            line_type_debit = True
#            print 'TEST line.type: ', line.type
            if line.type=='cr':
                line_type_debit = False
                
        #skonto_line_ids
        for line in voucher_line_pool.browse(cr, uid, skonto_line_ids, context=context):
            # HACK: 28.03.2014 06:51:24: olivier: check as well amount_unreconcile, because it should be possible to set 0.0 invoices as reconciled
            #create one move line per voucher line where amount is not 0.0
            if not line.amount and line.amount_unreconciled != 0:
                continue
            
            # if voucher_line_type was not set in invoice_line_ids -> it means that there are no invoice_lines_ids so we have to set the type according to the first skonto_line_id
            if not voucher_line_type:
                voucher_line = line
                voucher_line_type = line.type
                line_type_debit = True
                if line.type=='cr':
                    line_type_debit = False
            
            #set current_currency_invoice
            current_currency_invoice = company_currency
            if line.move_line_id:
                current_currency_invoice = line.move_line_id.currency_id.id <> False and line.move_line_id.currency_id.id or company_currency
            
            currency_difference_correct  = 0    
            #hack jool: just ignore skonto lines if payment_difference is set!
            if company_currency != current_currency_invoice and payment_option != 'with_writeoff':
                currency_difference_correct = self.calculate_currency_differences(cr, uid, line, context)
            
#            print 'diff_currency_correct 1: ', diff_currency_correct
            line_amount_compare = abs(line.amount)
            line_amount_unreconciled_compare = abs(line.amount_original)
                
            self.calculate_amount_pay_in_chf(cr, uid, line, context)
            self.calculate_currency_correct(cr, uid, currency_difference_correct, line, context)
            amount_currency = self.calculate_amount_currency(cr, uid, line, context)
            self.create_move_line(cr, uid, line, amount_currency, context)
            
        
        #gutschrift_line_ids
        for line in voucher_line_pool.browse(cr, uid, gutschrift_line_ids, context=context):
            # HACK: 28.03.2014 06:51:24: olivier: check as well amount_unreconcile, because it should be possible to set 0.0 invoices as reconciled
            #create one move line per voucher line where amount is not 0.0
            if not line.amount and line.amount_unreconciled != 0:
                continue
            #set voucher_line_type at the first time / then compare them with the next voucher_lines -> if they are equal they are still invoices, if not they are credits 
            if voucher_line_type == line.type:
                if line.move_line_id:
                    amount_residual_total_without_skonto += line.move_line_id.amount_residual
                else:
                    #get name and ref from account_bank_statement_line of current voucher
                    account_bank_statement_line_pool = self.pool.get('account.bank.statement.line')
                    bank_statement_line_id = account_bank_statement_line_pool.search(cr, uid, [('voucher_id', '=', voucher.id)])[0]
                    bank_statement_line = account_bank_statement_line_pool.browse(cr, uid, bank_statement_line_id, context=context)
                    raise osv.except_osv(_('Error !'), _('Voucher of "%s" is not correct, please recreate voucher and edit it again!') % (bank_statement_line.name + ' - ' + bank_statement_line.ref))
            else:
                if line.move_line_id:
                    amount_residual_total_without_skonto = line.move_line_id.amount_residual
                else:
                    #get name and ref from account_bank_statement_line of current voucher
                    account_bank_statement_line_pool = self.pool.get('account.bank.statement.line')
                    bank_statement_line_id = account_bank_statement_line_pool.search(cr, uid, [('voucher_id', '=', voucher.id)])[0]
                    bank_statement_line = account_bank_statement_line_pool.browse(cr, uid, bank_statement_line_id, context=context)
                    raise osv.except_osv(_('Error !'), _('Voucher of "%s" is not correct, please recreate voucher and edit it again!') % (bank_statement_line.name + ' - ' + bank_statement_line.ref))
                
            #set current_currency_invoice
            current_currency_invoice = company_currency
            if line.move_line_id:
                current_currency_invoice = line.move_line_id.currency_id.id <> False and line.move_line_id.currency_id.id or company_currency
                
            currency_difference_correct  = 0
            #hack jool: just ignore skonto lines if payment_difference is set!
            if company_currency != current_currency_invoice:
                currency_difference_correct = self.calculate_currency_differences(cr, uid, line, context)
                
#            print 'diff_currency_correct 1: ', diff_currency_correct
            line_amount_compare = abs(line.amount)
            line_amount_unreconciled_compare = abs(line.amount_unreconciled)
            
            self.calculate_amount_pay_in_chf(cr, uid, line, context)
            self.calculate_currency_correct(cr, uid, currency_difference_correct, line, context)
            amount_currency = self.calculate_amount_currency(cr, uid, line, context)
            self.create_move_line(cr, uid, line, amount_currency, context)
    
    def create_writeoff_move_lines(self, cr, uid, account_id, context):
        global line_total
        global move_line_netto_dict
        global move_line_vat_dict
        global netto_sum
        global diff_computed
        global diff_computed_currency
        global context_multi_currency_special
        #if voucher.writeoff_amount > 0:

        #diff = line_total
        #diff = writeoff_amount
        diff = voucher_writeoff_amount
        print 'diff: ', diff
        
        set_voucher_line = False
        try:
            set_voucher_line = voucher_line
        except:
            pass
        
        context_multi_currency_special_diff_currency = context_multi_currency.copy()
        if set_voucher_line:
            context_multi_currency_special_diff_currency.update({'date': set_voucher_line.move_line_id.date})
        
        diff_currency = round(currency_pool.compute(cr, uid, current_currency, current_currency_invoice, diff, context=context_multi_currency_special_diff_currency, round=False),2) or 0.0
        diff_computed = diff
        diff_computed_currency = diff_currency
#        print 'diff_computed_currency: ', diff_computed_currency
        #hack jool: if currency is different compute value from currency
        #pay foreign currency over foreign account
        #pay foreign currency over CHF account
        if current_currency == current_currency_invoice and company_currency != current_currency \
            or current_currency != current_currency_invoice and company_currency == current_currency:
#            print 'CALCULATE DIFF_COMPUTED 1'
            #hack jool: set date to creation date of invoice
            if payment_difference_id and payment_difference_id == 1:
                if set_voucher_line:
                    context_multi_currency_special.update({'date': set_voucher_line.move_line_id.date})
            diff_computed = round(currency_pool.compute(cr, uid, current_currency, company_currency, diff, context=context_multi_currency_special, round=False),2) or 0.0
        ##pay foreign currency over CHF account
        #if current_currency != current_currency_invoice and company_currency == current_currency:
        #    print 'CALCULATE DIFF_COMPUTED 2'
        #    #hack jool: set date to creation date of invoice
        #    if payment_difference_id and payment_difference_id == 1:
        #        context_multi_currency_special.update({'date': line.move_line_id.date})
        #    diff_computed = currency_pool.compute(cr, uid, current_currency, company_currency, diff, context=context_multi_currency_special) or 0.0
#        print 'diff 1: ', diff
#        print 'diff_computed: ', diff_computed
#        print 'line_type_debit: ', line_type_debit
#        print 'line_total1: ', line_total
        line_total = round(line_total,2)
#        print 'line_total a: ', line_total
        if line_type_debit:
            if current_currency != current_currency_invoice and company_currency == current_currency:
                line_total -= round(diff,2)
#                print 'line_total b: ', line_total
            else:
                line_total -= round(diff_computed,2)
#                print 'line_total c: ', line_total
        else:
            if current_currency != current_currency_invoice and company_currency == current_currency:
                line_total += round(diff,2)
#                print 'line_total d: ', line_total
            else:
                line_total += round(diff_computed,2)
#        print 'line_total 2: ', line_total
                print 'line_total e: ', line_total
                        
        ##############################################################
        #hack jool: just create netto and vat lines if payment_difference is "Skontoabzug"
        netto_sum = 0
        if payment_difference_id and payment_difference_id == 1 and move_line_id_of_write_off:
#            print 'move_line_id_of_write_off: ', move_line_id_of_write_off
            get_move_id = move_line_pool.browse(cr,uid,move_line_id_of_write_off)
#                    print 'get_move_id.move_id.id: ', get_move_id.move_id.id
            move_line_netto_id = move_line_pool.search(cr,uid,['&','|',('debit','!=','0'),('credit','!=','0'),('move_id','=',get_move_id.move_id.id),'!',('tax_code_id','=',False),('tax_amount_base','=','0')])
#                    print 'move_line_netto_id: ', move_line_netto_id
            #if not move_line_netto_id:
            #    move_line_netto_id = move_line_pool.search(cr,uid,[('move_id','=',get_move_id.move_id.id),'!',('date_maturity_start','=',False),('tax_amount_base','=','0')])
            move_line_netto = move_line_pool.browse(cr,uid,move_line_netto_id)
            
            
            move_line_brutto_id = move_line_pool.search(cr,uid,[('move_id','=',get_move_id.move_id.id)])
            move_line_brutto = move_line_pool.browse(cr,uid,move_line_brutto_id)
            
#             pro_ids_brutto = [x.id for x in move_line_brutto]
            if move_line_brutto_id:
                cr.execute('select sum(tax_amount) from account_move_line where id in %s', (tuple(move_line_brutto_id), ))
                sum_brutto = cr.dictfetchall()
            
            #skonto - create for each line of tax a line
#             pro_ids = [x.id for x in move_line_netto]
            if move_line_netto_id:
                cr.execute('select sum(tax_amount) from account_move_line where id in %s', (tuple(move_line_netto_id), ))
                sum_netto = cr.dictfetchall()
            i = 0
            diff_new_total = 0
            len_move_line_netto = len(move_line_netto)
            if len_move_line_netto>0:
                credit_amount_total = 0
                debit_amount_total = 0
                count_move_line_netto_done = 0
                for move_line_netto_line in move_line_netto:
                    count_move_line_netto_done += 1
                    cr.execute('select distinct amount from account_tax where tax_code_id = %s or base_code_id = %s', (move_line_netto_line.tax_code_id.id,move_line_netto_line.tax_code_id.id))
                    tax_ids = cr.fetchall()
                    netto = 0
                    vat = 0
                    if tax_ids == []:
                        continue
                    else:
                        tax_names_dict = {}
                        for item in range(0, len(tax_ids)):
                            #need this to calculate taxes
                            amount = move_line_netto_line.tax_amount + (move_line_netto_line.tax_amount*tax_ids[item][0])
                            diff_new = diff / sum_brutto[0]['sum'] * abs(amount)
                            diff_new = round(diff_new, 2)
                            if i+1 < len_move_line_netto:
                                diff_new_total += diff_new
                            else:
                                diff_new = diff - diff_new_total
                            
                            netto = diff_new / (tax_ids[item][0] + 1)
                            vat = diff_new - netto
                            vat = round(vat, 2)
                    
                    #hack jool: if invoice currency is the same as the bank statement currency AND bank statement currency is not like company currency then...
                    #... set amount_currency as "netto"
                    #... calculate debit from "netto"
                    #... calculate credit from "netto"
                    amount_currency_move = 0
                    credit_move = line_type_debit and netto or 0.0
                    debit_move = not line_type_debit and netto or 0.0
                    
                    #print 'count_move_line_netto_done: ', count_move_line_netto_done
                    #print 'len_move_line_netto: ', len_move_line_netto
                    #print 'credit_move: ', credit_move
                    #print 'debit_move: ', debit_move
                    #pay foreign currency over foreign account
                    if current_currency == current_currency_invoice and company_currency != current_currency:
                        #hack jool: if there are rounding differences, add to last entry
#                                print 'pay foreign currency over foreign account'
#                                print 'netto: ', netto
#                                print 'current_currency: ', current_currency
#                                print 'company_currency: ', company_currency
#                                print 'context_multi_currency_special: ', context_multi_currency_special
                        credit_move = line_type_debit and round(currency_pool.compute(cr, uid, current_currency, company_currency, netto, context=context_multi_currency_special, round=False),2) or 0.0
                        debit_move = not line_type_debit and round(currency_pool.compute(cr, uid, current_currency, company_currency, netto, context=context_multi_currency_special, round=False),2) or 0.0
#                                print 'credit_move: ', credit_move
#                                print 'debit_move: ', debit_move
                        if credit_move > 0:
                            amount_currency_move = netto * -1 or 0.0
                        else:
                            amount_currency_move = netto or 0.0
                    #pay foreign currency over CHF account
                    if current_currency != current_currency_invoice and company_currency == current_currency:
#                                print 'pay foreign currency over CHF account'
#                                print 'context_multi_currency_special: ', context_multi_currency_special
#                                print 'netto: ', netto
                        if credit_move > 0:
                            amount_currency_move = round(currency_pool.compute(cr, uid, current_currency, current_currency_invoice, netto * -1, context=context_multi_currency_special, round=False),2) or 0.0
                        else:
                            amount_currency_move = round(currency_pool.compute(cr, uid, current_currency, current_currency_invoice, netto, context=context_multi_currency_special, round=False),2) or 0.0
#                        print 'amount_currency_move: ', amount_currency_move
                    
                    credit_amount_total += credit_move
                    debit_amount_total += debit_move
                    #print 'amount_currency_move: ', amount_currency_move
                    #print 'credit_move: ', credit_move
                    #print 'debit_move: ', debit_move
                    #print 'tax_amount(netto): ', netto
                    if debit_move > 0:
                        tax_amount = debit_move
                    else:
                        tax_amount = credit_move
                    account = self.pool.get('account.account').browse(cr, uid, account_id)
                    move_line = {
                        'name': name,
                        'account_id': account_id,
                        'move_id': move_id,
                        'partner_id': voucher.partner_id.id,
                        'date': voucher.date,
                        #hack jool
                        'payment_difference_id': payment_difference_id,
                        'amount_currency': amount_currency_move,
                        'currency_id': (current_currency_invoice <> current_currency and current_currency_invoice) or (company_currency <> current_currency and current_currency) or False,
                        'tax_code_id': move_line_netto_line.tax_code_id.id, 
                        'tax_amount_base': 0,
                        'credit': credit_move,
                        'debit': debit_move,
                        'tax_amount': tax_amount,
                        'analytic_account_id': account.requires_analytic_account and (writeoff_analytic_id and writeoff_analytic_id.id or voucher.journal_id.company_id.property_currency_difference_analytic_account.id),
                        'bank_statement_line_id': self.pool.get('account.bank.statement.line').search(cr, uid, [('voucher_id','=',voucher.id)], context=context) and self.pool.get('account.bank.statement.line').search(cr, uid, [('voucher_id','=',voucher.id)], context=context)[0] or False,
                    }
                        
                    if move_line['tax_code_id'] in move_line_netto_dict:
#                        if voucher.partner_id.id == 9749:
#                            print 'IS ALREADY IN DICT netto'
                        move_line_netto_dict[move_line['tax_code_id']]['amount_currency'] += move_line['amount_currency']
                        move_line_netto_dict[move_line['tax_code_id']]['credit'] += move_line['credit']
                        move_line_netto_dict[move_line['tax_code_id']]['debit'] += move_line['debit']
                        move_line_netto_dict[move_line['tax_code_id']]['tax_amount'] += move_line['tax_amount']
                    else:
#                        if voucher.partner_id.id == 9749:
#                            print 'IS NEW IN DICT netto'
                        move_line_netto_dict[move_line['tax_code_id']] = move_line

                    netto_sum += netto
                    
                    #hack jool: do not ignore vat line when 0 -> this line is needed for tax report!!!!
#                    if vat <> 0:
                    cr.execute('select tax_code_id from account_tax where base_code_id = %s', (move_line_netto_line.tax_code_id.id,))
                    tax_ids = cr.fetchall()
                    if not tax_ids:
                        cr.execute('select base_code_id from account_tax where base_code_id = %s', (move_line_netto_line.tax_code_id.id,))
                        tax_ids = cr.fetchall()
                    
                    move_line_vat_id = move_line_pool.search(cr,uid,[('move_id','=',get_move_id.move_id.id),('tax_code_id','=',tax_ids[0]),('tax_amount_base','<>','0')])
                    move_line_vat = move_line_pool.browse(cr,uid,move_line_vat_id)
                    
                    #create vat move_line
                    amount_currency_move = 0
                    credit_move = line_type_debit and vat or 0.0
                    debit_move = not line_type_debit and vat or 0.0
                    #pay foreign currency over foreign account
                    if current_currency == current_currency_invoice and company_currency != current_currency:
                        credit_move = line_type_debit and round(currency_pool.compute(cr, uid, current_currency, company_currency, vat, context=context_multi_currency_special, round=False),2) or 0.0
                        debit_move = not line_type_debit and round(currency_pool.compute(cr, uid, current_currency, company_currency, vat, context=context_multi_currency_special, round=False),2) or 0.0
                        if credit_move > 0:
                            amount_currency_move = vat * -1 or 0.0
                        else:
                            amount_currency_move = vat or 0.0
                        
                    #pay foreign currency over CHF account
                    if current_currency != current_currency_invoice and company_currency == current_currency:
#                                    print 'pay foreign currency over CHF account'
                        if credit_move > 0:
                            amount_currency_move = round(currency_pool.compute(cr, uid, current_currency, current_currency_invoice, vat * -1, context=context_multi_currency_special, round=False),2) or 0.0
                        else:
                            amount_currency_move = round(currency_pool.compute(cr, uid, current_currency, current_currency_invoice, vat, context=context_multi_currency_special, round=False),2) or 0.0
                        
                    vat_new = vat
                    netto_new = netto
                    if company_currency != current_currency:
                        vat_new = round(currency_pool.compute(cr, uid, current_currency, company_currency, vat, context=context_multi_currency_special, round=False),2) or 0.0
                        netto_new = round(currency_pool.compute(cr, uid, current_currency, company_currency, netto, context=context_multi_currency_special, round=False),2) or 0.0
                    #print 'amount_currency_move: ', amount_currency_move
                    #print 'credit_move: ', credit_move
                    #print 'debit_move: ', debit_move
                    #
                    #print 'TTTTTTTTTTTTTTTTTTTTTTEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEST'
                    #print 'line_total: ', line_total
#                                if line_type_debit:
#                                    print 'debit'
#                                    line_total -= credit_move
#                                else:
#                                    print 'credit'
#                                    line_total += debit_move
#                                print 'line_total_new: ', line_total
                    account = move_line_vat[0].account_id
                    move_line = {
                        'name': move_line_vat[0].name,
                        'account_id': move_line_vat[0].account_id.id,
                        'move_id': move_id,
                        'partner_id': voucher.partner_id.id,
                        'date': voucher.date,
                        #hack jool
                        'payment_difference_id': payment_difference_id,
                        'tax_code_id': move_line_vat[0].tax_code_id.id, 
                        'tax_amount_base': netto_new,
                        'tax_amount': vat_new,
                        'credit': credit_move,
                        'debit': debit_move,
                        'amount_currency': amount_currency_move,
                        'currency_id': (current_currency_invoice <> current_currency and current_currency_invoice) or (company_currency <> current_currency and current_currency) or False,
                        'analytic_account_id': account.requires_analytic_account and (writeoff_analytic_id and writeoff_analytic_id.id or voucher.journal_id.company_id.property_currency_difference_analytic_account.id),
                        'bank_statement_line_id': self.pool.get('account.bank.statement.line').search(cr, uid, [('voucher_id','=',voucher.id)], context=context) and self.pool.get('account.bank.statement.line').search(cr, uid, [('voucher_id','=',voucher.id)], context=context)[0] or False,
                    }
                    print '####################################################################################'
#                    if voucher.partner_id.id == 9749:
#                        print 'move_line vat: ', move_line
                        
                    if move_line['tax_code_id'] in move_line_vat_dict:
#                        if voucher.partner_id.id == 9749:
#                            print 'IS ALREADY IN DICT vat'
                        move_line_vat_dict[move_line['tax_code_id']]['amount_currency'] += move_line['amount_currency']
                        move_line_vat_dict[move_line['tax_code_id']]['credit'] += move_line['credit']
                        move_line_vat_dict[move_line['tax_code_id']]['debit'] += move_line['debit']
                        move_line_vat_dict[move_line['tax_code_id']]['tax_amount'] += move_line['tax_amount']
                        move_line_vat_dict[move_line['tax_code_id']]['tax_amount_base'] += move_line['tax_amount_base']
                        #move_line_vat_dict[move_line['tax_code_id']]['amount_currency'] = float(move_line_vat_dict[move_line['tax_code_id']]['amount_currency']) + float(move_line['amount_currency'])
                        #move_line_vat_dict[move_line['tax_code_id']]['credit'] = float(move_line_vat_dict[move_line['tax_code_id']]['credit']) + float(move_line['credit'])
                        #move_line_vat_dict[move_line['tax_code_id']]['debit'] = float(move_line_vat_dict[move_line['tax_code_id']]['debit']) + float(move_line['debit'])
                        #move_line_vat_dict[move_line['tax_code_id']]['tax_amount'] = float(move_line_vat_dict[move_line['tax_code_id']]['tax_amount']) + float(move_line['tax_amount'])
                        #move_line_vat_dict[move_line['tax_code_id']]['tax_amount_base'] = float(move_line_vat_dict[move_line['tax_code_id']]['tax_amount_base']) + float(move_line['tax_amount_base'])
                    else:
#                        if voucher.partner_id.id == 9749:
#                            print 'IS NEW IN DICT vat'
                        move_line_vat_dict[move_line['tax_code_id']] = move_line
#                                print '####################################################################################'
                    #move_line_pool.create(cr, uid, move_line)
                    i += 1
            else:
                #create netto move_line
                move_line = {
                    'name': name,
                    'account_id': account_id,
                    'move_id': move_id,
                    'partner_id': voucher.partner_id.id,
                    'date': voucher.date,
                    #hack jool
                    'payment_difference_id': payment_difference_id,
#                    'journal_id': 19,
#                    'period_id': voucher.period_id.id,
                    #'amount_currency': company_currency <> current_currency and currency_pool.compute(cr, uid, company_currency, current_currency, netto * -1, context=context_multi_currency) or 0.0,
                    #'amount_currency': voucher.writeoff_amount,
                    #'currency_id': company_currency <> current_currency and current_currency or False,
                    'credit': line_type_debit and (str(round(diff_computed,2))) or 0.0,
                    'debit': not line_type_debit and (str(round(diff_computed,2))) or 0.0,
                    'bank_statement_line_id': self.pool.get('account.bank.statement.line').search(cr, uid, [('voucher_id','=',voucher.id)], context=context) and self.pool.get('account.bank.statement.line').search(cr, uid, [('voucher_id','=',voucher.id)], context=context)[0] or False,
                }
                print '####################################################################################'
                print 'move_line2: ', move_line
                print 'line_total3: ', line_total
                print '####################################################################################'
                move_line_pool.create(cr, uid, move_line)
        else:
            #if payment_difference is set but not as 'Skontoabzug'
            amount_currency_move = 0
            if line_type_debit:
                debit_move = paid_to_much > 0 and abs(diff) or 0.0
                credit_move = bt_format.check_if_zero(paid_to_much) and abs(diff) or 0.0
            else:
                credit_move = paid_to_much > 0 and abs(diff) or 0.0
                debit_move = bt_format.check_if_zero(paid_to_much) and abs(diff) or 0.0
#                    print '----------line_total:', line_total
#                    print '----------diff:', diff
#                    print '----------credit_move:', credit_move
#                    print '----------debit_move:', debit_move
            #if credit_move > 0:
            #    line_total -= float(str(round(credit_move,2)))
            #else:
            #    line_total += float(str(round(debit_move,2)))
            #print '----------line_total2:', line_total
            #pay foreign currency over foreign account
            if current_currency == current_currency_invoice and company_currency != current_currency:
                if line_type_debit:
                    debit_move = paid_to_much > 0 and round(currency_pool.compute(cr, uid, current_currency, company_currency, abs(diff), context=context_multi_currency, round=False),2) or 0.0
                    credit_move = bt_format.check_if_zero(paid_to_much) and round(currency_pool.compute(cr, uid, current_currency, company_currency, abs(diff), context=context_multi_currency, round=False),2) or 0.0
                else:
                    credit_move = paid_to_much > 0 and round(currency_pool.compute(cr, uid, current_currency, company_currency, abs(diff), context=context_multi_currency, round=False),2) or 0.0
                    debit_move = bt_format.check_if_zero(paid_to_much) and round(currency_pool.compute(cr, uid, current_currency, company_currency, abs(diff), context=context_multi_currency, round=False),2) or 0.0
                if credit_move > 0:
                    amount_currency_move = abs(diff) * -1 or 0.0
                else:
                    amount_currency_move = abs(diff) or 0.0
                
            #pay foreign currency over CHF account
            # HACK: 29.01.2014 16:29:44: olivier: is this really needed? why do we need amount_currency when we are creating a move in CHF?
#             if current_currency != current_currency_invoice and company_currency == current_currency:
#                 if credit_move > 0:
#                     amount_currency_move = round(currency_pool.compute(cr, uid, current_currency, current_currency_invoice, abs(diff) * -1, context=context_multi_currency, round=False),2) or 0.0
#                 else:
#                     amount_currency_move = round(currency_pool.compute(cr, uid, current_currency, current_currency_invoice, abs(diff), context=context_multi_currency, round=False),2) or 0.0
            
            
            #create netto move_line
            account = self.pool.get('account.account').browse(cr, uid, account_id)
            move_line = {
                'name': name,
                'account_id': account_id,
                'move_id': move_id,
                'partner_id': voucher.partner_id.id,
                'date': voucher.date,
                #hack jool
                'payment_difference_id': payment_difference_id,
#                    'journal_id': 19,
#                    'period_id': voucher.period_id.id,
                'credit': (str(round(credit_move,2))),
                'debit': (str(round(debit_move,2))),
                'amount_currency': (str(round(amount_currency_move,2))),
                'currency_id': ((current_currency_invoice <> current_currency and company_currency == current_currency_invoice) and current_currency_invoice) or (company_currency <> current_currency and current_currency) or False,
                'analytic_account_id': account.requires_analytic_account and (writeoff_analytic_id and writeoff_analytic_id.id or voucher.journal_id.company_id.property_currency_difference_analytic_account.id),
                'bank_statement_line_id': self.pool.get('account.bank.statement.line').search(cr, uid, [('voucher_id','=',voucher.id)], context=context) and self.pool.get('account.bank.statement.line').search(cr, uid, [('voucher_id','=',voucher.id)], context=context)[0] or False,
            }
            print '####################################################################################'
            print 'move_line3: ', move_line
            print 'line_total4: ', line_total
            print '####################################################################################'
            move_line_pool.create(cr, uid, move_line)
    
    def create_move_lines_bundled(self, cr, uid, context):
        global netto_sum
        global diff_computed
        global diff_computed_currency
        global rounding_differences
        #            print 'CREATE MOVE_LINES BUNDLED'
#            print 'line_type_debit: ', line_type_debit
        total_debit_credit = 0
        total_amount_currency = 0
        move_line_netto_dict_len = len(move_line_netto_dict)
        move_line_vat_dict_len = len(move_line_vat_dict)
        i = 0
#        print 'move_line_netto_dict: ', move_line_netto_dict
#        print 'diff_computed: ', diff_computed
        for line_netto in move_line_netto_dict.values():
            i += 1
            if netto_sum <> 0:
                total_debit_credit += round(line_netto['debit'],2)
                total_debit_credit -= round(line_netto['credit'],2)
#                print 'total_debit_credit: ', total_debit_credit
                total_amount_currency += round(line_netto['amount_currency'],2)
                line_netto.update({'amount_currency': (str(round(line_netto['amount_currency'],2)))})
                line_netto.update({'debit': (str(round(line_netto['debit'],2)))})
                line_netto.update({'credit': (str(round(line_netto['credit'],2)))})
                line_netto.update({'tax_amount': (str(round(line_netto['tax_amount'],2)))})
                line_netto.update({'tax_amount_base': (str(round(line_netto['tax_amount_base'],2)))})
                #hack jool: calculate rounding differences and add to Rundungsdifferenzen
                #just calculate rounding_differences if currency is not CHF (for both invoice and journal)
                #if not(current_currency == company_currency and current_currency_invoice == company_currency):
                if True:
                    if move_line_vat_dict_len == 0 and i == move_line_netto_dict_len:
                    #if i == move_line_netto_dict_len:
                        #add rounding_differences to last entry
#                            print 'CALCULATE ROUNDING DIFFERENCE NETTO'
                        #set abs()
                        diff_computed = abs(diff_computed)
                        total_debit_credit = abs(total_debit_credit)
                        diff_computed_currency = abs(diff_computed_currency)
                        total_amount_currency = abs(total_amount_currency)
#                            print 'diff_computed: ', diff_computed
#                            print 'total_debit_credit: ', total_debit_credit
                        rounding_differences = round(diff_computed,2) - round(total_debit_credit,2)
#                        print 'rounding_differences netto: ', rounding_differences
                        rounding_differences_currency = round(diff_computed_currency,2) - round(total_amount_currency,2)
#                        print 'rounding_differences_currency netto: ', rounding_differences_currency
                        #update credit, debit, tax_amount
                        if abs(rounding_differences) <= 0.05:
                            if line_type_debit:
                                #update tax_amount
                                line_tax_amount = float(line_netto['tax_amount']) - abs(rounding_differences)
                                line_netto.update({'tax_amount': (str(round(line_tax_amount,2)))})
                                #update credit
                                line_credit = float(line_netto['credit']) + rounding_differences
                                rounding_differences -= rounding_differences
                                line_netto.update({'credit': (str(round(line_credit,2)))})
                            else:
                                #update tax_amount
                                line_tax_amount = float(line_netto['tax_amount']) + abs(rounding_differences)
                                line_netto.update({'tax_amount': (str(round(line_tax_amount,2)))})
                                #update debit
                                line_debit = float(line_netto['debit']) + rounding_differences
                                rounding_differences -= rounding_differences
                                line_netto.update({'debit': (str(round(line_debit,2)))})
                        #update amount_currency
                        if abs(rounding_differences_currency) <= 0.05:
                            if line_type_debit:
                                line_amount_currency = float(line_netto['amount_currency']) - rounding_differences_currency
                                line_netto.update({'amount_currency': (str(round(line_amount_currency,2)))})
                            else:
                                line_amount_currency = float(line_netto['amount_currency']) + rounding_differences_currency
                                line_netto.update({'amount_currency': (str(round(line_amount_currency,2)))})
                    #else:
                        
                    
#                if line_netto['partner_id'] == 9749:
#                    print 'INSERT move_line_netto: ', line_netto
                print '####################################################################################'
                print 'line_netto: ', line_netto
                print '####################################################################################'
                move_line_pool.create(cr, uid, line_netto)
        
        i = 0
#        print 'move_line_vat_dict: ', move_line_vat_dict
        for line_vat in move_line_vat_dict.values():
            i += 1
            total_debit_credit += round(line_vat['debit'],2)
            total_debit_credit -= round(line_vat['credit'],2)
            total_amount_currency += round(line_vat['amount_currency'],2)
            line_vat.update({'amount_currency': (str(round(line_vat['amount_currency'],2)))})
            line_vat.update({'credit': (str(round(line_vat['credit'],2)))})
            line_vat.update({'debit': (str(round(line_vat['debit'],2)))})
            line_vat.update({'tax_amount': (str(round(line_vat['tax_amount'],2)))})
            line_vat.update({'tax_amount_base': (str(round(line_vat['tax_amount_base'],2)))})
            #hack jool: calculate rounding differences and add to Rundungsdifferenzen
            #just calculate rounding_differences if currency is not CHF (for both invoice and journal)
            #if not(current_currency == company_currency and current_currency_invoice == company_currency):
            if True:
                if i == move_line_vat_dict_len:
                    #add rounding_differences to last entry
#                        print 'CALCULATE ROUNDING DIFFERENCE VAT'
                    #set abs()
                    diff_computed = abs(diff_computed)
                    total_debit_credit = abs(total_debit_credit)
                    diff_computed_currency = abs(diff_computed_currency)
                    total_amount_currency = abs(total_amount_currency)
                    #add rounding_differences to last entry
                    rounding_differences = round(diff_computed,2) - round(total_debit_credit,2)
                    rounding_differences_currency = round(diff_computed_currency,2) - round(total_amount_currency,2)
#                    if line_vat['partner_id'] == 9749:
#                        print 'INSERT rounding_differences: ', rounding_differences
#                        print 'line_vat[credit]: ', line_vat['credit']
                    #update credit, debit, tax_amount
                    #update just if both (debit and credit) aren't 0
                    if not(float(line_vat['credit']) == 0 and float(line_vat['debit']) == 0):
                        if abs(rounding_differences) <= 0.05:
                            if line_type_debit:
                                #update tax_amount
                                line_tax_amount = float(line_vat['tax_amount']) - abs(rounding_differences)
                                line_vat.update({'tax_amount': (str(round(line_tax_amount,2)))})
                                #update credit
                                line_credit = float(line_vat['credit']) + rounding_differences
                                rounding_differences -= rounding_differences
                                line_vat.update({'credit': (str(round(line_credit,2)))})
                            else:
                                #update tax_amount
                                line_tax_amount = float(line_vat['tax_amount']) + abs(rounding_differences)
                                line_vat.update({'tax_amount': (str(round(line_tax_amount,2)))})
                                #update debit
                                line_debit = float(line_vat['debit']) + rounding_differences
                                rounding_differences -= rounding_differences
                                line_vat.update({'debit': (str(round(line_debit,2)))})
                    
                    #update just if both (debit and credit) aren't 0
                    if not(float(line_vat['credit']) == 0 and float(line_vat['debit']) == 0):
                        #update amount_currency
                        if abs(rounding_differences_currency) <= 0.05:
                            if line_type_debit:
                                line_amount_currency = float(line_vat['amount_currency']) - rounding_differences_currency
                                line_vat.update({'amount_currency': (str(round(line_amount_currency,2)))})
                            else:
                                line_amount_currency = float(line_vat['amount_currency']) + rounding_differences_currency
                                line_vat.update({'amount_currency': (str(round(line_amount_currency,2)))})
            
#            if line_vat['partner_id'] == 9749:
#                print 'INSERT move_line_vat: ', line_vat
            print '####################################################################################'
            print 'line_vat: ', line_vat
            print '####################################################################################'
            move_line_pool.create(cr, uid, line_vat)
    
    #TODO test rounding differences!!!
    def create_rounding_difference_move_line(self, cr, uid, context):
        global rounding_differences
        global name
        global account_id
        global move_id
        global company_currency
        global current_currency
        global current_currency_invoice
        #set account 6845 Aufwendungen aus Rundungsdifferenzen - 786
        if rounding_differences > 0:
            account_id = voucher.journal_id.company_id.property_rounding_difference_cost_account.id
        #set account 6895 Ertrage aus Rundungsdifferenzen - 798
        else:
            account_id = voucher.journal_id.company_id.property_rounding_difference_profit_account.id

        print 'rounding_differences: ', rounding_differences
        
        print 'line_type_debit: ', line_type_debit
        #hack jool: set -
        if line_type_debit:
            rounding_differences = rounding_differences*-1

        move_line = {
            'name': name,
            'account_id': account_id,
            'move_id': move_id,
            'partner_id': voucher.partner_id.id,
            'date': voucher.date,
            'credit': rounding_differences < 0 and (str(round(-rounding_differences,2))) or 0.0,
            'debit': rounding_differences > 0 and (str(round(rounding_differences,2))) or 0.0,
#            'currency_id': company_currency,
            'currency_id': False, # HACK: 08.04.2014 15:43:06: olivier: set currency_id to False, otherwise it will get via defaults from account.move.line with "def _get_currency" the currency_id from the journal in the context, and then the check "_check_currency_company" will fail
            'amount_currency': 0.0,
            'bank_statement_line_id': self.pool.get('account.bank.statement.line').search(cr, uid, [('voucher_id','=',voucher.id)], context=context) and self.pool.get('account.bank.statement.line').search(cr, uid, [('voucher_id','=',voucher.id)], context=context)[0] or False,
        }
        print '####################################################################################'
        print 'move_line rounding_differences: ', move_line
        print '####################################################################################'
        rounding_differences = 0
        move_line_pool.create(cr, uid, move_line)
    
    def create_currency_correct_move_lines(self, cr, uid, context):
        global diff_currency_correct_dict
        global line_total
        print 'diff_currency_correct_dict: ', diff_currency_correct_dict
        for line_currency_difference_item in diff_currency_correct_dict:
            #move_id = line_currency_difference_item.id
            line_currency_difference = diff_currency_correct_dict[line_currency_difference_item]['diff_currency_correct']
            line_is_gutschrift = diff_currency_correct_dict[line_currency_difference_item]['is_gutschrift']
#            print 'move_id: ', move_id
#            print 'line_currency_difference: ', line_currency_difference
            line_type_debit = diff_currency_correct_dict[line_currency_difference_item]['type'] == 'dr'
            
            #change the line_type_debit if line is a gutschrift line
            if line_is_gutschrift:
                line_type_debit = not line_type_debit
            
            #create move_line for reconciliation
            #get account where invoice was booked on
            account_id = invoice_account_id
            credit_move = 0
            debit_move = 0
#            print 'line_type_debit: ', line_type_debit
            if line_type_debit:
                if line_currency_difference < 0:
                    credit_move = round(abs(line_currency_difference),2)
                else:
                    debit_move = round(abs(line_currency_difference),2)
            else:
                if line_currency_difference > 0:
                    credit_move = round(abs(line_currency_difference),2)
                else:
                    debit_move = round(abs(line_currency_difference),2)
            
#            print 'credit_move: ', credit_move
#            print 'debit_move: ', debit_move
            account = self.pool.get('account.account').browse(cr, uid, account_id)
            if line_type_debit:
                move_line = {
                    'name': name,
                    'account_id': account_id,
                    'move_id': move_id,
                    'partner_id': voucher.partner_id.id,
                    'date': voucher.date,
                    'credit': line_currency_difference < 0 and float(str(round(credit_move,2))) or 0.0,
                    'debit': line_currency_difference > 0 and float(str(round(debit_move,2))) or 0.0,
#                     'currency_id': company_currency,
                    #jool1: changed currency_id
#                     'currency_id': company_currency <> current_currency_invoice and current_currency_invoice or False,
                    #'currency_id': False, # HACK: 08.04.2016 10:00:39: jool1: currency_id should always be False because this is the company currency amount which will be booked
                    'currency_id': account.currency_id and account.currency_id.id or False,#HACK 21.09.2016: piti1: Curency id should be set if the account is in foreign currency 
                    #set reconcile_partial_id
                    #'reconcile_partial_id':
                    'amount_currency': 0.0,
                    'currency_difference': True,
                    'currency_difference_belongs_to': line_currency_difference_item.id,
                    'analytic_account_id': account.requires_analytic_account and (writeoff_analytic_id and writeoff_analytic_id.id or voucher.journal_id.company_id.property_currency_difference_analytic_account.id),
                    'bank_statement_line_id': self.pool.get('account.bank.statement.line').search(cr, uid, [('voucher_id','=',voucher.id)], context=context) and self.pool.get('account.bank.statement.line').search(cr, uid, [('voucher_id','=',voucher.id)], context=context)[0] or False,
                }
            else:
                move_line = {
                    'name': name,
                    'account_id': account_id,
                    'move_id': move_id,
                    'partner_id': voucher.partner_id.id,
                    'date': voucher.date,
                    'credit': line_currency_difference > 0 and float(str(round(credit_move,2))) or 0.0,
                    'debit': line_currency_difference < 0 and float(str(round(debit_move,2))) or 0.0,
#                     'currency_id': company_currency,
                    #jool1: changed currency_id
#                     'currency_id': company_currency <> current_currency_invoice and current_currency_invoice or False,
                    #'currency_id': False, # HACK: 08.04.2016 10:00:39: jool1: currency_id should always be False because this is the company currency amount which will be booked
                    'currency_id': account.currency_id and account.currency_id.id or False,#HACK 21.09.2016: piti1: Curency id should be set if the account is in foreign currency 
                    #set reconcile_partial_id
                    #'reconcile_partial_id':
                    'amount_currency': 0.0,
                    'currency_difference': True,
                    'currency_difference_belongs_to': line_currency_difference_item.id,
                    'analytic_account_id': account.requires_analytic_account and (writeoff_analytic_id and writeoff_analytic_id.id or voucher.journal_id.company_id.property_currency_difference_analytic_account.id),
                    'bank_statement_line_id': self.pool.get('account.bank.statement.line').search(cr, uid, [('voucher_id','=',voucher.id)], context=context) and self.pool.get('account.bank.statement.line').search(cr, uid, [('voucher_id','=',voucher.id)], context=context)[0] or False,
                }
            print '####################################################################################'
            print 'move_line currency_difference reconciliation: ', move_line
            print '####################################################################################'
            move_line_pool.create(cr, uid, move_line)
            
#            print 'line_total: ', line_total
            #create move_line for currency difference
            if line_total <>0:
                if line_type_debit:
                    if line_total>0:
                        line_currency_difference += abs(line_total)
                    else:
                        line_currency_difference -= abs(line_total)
                else:
                    if line_total>0:
                        line_currency_difference -= abs(line_total)
                    else:
                        line_currency_difference += abs(line_total)
                line_total = 0
            
            #hack jool: set account 6842 Kursdifferenzen
            account_id = voucher.journal_id.company_id.property_currency_difference_account.id
            account = self.pool.get('account.account').browse(cr, uid, account_id)
            if line_type_debit:
                move_line = {
                    'name': name,
                    'account_id': account_id,
                    'move_id': move_id,
                    'partner_id': voucher.partner_id.id,
                    'date': voucher.date,
                    'credit': line_currency_difference > 0 and (str(round(line_currency_difference,2))) or 0.0,
                    'debit': line_currency_difference < 0 and (str(round(-line_currency_difference,2))) or 0.0,
#                     'currency_id': company_currency, # HACK: 29.01.2014 15:43:44: olivier: removed currency_id, because of constraint "_check_currency_company" we cannot book currency_id with company_currency
                    'amount_currency': 0.0,
                    #jool1: changed currency_id
#                     'currency_id': company_currency <> current_currency_invoice and current_currency_invoice or False,
                    'currency_id': False, # HACK: 08.04.2014 15:43:06: olivier: set currency_id to False, otherwise it will get via defaults from account.move.line with "def _get_currency" the currency_id from the journal in the context, and then the check "_check_currency_company" will fail
                    'analytic_account_id': account.requires_analytic_account and (writeoff_analytic_id and writeoff_analytic_id.id or voucher.journal_id.company_id.property_currency_difference_analytic_account.id),
                    'bank_statement_line_id': self.pool.get('account.bank.statement.line').search(cr, uid, [('voucher_id','=',voucher.id)], context=context) and self.pool.get('account.bank.statement.line').search(cr, uid, [('voucher_id','=',voucher.id)], context=context)[0] or False,
                }

            else:
                move_line = {
                    'name': name,
                    'account_id': account_id,
                    'move_id': move_id,
                    'partner_id': voucher.partner_id.id,
                    'date': voucher.date,
                    'credit': line_currency_difference < 0 and (str(round(-line_currency_difference,2))) or 0.0,
                    'debit': line_currency_difference > 0 and (str(round(line_currency_difference,2))) or 0.0,
#                     'currency_id': company_currency, # HACK: 29.01.2014 15:43:44: olivier: removed currency_id, because of constraint "_check_currency_company" we cannot book currency_id with company_currency
                    'amount_currency': 0.0,
                    #jool1: changed currency_id
#                     'currency_id': company_currency <> current_currency_invoice and current_currency_invoice or False,
                    'currency_id': False, # HACK: 08.04.2014 15:43:06: olivier: set currency_id to False, otherwise it will get via defaults from account.move.line with "def _get_currency" the currency_id from the journal in the context, and then the check "_check_currency_company" will fail
                    'analytic_account_id': account.requires_analytic_account and (writeoff_analytic_id and writeoff_analytic_id.id or voucher.journal_id.company_id.property_currency_difference_analytic_account.id),
                    'bank_statement_line_id': self.pool.get('account.bank.statement.line').search(cr, uid, [('voucher_id','=',voucher.id)], context=context) and self.pool.get('account.bank.statement.line').search(cr, uid, [('voucher_id','=',voucher.id)], context=context)[0] or False,
                }
            print '####################################################################################'
            print 'move_line currency_difference: ', move_line
            print '####################################################################################'
            move_line_pool.create(cr, uid, move_line)
    
    def create_general_type_move_lines(self, cr, uid, context):
        global voucher
        global line_total
        global context_multi_currency
        #Belastung
        debit = credit = 0
#        print 'line_total1: ', line_total
        if voucher.type in ('purchase', 'payment'):
            debit = voucher.amount
            debit = round(currency_pool.compute(cr, uid, current_currency, company_currency, debit, context=context_multi_currency, round=False),2)
            line_total += debit
        #Gutschrift
        if voucher.type in ('sale', 'receipt'):
            credit = voucher.amount
            credit = round(currency_pool.compute(cr, uid, current_currency, company_currency, credit, context=context_multi_currency, round=False),2)
            line_total -= credit
#        print 'line_total2: ', line_total
        move_line = {
            'name': voucher.name or '/',
            'account_id': voucher.account_id_bank_statement.id,
            'move_id': move_id,
            'partner_id': voucher.partner_id.id,
            'date': voucher.date,
            #'credit': line_currency_difference < 0 and (str(round(-line_currency_difference,2))) or 0.0,
            #'debit': line_currency_difference > 0 and (str(round(line_currency_difference,2))) or 0.0,
            'credit': credit,
            'debit': debit,
            #'currency_id': company_currency,
            'amount_currency': 0.0,
            #jool1: changed currency_id
            'currency_id': company_currency <> current_currency_invoice and current_currency_invoice or False,
            'bank_statement_line_id': self.pool.get('account.bank.statement.line').search(cr, uid, [('voucher_id','=',voucher.id)], context=context) and self.pool.get('account.bank.statement.line').search(cr, uid, [('voucher_id','=',voucher.id)], context=context)[0] or False,
        }
        
        print '####################################################################################'
        print 'general type move_line: ', move_line
        print '####################################################################################'        
        move_line_pool.create(cr, uid, move_line)
    
    def action_move_line_create(self, cr, uid, ids, context=None):
        if context and context.get('bt_payment_difference', True) is False:
            return super(account_voucher_extended, self).action_move_line_create(cr, uid, ids, context=context)
        global voucher
        global voucher_type
        global voucher_amount
        global amount_total_paid_voucher
        global company_currency
        global current_currency
        global current_currency_invoice
        global context_multi_currency
        global name
        global move_pool, move_line_pool, currency_pool, tax_obj, seq_obj, account_pool, voucher_line_pool, invoice_obj
        global debit, credit, line_total
        global invoice_line_ids, skonto_line_ids, gutschrift_line_ids
        global paid_to_much, paid_not_enough
        global payment_option, voucher_writeoff_amount, writeoff_acc_id, payment_difference_id, writeoff_comment, writeoff_analytic_id
        global diff_currency_correct_dict
        global move_id
        #TODO: needed?
        global all_line_ids
        global line_type_debit
        global voucher_line
        global move_line_id_of_write_off
        global writeoff_amount
        global last_move_line_id
        global invoice_account_id
        global voucher_line_type
        global diff_currency_correct
        global gutschriften_added
        global rec_list_ids
        global count_ids
        
        global move_line_netto_dict
        global move_line_vat_dict
        global rounding_differences
        global context_multi_currency_special
        global amount_residual_total_without_skonto
 
        def _get_payment_term_lines(term_id, amount):
            term_pool = self.pool.get('account.payment.term')
            if term_id and amount:
                terms = term_pool.compute(cr, uid, term_id, amount)
                return terms
            return False
        if context is None:
            context = {}
            
        amount_total_paid_voucher = 0
        current_currency_invoice = False
            
        move_pool = self.pool.get('account.move')
        move_line_pool = self.pool.get('account.move.line')
        currency_pool = self.pool.get('res.currency')
        tax_obj = self.pool.get('account.tax')
        seq_obj = self.pool.get('ir.sequence')
        account_pool = self.pool.get('account.account')
        voucher_line_pool = self.pool.get('account.voucher.line')
        invoice_obj = self.pool.get('account.invoice')

#        print 'ACTION_MOVE_LINE_CREATE'

        for voucher_obj in self.browse(cr, uid, ids, context=context):
            voucher = voucher_obj
            if voucher.move_id:
                continue
            rec_list_ids = []
            move_line_id_of_write_off = 0
            last_move_line_id = 0
            voucher_line_type = False
            diff_currency_correct = 0
            amount_residual_total_without_skonto = 0
            line_currency_difference = 0
            diff_currency_correct_dict = {}
            move_line_netto_dict = {}
            move_line_vat_dict = {}
            gutschriften_added = []
            
            #set all important voucher infos
            self.set_voucher_infos(cr, uid, context)
            
            ########################################################################################################
            #TODO: REPLACE ALL THIS!!!!
            #hack jool: order line_ids by id
            #get line_ids of invoice
            ids = [x.id for x in voucher.line_ids]
            
            #get by type (needed, so that the gutschriften will be at the end)
            if voucher_type in ('sale', 'receipt'):
                ids_ordered = voucher_line_pool.search(cr, uid, [('id', 'in', ids)], order='type asc, skonto, id')
            elif voucher_type in ('purchase', 'payment'):
                ids_ordered = voucher_line_pool.search(cr, uid, [('id', 'in', ids)], order='type desc, skonto, id')
            
            count_ids = len(ids_ordered)
            ########################################################################################################
            #create move_id
            move_id = self.create_move_id(cr, uid, context)
            
            # HACK: 14.01.2014 09:10:36: olivier: removed becuase this is already done in 'set_voucher_infos'
            #calculate all lines which will be paid
            #self.get_amount_total_paid_voucher(cr, uid, invoice_line_ids + gutschrift_line_ids, context)
            
            #create first move line manually
            self.create_first_move_line(cr, uid, move_id, context)
            #create move lines for invoice_lines, skonto_lines and gutschrift_lines
            self.create_move_lines(cr, uid, context)
            ########################################################################################################
            #hack jool:TODO create credit_voucher
#            print 'paid_to_much: ', paid_to_much
            #if paid_to_much: 
            #for this version, the customer must create an credit_voucher by hand!!!
            
#            print 'DO SET move_line_id_of_write_off 2'    
            if voucher_writeoff_amount <> 0 and bt_format.check_if_zero(move_line_id_of_write_off):
#                print 'SET move_line_id_of_write_off 2'
                move_line_id_of_write_off = last_move_line_id
                
            
            #hack jool
            payment_difference_id = False
            rounding_differences = 0
            context_multi_currency_special = context_multi_currency.copy()
            
            #hack jool
            account_id = False
            if voucher.payment_option == 'with_writeoff':
                account_id = voucher.writeoff_acc_id.id
                #hack jool
                payment_difference_id = voucher.payment_difference_id.id
            elif voucher.type in ('sale', 'receipt'):
                account_id = voucher.partner_id.property_account_receivable.id
            else:
                account_id = voucher.partner_id.property_account_payable.id
            ########################################################################################################
            #create move line for writeoff
            if voucher_writeoff_amount <> 0 and payment_option == 'with_writeoff':    
                self.create_writeoff_move_lines(cr, uid, account_id, context)
            #create move lines bundled
            self.create_move_lines_bundled(cr, uid, context)
            #create move lines for rounding differences
            if rounding_differences <> 0:
                self.create_rounding_difference_move_line(cr, uid, context)
            #create move lines for correct currency differences
            if diff_currency_correct_dict:
                self.create_currency_correct_move_lines(cr, uid, context)
            ########################################################################################################
            #hack jool: book all bankstatement lines with type == general ("Sonstige")
            if voucher.type_bank_statement == 'general':
                self.create_general_type_move_lines(cr, uid, context)
           
            print 'voucher.currency_id: ', voucher.payment_rate_currency_id
            print 'line_total: ', line_total
            #hack jool: 6.1 - changed currency_id to payment_rate_currency_id 
#            if not currency_pool.is_zero(cr, uid, voucher.currency_id, line_total):
            if not currency_pool.is_zero(cr, uid, voucher.payment_rate_currency_id, line_total):
                #diff = line_total
                diff = line_total
                account_id = False
#                #hack jool
#                print 'voucher.type: ', voucher.type
#                print 'diff: ', diff
                
                if line_currency_difference > 0 :
                    #hack jool: set account 6842 Kursdifferenzen
                    account_id = voucher.journal_id.company_id.property_currency_difference_account.id
                
                #if voucher.payment_option == 'with_writeoff':
                #    if payment_difference_id and payment_difference_id == 1:
                #        #account_id = voucher.writeoff_acc_id.id
                #        #hack jool!!!!!! TODO
                #        account_id = 785
                #        #account_id = voucher_line_pool.search(cr, uid, [('id', 'in', ids)], order='id')
                #    else:
                #        account_id = voucher.writeoff_acc_id.id
                #    print 'if'
#                if voucher.type in ('payment'):
#                    if voucher.journal_id.company_id.property_currency_difference_account:
#                        print 'voucher.journal_id.company_id.property_currency_difference_account:'
#                        print voucher.journal_id.company_id.property_currency_difference_account.id
#                        account_id = voucher.journal_id.company_id.property_currency_difference_account.id
                elif voucher.type in ('sale', 'receipt'):
                    try:
                        account_id = invoice_account_id
                    except:
                        account_id = voucher.partner_id.property_account_receivable.id
                else:
#                    print 'else'
                    #account_id = voucher.partner_id.property_account_payable.id
                    #hack jool: set account 6842 Kursdifferenzen
                    account_id = account_id = voucher.journal_id.company_id.property_currency_difference_account.id
                account = self.pool.get('account.account').browse(cr, uid, account_id)
                move_line = {
                    'name': name,
                    'account_id': account_id,
                    'move_id': move_id,
                    'partner_id': voucher.partner_id.id,
                    'date': voucher.date,
                    'credit': diff > 0 and (float(str(round(diff,2)))) or 0.0,
                    'debit': diff < 0 and (float(str(round(-diff,2)))) or 0.0,
#                    'journal_id': 19,
#                    'period_id': voucher.period_id.id,
                    #'amount_currency': company_currency <> current_currency and currency_pool.compute(cr, uid, company_currency, current_currency, diff * -1, context=context_multi_currency) or 0.0,
#                     'currency_id': company_currency, # HACK: 29.01.2014 15:43:44: olivier: removed currency_id, because of constraint "_check_currency_company" we cannot book currency_id with company_currency
                    'amount_currency': 0.0,
                    #jool1: changed currency_id
#                     'currency_id': company_currency <> current_currency_invoice and current_currency_invoice or False,
                    'currency_id': False, # HACK: 08.04.2014 15:43:06: olivier: set currency_id to False, otherwise it will get via defaults from account.move.line with "def _get_currency" the currency_id from the journal in the context, and then the check "_check_currency_company" will fail
                    'analytic_account_id': account.requires_analytic_account and (writeoff_analytic_id and writeoff_analytic_id.id or voucher.journal_id.company_id.property_currency_difference_analytic_account.id),
                    'bank_statement_line_id': self.pool.get('account.bank.statement.line').search(cr, uid, [('voucher_id','=',voucher.id)], context=context) and self.pool.get('account.bank.statement.line').search(cr, uid, [('voucher_id','=',voucher.id)], context=context)[0] or False,
                }
                print '####################################################################################'
                print 'move_line currency_pool.is_zero: ', move_line
                print '####################################################################################'
                move_line_pool.create(cr, uid, move_line)
            
            
            self.write(cr, uid, [voucher.id], {
                'move_id': move_id,
                'state': 'posted',
                'number': name,
            })
            
            move_pool.post(cr, uid, [move_id], context={})
#            i = 0
#            print 'rec_list_ids: ', rec_list_ids
            for rec_ids in rec_list_ids:
                if len(rec_ids) >= 2:
                    #set context "first" to true for first line
                    context_reconcile = context.copy()
#                    context_reconcile.update({'first': False})
#                    if i == 0:
#                        context_reconcile.update({'first': True})
#                    i += 1
                    
                    #move_line_pool.reconcile_partial(cr, uid, rec_ids, context=context_reconcile)
                    move_line_pool.reconcile_partial(cr, uid, rec_ids, writeoff_acc_id=voucher.writeoff_acc_id.id, writeoff_period_id=voucher.period_id.id, writeoff_journal_id=voucher.journal_id.id)
            
        return True
        return super(account_voucher_extended, self).action_move_line_create(self, cr, uid, ids, context=None)

    #hack jool: now it works also with credits!!        
    #hack jool: 6.1 - not needed anymore!
#    def onchange_partner_id(self, cr, uid, ids, partner_id, journal_id, price, currency_id, ttype, date, context=None):
#     def onchange_partner_id(self, cr, uid, ids, partner_id, journal_id, amount, currency_id, ttype, date, context=None):
#         """price
#         Returns a dict that contains new values and context
# 
#         @param partner_id: latest value from user input for field partner_id
#         @param args: other arguments
#         @param context: context arguments, like lang, time zone
# 
#         @return: Returns a dict which contains new values, and context
#         """
#         print 'bt_payment_difference/account_voucher_extended.py onchange_partner_id'
#         price = amount 
#         if context is None:
#             context = {}
#         if not journal_id:
#             return {}
#         context_multi_currency = context.copy()
#         if date:
#             context_multi_currency.update({'date': date})
# 
#         line_pool = self.pool.get('account.voucher.line')
#         print 'ids: ', ids
#         line_ids = ids and line_pool.search(cr, uid, [('voucher_id', '=', ids[0])]) or False
#         if line_ids:
#             line_pool.unlink(cr, uid, line_ids)
# 
#         currency_pool = self.pool.get('res.currency')
#         move_line_pool = self.pool.get('account.move.line')
#         partner_pool = self.pool.get('res.partner')
#         journal_pool = self.pool.get('account.journal')
# 
#         tax_id = False
#         company_id = False
#         currency_id = False
# #        vals = self.onchange_journal(cr, uid, ids, journal_id, [], False, partner_id, context)
#         if line_ids:
#             vals = self.onchange_journal(cr, uid, ids, journal_id, line_ids, tax_id, partner_id, time.strftime('%Y-%m-%d'), price, ttype, company_id, context)
#             vals = vals.get('value')
#             currency_id = vals.get('currency_id', currency_id)
#         default = {
#             'value':{'line_ids':[], 'line_dr_ids':[], 'line_cr_ids':[], 'pre_line': False, 'currency_id':currency_id},
#         }
# 
#         if not partner_id:
#             return default
# 
#         if not partner_id and ids:
#             line_ids = line_pool.search(cr, uid, [('voucher_id', '=', ids[0])])
#             if line_ids:
#                 line_pool.unlink(cr, uid, line_ids)
#             return default
# 
#         journal = journal_pool.browse(cr, uid, journal_id, context=context)
#         partner = partner_pool.browse(cr, uid, partner_id, context=context)
#         account_id = False
#         if journal.type in ('sale','sale_refund'):
#             account_id = partner.property_account_receivable.id
#         elif journal.type in ('purchase', 'purchase_refund','expense'):
#             account_id = partner.property_account_payable.id
#         else:
#             if not journal.default_credit_account_id or not journal.default_debit_account_id:
#                 raise osv.except_osv(_('Error !'), _('Please define default credit/debit accounts on the journal "%s" !') % (journal.name))
#             account_id = journal.default_credit_account_id.id or journal.default_debit_account_id.id
# 
#         default['value']['account_id'] = account_id
# 
#         if journal.type not in ('cash', 'bank'):
#             return default
# 
#         total_credit = 0.0
#         total_debit = 0.0
#         account_type = 'receivable'
# #        print 'ttype: ', ttype 
#         if ttype == 'payment':
#             account_type = 'payable'
#             total_debit = price or 0.0
#         else:
#             total_credit = price or 0.0
#             account_type = 'receivable'
# 
#         if not context.get('move_line_ids', False):
# #            print 'account_type: ', account_type
#             ids = move_line_pool.search(cr, uid, [('state','=','valid'), ('account_id.type', '=', account_type), ('reconcile_id', '=', False), ('partner_id', '=', partner_id)], context=context)
#         else:
#             ids = context['move_line_ids']
#         ids.reverse()
# #        print 'ids: ', ids
#         moves = move_line_pool.browse(cr, uid, ids, context=context)
# 
#         company_currency = journal.company_id.currency_id.id
#         if company_currency != currency_id and ttype == 'payment':
#             total_debit = currency_pool.compute(cr, uid, currency_id, company_currency, total_debit, context=context_multi_currency)
#         elif company_currency != currency_id and ttype == 'receipt':
#             total_credit = currency_pool.compute(cr, uid, currency_id, company_currency, total_credit, context=context_multi_currency)
# 
# #        print 'moves: ', moves
# #        print 'ttype: ', ttype
# #        print 'total_debit: ', total_debit
# #        print 'total_credit: ', total_credit
#         #hack jool
#         reconcile_partial_id_dict = {}
#         for line in moves:
#             #hack jool
#             cr.execute("select type from account_invoice where move_id in (select move_id from account_move_line where id = %s)"%(line.id))
#             result = cr.fetchall()
#             type = ''
#             for r in result:
#                 type = r[0]
#                 if line.reconcile_partial_id.id:
#                     reconcile_partial_id_dict[line.reconcile_partial_id.id] = type
#             if not type:
# #                print 'reconcile_partial_id_dict: ', reconcile_partial_id_dict
# #                print 'CONTINUE No type1'
# #                print 'line.reconcile_partial_id.id: ', line.reconcile_partial_id.id
#                 if line.reconcile_partial_id.id and reconcile_partial_id_dict != {}:
#                     type = reconcile_partial_id_dict[line.reconcile_partial_id.id]
#                 if not type:
# #                    print 'CONTINUE No type1 2'
#                     continue
# #            print 'type: ', type
#             if type == 'out_refund' or type == 'in_refund':
#                 #for gutschriften
# #                print 'GUTSCHRIFT'
#                 if line.debit and line.reconcile_partial_id and ttype == 'receipt':
# #                    print 'CONTINUE1'
#                     continue
#                 if line.credit and line.reconcile_partial_id and ttype == 'payment':
# #                    print 'CONTINUE2'
#                     continue
#             else:
#                 ##for invoices
#                 if line.credit and line.reconcile_partial_id and ttype == 'receipt':
# #                    print 'CONTINUE3'
#                     continue
#                 if line.debit and line.reconcile_partial_id and ttype == 'payment':
# #                    print 'CONTINUE4'
#                     continue
#             total_credit += line.credit or 0.0
#             total_debit += line.debit or 0.0
# #            print 'total_credit: ', total_credit
# #            print 'total_debit: ', total_debit
#         for line in moves:
#             #hack jool
#             cr.execute("select type from account_invoice where move_id in (select move_id from account_move_line where id = %s)"%(line.id))
#             result = cr.fetchall()
#             type = ''
#             for r in result:
#                 type = r[0]
# #            print 'type: ', type
#             if not type:
# #                print 'CONTINUE No type2'
#                 continue
# #                type = reconcile_partial_id_dict[line.reconcile_partial_id.id][0]
# #                if not type:
# #                    print 'CONTINUE No type2 2'
# #                    continue
#             if type == 'out_refund' or type == 'in_refund':
#                 #for gutschriften
# #                print 'GUTSCHRIFT'
#                 if line.debit and line.reconcile_partial_id and ttype == 'receipt':
# #                    print 'CONTINUE5'
#                     continue
#                 if line.credit and line.reconcile_partial_id and ttype == 'payment':
# #                    print 'CONTINUE6'
#                     continue
#             else:
#                 ##for invoices
# #                print 'INVOICE'
#                 if line.credit and line.reconcile_partial_id and ttype == 'receipt':
# #                    print 'CONTINUE7'
#                     continue
#                 if line.debit and line.reconcile_partial_id and ttype == 'payment':
# #                    print 'CONTINUE8'
#                     continue
#             original_amount = line.credit or line.debit or 0.0
#             amount_unreconciled = currency_pool.compute(cr, uid, line.currency_id and line.currency_id.id or company_currency, currency_id, abs(line.amount_residual_currency), context=context_multi_currency)
#             rs = {
#                 'name':line.move_id.name,
#                 'type': line.credit and 'dr' or 'cr',
#                 'move_line_id':line.id,
#                 'account_id':line.account_id.id,
#                 'amount_original': currency_pool.compute(cr, uid, line.currency_id and line.currency_id.id or company_currency, currency_id, line.currency_id and abs(line.amount_currency) or original_amount, context=context_multi_currency),
#                 'date_original':line.date,
#                 'date_due':line.date_maturity,
#                 'amount_unreconciled': amount_unreconciled,
# 
#             }
# 
#             if line.credit:
#                 amount = min(amount_unreconciled, currency_pool.compute(cr, uid, company_currency, currency_id, abs(total_debit), context=context_multi_currency))
#                 rs['amount'] = amount
#                 total_debit -= amount
#             else:
#                 amount = min(amount_unreconciled, currency_pool.compute(cr, uid, company_currency, currency_id, abs(total_credit), context=context_multi_currency))
#                 rs['amount'] = amount
#                 total_credit -= amount
# 
#             default['value']['line_ids'].append(rs)
#             if rs['type'] == 'cr':
#                 default['value']['line_cr_ids'].append(rs)
#             else:
#                 default['value']['line_dr_ids'].append(rs)
# 
# #            print '----------------------------------------------------------------------------------------------------------------------------'
# #            print 'ttype: ', ttype
# #            print 'default[value][line_cr_ids]: ', default['value']['line_cr_ids']
# #            print 'default[value][line_dr_ids]: ', default['value']['line_dr_ids']
# #            print 'default[value][pre_line]: ', default['value']['pre_line']
#             if ttype == 'payment' and len(default['value']['line_cr_ids']) > 0:
#                 default['value']['pre_line'] = 1
#             elif ttype == 'receipt' and len(default['value']['line_dr_ids']) > 0:
#                 default['value']['pre_line'] = 1
#             default['value']['writeoff_amount'] = self._compute_writeoff_amount(cr, uid, default['value']['line_dr_ids'], default['value']['line_cr_ids'], price, ttype)
#         return default


account_voucher_extended()

def resolve_o2m_operations(cr, uid, target_osv, operations, fields, context):
    results = []
    for operation in operations:
        result = None
        if not isinstance(operation, (list, tuple)):
            result = target_osv.read(cr, uid, operation, fields, context=context)
        elif operation[0] == 0:
            # may be necessary to check if all the fields are here and get the default values?
            result = operation[2]
        elif operation[0] == 1:
            result = target_osv.read(cr, uid, operation[1], fields, context=context)
            if not result: result = {}
            result.update(operation[2])
        elif operation[0] == 4:
            result = target_osv.read(cr, uid, operation[1], fields, context=context)
        if result != None:
            results.append(result)
    return results

