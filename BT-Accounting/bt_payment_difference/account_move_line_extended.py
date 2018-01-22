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
from datetime import datetime
from operator import itemgetter

import netsvc
from osv import fields, osv
from tools.translate import _
import decimal_precision as dp
import tools

class account_move_line_extended(osv.osv):
    _inherit = 'account.move.line'
    
    def _amount_residual_new(self, cr, uid, ids, field_names, args, context=None):
        """
           This function returns the residual amount on a receivable or payable account.move.line.
           By default, it returns an amount in the currency of this journal entry (maybe different
           of the company currency), but if you pass 'residual_in_company_currency' = True in the
           context then the returned amount will be in company currency.
        """
#        print 'AMOUNT_RESIDUAL'
#        print 'ids: ', ids
        res = {}
        if context is None:
            context = {}
        cur_obj = self.pool.get('res.currency')
        for move_line in self.browse(cr, uid, ids, context=context):
#            print '****************MOVE_LINE NEW: ', move_line
            res[move_line.id] = {
                'amount_residual': 0.0,
                'amount_residual_currency': 0.0,
            }

            if move_line.reconcile_id:
                continue
#            print 'move_line.account_id.type: ', move_line.account_id.type
            if not move_line.account_id.type in ('payable', 'receivable'):
                #this function does not suport to be used on move lines not related to payable or receivable accounts
                continue

            if move_line.currency_id:
                move_line_total = move_line.amount_currency
                sign = move_line.amount_currency < 0 and -1 or 1
            else:
                move_line_total = move_line.debit - move_line.credit
                sign = (move_line.debit - move_line.credit) < 0 and -1 or 1
            line_total_in_company_currency =  move_line.debit - move_line.credit
#            print 'move_line_total: ', move_line_total
#            print 'line_total_in_company_currency: ', line_total_in_company_currency
            context_unreconciled = context.copy()
            #hack jool: get company_currency_id
            res_users_obj = self.pool.get('res.users')
            company_currency_id = res_users_obj.browse(cr, uid, uid, context=context).company_id.currency_id.id
#            print 'company_currency_id: ', company_currency_id
            if move_line.reconcile_partial_id:
                for payment_line in move_line.reconcile_partial_id.line_partial_ids:
                    #print 'payment_line: ', payment_line
                    if payment_line.id == move_line.id:
                        continue
                    #print 'payment_line.currency_id: ', payment_line.currency_id
                    #print 'move_line.currency_id: ', move_line.currency_id
                    if payment_line.currency_id and move_line.currency_id and payment_line.currency_id.id == move_line.currency_id.id:
                    #    print 'IF------------------'
                    #    print 'move_line_total: ', move_line_total
                        move_line_total += payment_line.amount_currency
#                        print 'move_line_total: ', move_line_total
                    else:
                    #    print 'ELSE----------------'
                        if move_line.currency_id:
                    #        print 'move_line_total: ', move_line_total
                    #        print 'ELSE IF---------'
                            
                            #hack jool: if company.currency_id == payment_line.currency_id
                            if payment_line.currency_id and company_currency_id and payment_line.currency_id.id == company_currency_id:
                                if not payment_line.amount_currency:
                                    continue
                            
                            context_unreconciled.update({'date': payment_line.date})
                            amount_in_foreign_currency = cur_obj.compute(cr, uid, move_line.company_id.currency_id.id, move_line.currency_id.id, (payment_line.debit - payment_line.credit), round=False, context=context_unreconciled)
                            move_line_total += amount_in_foreign_currency
                    #        print 'move_line_total: ', move_line_total
                        else:
                    #        print 'ELSE ELSE-------'
                    #        print 'move_line_total: ', move_line_total
                            move_line_total += (payment_line.debit - payment_line.credit)
                    #        print 'move_line_total: ', move_line_total
                    line_total_in_company_currency += (payment_line.debit - payment_line.credit)

            result = move_line_total
#            print 'TEST!!!!!!!!!!!!!'
#            print 'sign: ', sign
#            print 'move_line.currency_id: ', move_line.currency_id
#            print 'result: ', result
            res[move_line.id]['amount_residual_currency'] =  sign * (move_line.currency_id and self.pool.get('res.currency').round(cr, uid, move_line.currency_id, result) or result)
            res[move_line.id]['amount_residual'] = sign * line_total_in_company_currency
        #print 'RES amount_residual: ', res
        return res
    
    _columns = {
        'payment_difference_id':fields.many2one('payment.difference.type', 'Payment difference', required=False, readonly=True, states={'draft':[('readonly',False)]}),
        'currency_difference':fields.boolean('Is currency difference', required=False),
        'currency_difference_belongs_to': fields.integer('Currency Difference belongs to which move', required=False, help="this is the move_id to which the currency difference belongs to"),
        'amount_residual_currency': fields.function(_amount_residual_new, method=True, string='Residual Amount', multi="residual", help="The residual amount on a receivable or payable of a journal entry expressed in its currency (maybe different of the company currency)."),
        'amount_residual': fields.function(_amount_residual_new, method=True, string='Residual Amount', multi="residual", help="The residual amount on a receivable or payable of a journal entry expressed in the company currency."),
    }
    
    #def reconcile_partial(self, cr, uid, ids, type='auto', context=None):
    def reconcile_partial(self, cr, uid, ids, type='auto', context=None, writeoff_acc_id=False, writeoff_period_id=False, writeoff_journal_id=False):
        print 'JOOL reconcile_partial extended'
        print 'ids: ', ids
        move_rec_obj = self.pool.get('account.move.reconcile')
        merges = []
        unmerge = []
        total = 0.0
        merges_rec = []
        company_list = []
        if context is None:
            context = {}
        for line in self.browse(cr, uid, ids, context=context):
            if company_list and not line.company_id.id in company_list:
                raise osv.except_osv(_('Warning !'), _('To reconcile the entries company should be the same for all entries'))
            company_list.append(line.company_id.id)

        currency_difference_calculated = False
        currency_difference_belongs_to_move_ids = []
        for line in self.browse(cr, uid, ids, context=context):
            currency_difference_belongs_to_move_ids.append(line.id)
        
        for line in self.browse(cr, uid, ids, context=context):
            #hack jool: get Kursdifferenzen which will be booked
            currency_difference_line_ids = self.search(cr, uid, [('move_id','=',line.move_id.id), ('currency_difference','=',True), ('currency_difference_belongs_to','in',currency_difference_belongs_to_move_ids)])            
            currency_difference_lines = self.browse(cr, uid, currency_difference_line_ids, context=context)
#            print 'currency_difference_lines: ', currency_difference_lines
            for currency_difference_line in currency_difference_lines:
                currency_difference_calculated = True
#                print 'currency_difference_line.debit: ', currency_difference_line.debit
#                print 'currency_difference_line.credit: ', currency_difference_line.credit
                total += (currency_difference_line.debit or 0.0) - (currency_difference_line.credit or 0.0)
                merges.append(currency_difference_line.id)
            
            company_currency_id = line.company_id.currency_id
            
            if line.reconcile_id:
                if line.partner_id:
                    # HACK: 04.03.2014 10:28:30: olivier: check if last_name exists in db
                    cr.execute("select id from ir_model_fields where model_id in (select id from ir_model where model = 'res.partner') and name = 'last_name'")
                    last_name_exists = cr.fetchall()
                    if last_name_exists != []:
                        full_name = (line.partner_id.last_name + ' ' if line.partner_id.last_name else '') + line.partner_id.name
                    else:
                        full_name = line.partner_id.name
                    raise osv.except_osv(_('Warning'), _('Already Reconciled (Partner %s - %s)!') % (full_name, line.name))
                else:
                    raise osv.except_osv(_('Warning'), _('Already Reconciled (%s)!') % line.name)
            if line.reconcile_partial_id:
                for line2 in line.reconcile_partial_id.line_partial_ids:
                    if not line2.reconcile_id:
#                        print 'if not'
                        if line2.id not in merges:
#                            print 'if'
                            merges.append(line2.id)
                            
#                        print 'line2.debit: ', line2.debit
#                        print 'line2.credit: ', line2.credit
                        total += (line2.debit or 0.0) - (line2.credit or 0.0)
                merges_rec.append(line.reconcile_partial_id.id)
            else:
#                print 'else'
                unmerge.append(line.id)
#                print 'line.debit: ', line.debit
#                print 'line.credit: ', line.credit
                total += (line.debit or 0.0) - (line.credit or 0.0)

#        print 'merges: ', merges
#        print 'unmerge: ', unmerge
#        print 'total: ', total
        #hack jool: removed (it would be better to set status to "paid" and leave all partial_reconcile_id's)!! 
        #Problem: if there are several partial payments for an invoice and the whole invoice is paid it would create one reconcile_id for all partial payments. and if you now want to cancel an bankstatemtent, all payments will be deleted because they all refer to the same reconcile_id
#        print 'company_currency_id: ', company_currency_id
        if self.pool.get('res.currency').is_zero(cr, uid, company_currency_id, total):
#            print 'if'
            res = self.reconcile(cr, uid, merges+unmerge, context=context, writeoff_acc_id=writeoff_acc_id, writeoff_period_id=writeoff_period_id, writeoff_journal_id=writeoff_journal_id)
            return res
#        print 'CREATE'
        r_id = move_rec_obj.create(cr, uid, {
            'type': type,
            'line_partial_ids': map(lambda x: (4,x,False), merges+unmerge)
        })
        move_rec_obj.reconcile_partial_check(cr, uid, [r_id] + merges_rec, context=context)
        return True
        return super(account_move_line_extended, self).reconcile_partial(self, cr, uid, ids, type='auto', context=None)

        
    def reconcile1(self, cr, uid, ids, type='auto', writeoff_acc_id=False, writeoff_period_id=False, writeoff_journal_id=False, context=None):
        print 'JOOL reconcile extended ids: ', ids
        account_obj = self.pool.get('account.account')
        move_obj = self.pool.get('account.move')
        move_rec_obj = self.pool.get('account.move.reconcile')
        partner_obj = self.pool.get('res.partner')
        currency_obj = self.pool.get('res.currency')
        lines = self.browse(cr, uid, ids, context=context)
        unrec_lines = filter(lambda x: not x['reconcile_id'], lines)
        credit = debit = 0.0
        currency = 0.0
        account_id = False
        partner_id = False
        if context is None:
            context = {}
        company_list = []
        for line in self.browse(cr, uid, ids, context=context):
            if company_list and not line.company_id.id in company_list:
                raise osv.except_osv(_('Warning !'), _('To reconcile the entries company should be the same for all entries'))
            company_list.append(line.company_id.id)
        currency_difference_calculated = False
        for line in unrec_lines:
            if line.state <> 'valid':
                raise osv.except_osv(_('Error'),
                        _('Entry "%s" is not valid !') % line.name)
#            print 'line credit: ', line['credit']
#            print 'line debit: ', line['debit']
            credit += line['credit']
            debit += line['debit']
            currency += line['amount_currency'] or 0.0
            account_id = line['account_id']['id']
            partner_id = (line['partner_id'] and line['partner_id']['id']) or False
        writeoff = debit - credit
#        print 'writeoff: ', writeoff

        # If date_p in context => take this date
        if context.has_key('date_p') and context['date_p']:
            date=context['date_p']
        else:
            date = time.strftime('%Y-%m-%d')

        cr.execute('SELECT account_id, reconcile_id '\
                   'FROM account_move_line '\
                   'WHERE id IN %s '\
                   'GROUP BY account_id,reconcile_id',
                   (tuple(ids), ))
        r = cr.fetchall()
        #TODO: move this check to a constraint in the account_move_reconcile object
        if (len(r) != 1) and not context.get('fy_closing', False):
            raise osv.except_osv(_('Error'), _('Entries are not of the same account or already reconciled ! '))
        if not unrec_lines:
            raise osv.except_osv(_('Error'), _('Entry is already reconciled'))
        account = account_obj.browse(cr, uid, account_id, context=context)
        if not context.get('fy_closing', False) and not account.reconcile:
            raise osv.except_osv(_('Error'), _("The account '%s' is not defined to be reconciled !") % (account.name,))
        if r[0][1] != None:
            raise osv.except_osv(_('Error'), _('Some entries are already reconciled !'))

        if context.get('fy_closing'):
            # We don't want to generate any write-off when being called from the
            # wizard used to close a fiscal year (and it doesn't give us any
            # writeoff_acc_id).
            pass
        elif (not currency_obj.is_zero(cr, uid, account.company_id.currency_id, writeoff)) or \
           (account.currency_id and (not currency_obj.is_zero(cr, uid, account.currency_id, currency))):
            if not writeoff_acc_id:
                raise osv.except_osv(_('Warning'), _('You have to provide an account for the write off entry !'))
            if writeoff > 0:
                debit = writeoff
                credit = 0.0
                self_credit = writeoff
                self_debit = 0.0
            else:
                debit = 0.0
                credit = -writeoff
                self_credit = 0.0
                self_debit = -writeoff
            # If comment exist in context, take it
            if 'comment' in context and context['comment']:
                libelle = context['comment']
            else:
                libelle = _('Write-Off')

            cur_obj = self.pool.get('res.currency')
            cur_id = False
            amount_currency_writeoff = 0.0
            if context.get('company_currency_id',False) != context.get('currency_id',False):
                cur_id = context.get('currency_id',False)
                for line in unrec_lines:
                    if line.currency_id and line.currency_id.id == context.get('currency_id',False):
                        amount_currency_writeoff += line.amount_currency
                    else:
                        tmp_amount = cur_obj.compute(cr, uid, line.account_id.company_id.currency_id.id, context.get('currency_id',False), abs(line.debit-line.credit), context={'date': line.date})
                        amount_currency_writeoff += (line.debit > 0) and tmp_amount or -tmp_amount

            writeoff_lines = [
                (0, 0, {
                    'name': libelle,
                    'debit': self_debit,
                    'credit': self_credit,
                    'account_id': account_id,
                    'date': date,
                    'partner_id': partner_id,
                    'currency_id': cur_id or (account.currency_id.id or False),
                    'amount_currency': amount_currency_writeoff and -1 * amount_currency_writeoff or (account.currency_id.id and -1 * currency or 0.0)
                }),
                (0, 0, {
                    'name': libelle,
                    'debit': debit,
                    'credit': credit,
                    'account_id': writeoff_acc_id,
                    'analytic_account_id': context.get('analytic_id', False),
                    'date': date,
                    'partner_id': partner_id,
                    'currency_id': cur_id or (account.currency_id.id or False),
                    'amount_currency': amount_currency_writeoff and amount_currency_writeoff or (account.currency_id.id and currency or 0.0)
                })
            ]

            writeoff_move_id = move_obj.create(cr, uid, {
                'period_id': writeoff_period_id,
                'journal_id': writeoff_journal_id,
                'date':date,
                'state': 'draft',
                'line_id': writeoff_lines
            })

            writeoff_line_ids = self.search(cr, uid, [('move_id', '=', writeoff_move_id), ('account_id', '=', account_id)])
            if account_id == writeoff_acc_id:
                writeoff_line_ids = [writeoff_line_ids[1]]
            ids += writeoff_line_ids

        r_id = move_rec_obj.create(cr, uid, {
            'type': type,
            'line_id': map(lambda x: (4, x, False), ids),
            'line_partial_ids': map(lambda x: (3, x, False), ids)
        })
        wf_service = netsvc.LocalService("workflow")
        # the id of the move.reconcile is written in the move.line (self) by the create method above
        # because of the way the line_id are defined: (4, x, False)
        for id in ids:
            wf_service.trg_trigger(uid, 'account.move.line', id, cr)

        if lines and lines[0]:
            partner_id = lines[0].partner_id and lines[0].partner_id.id or False
            if partner_id and context and context.get('stop_reconcile', False):
                partner_obj.write(cr, uid, [partner_id], {'last_reconciliation_date': time.strftime('%Y-%m-%d %H:%M:%S')})
        return r_id
        return super(account_move_line_extended, self).reconcile(self, cr, uid, ids, type='auto', writeoff_acc_id=False, writeoff_period_id=False, writeoff_journal_id=False, context=context)
    
    # HACK: 10.09.2013 10:46:51: olivier: overwrite create to catch the sql_constraint errors and add some info to the error
    def create(self, cr, uid, vals, context=None, check=True):
        bank_statement_line = ''
        partner = ''
        if 'partner_id' in vals and vals['partner_id']:
            partner = self.pool.get('res.partner').browse(cr, uid, int(vals['partner_id']), context=context).name
        if 'bank_statement_line_id' in vals and vals['bank_statement_line_id']:
            bank_statement_line = self.pool.get('account.bank.statement.line').browse(cr, uid, int(vals['bank_statement_line_id']), context=context).name
            #message = _("with communication '{1}' of partner '{2}'")
            message = _("occured in line with communication '{0}' of partner '{1}'").format(bank_statement_line, partner)
        else:
            message = _("occured in line with partner '{0}'").format(partner)
        
        #get translations
        contraints_translations = {}
        for constraint in getattr(self.pool.get('account.move.line'), '_sql_constraints', []):
            contraints_translations[constraint[2]] = _(constraint[2])
        
        error_title = _('Error')
        
        try:
            return super(account_move_line_extended, self).create(cr, uid, vals, context, check)
        except Exception as e:
            message_constraint = ''
            for constraint in getattr(self.pool.get('account.move.line'), '_sql_constraints', []):
                if constraint[0] in e.message:
                    message_constraint = contraints_translations[constraint[2]]
                    break
            if message_constraint == '':
                raise e
            raise osv.except_osv(error_title, "{0} \n\n {1}".format(message_constraint, message))
    # END HACK: 10.09.2013 10:46:51: olivier: overwrite create to catch the sql_constraint errors and add some info to the error
        
account_move_line_extended()

