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

from osv import osv, fields
from tools.translate import _

class account_bank_statement_line_extended(osv.osv):
    _inherit = 'account.bank.statement.line'
    
    #hack jool: if date will be changed in account.bank.statement.line -> change date for account_voucher
    def onchange_date(self, cr, uid, ids, date, context=None):
        for statement_line in self.browse(cr, uid, ids, context):
            #update period
            if context is None:
                context = {}
            period_pool = self.pool.get('account.period')
            ctx = dict(context, account_period_prefer_normal=True)
            pids = period_pool.find(cr, uid, date, context=ctx)
            if pids:
                self.pool.get('account.voucher').write(cr, uid, [statement_line.voucher_id.id], {'date': date, 'period_id': pids[0]}, context=context)
            self.pool.get('account.voucher').write(cr, uid, [statement_line.voucher_id.id], {'date': date}, context=context)
        return True
    
    def _open_amount_invoice_get(self, cr, uid, ids, name, args, context=None):
        if not ids: return {}
        res = {}
        invoice_obj = self.pool.get('account.invoice')
        account_move_line_obj = self.pool.get('account.move.line')
        total = 0.0
        total_voucher = 0.0
        is_other_currency = False
        inv_ids = []
        invoice_reconciled = False
        for line in self.browse(cr, uid, ids, context=context):
            if line.voucher_id.line_ids:
                for voucher_line in line.voucher_id.line_ids:
                    total_voucher += voucher_line.amount
                    if voucher_line.move_line_id:
                        invoice_ids = invoice_obj.search(cr, uid, [('move_id','=',voucher_line.move_line_id.move_id.id)])
                        for invoice in invoice_obj.browse(cr,uid, invoice_ids,context=context):
                            if not invoice.id in inv_ids:
                                inv_ids.append(invoice.id)
                                # HACK: 07.01.2013 07:45:35: olivier: get company currency via company!!
                                company_currency = self.pool.get('res.users').browse(cr, uid, uid, context=context).company_id.currency_id.id
                                #hack jool: if invoice currency is equal to company_currency or invoice currency is equal to journal currency - get amount from invoice, otherwise get amount from move_lines
                                if invoice.currency_id.id == company_currency or invoice.currency_id.id == line.statement_id.journal_id.currency.id:
                                    if invoice.reconciled:
                                        invoice_reconciled = True
                                    elif line.statement_id.state == 'draft':
                                        total += invoice.residual
                                    else:
                                        total += invoice.amount_total
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

            if invoice_reconciled:
                total = 0
            #hack jool: if invoice of payment is in another currency than the bank statment and the total is not 0 then set -1
            if is_other_currency and total <> 0:
                res[line.id] = -1
            else:
                res[line.id] = round(total,2)
            total = total_voucher = 0.0
            inv_ids = []
        return res

    def _partner_name(self, cr, uid, context=None):
        if context is None:
            context = {}
        partner_obj = self.pool.get('res.partner')
        if context.has_key('partner_id') and context['partner_id']:
            partner = partner_obj.browse(cr, uid, context['partner_id'], context=context)
            if partner.name:
                return partner.name
        return ''
    
    # HACK: 23.06.2014 09:54:51: olivier: removed this hack, because it should work now correctly!
#     def _check_amount(self, cr, uid, ids, context=None):
#         for obj in self.browse(cr, uid, ids, context=context):
#             if obj.voucher_id:
# #                 diff = abs(obj.amount) - obj.voucher_id.amount
# #                 diff = abs(obj.amount) - abs(obj.voucher_id.amount)
#                 sign = obj.type == 'supplier' and -1 or 1
#                 diff = sign*obj.amount - obj.voucher_id.amount
#                 if not self.pool.get('res.currency').is_zero(cr, uid, obj.statement_id.currency, diff):
#                     return False
#         return True

    def _get_writeoff_amount_extended(self, cr, uid, ids, name, args, context=None):
        if not ids: return {}
        res = {}
        for line in self.browse(cr, uid, ids, context=context):
            res[line.id] = line.voucher_id.writeoff_amount
        return res

    _columns = {
        'open_amount_invoice': fields.function(_open_amount_invoice_get, method=True, string='Open Amount Invoice'),
        'writeoff_amount': fields.function(_get_writeoff_amount_extended, string='Difference Amount', type='float', readonly=True, help="Computed as the difference between the amount stated in the voucher and the sum of allocation on the voucher lines."),
        'partner_name': fields.char('Partner Name', size=64, required=True),
    }

    _defaults = {
        'partner_name': _partner_name,
    }

    # HACK: 18.07.2014 14:25:23: olivier: if type will be changed in account.bank.statement.line -> change type_bank_statement for account_voucher
    def onchange_type(self, cr, uid, line_id, partner_id, type, context=None):
        res = super(account_bank_statement_line_extended, self).onchange_type(cr, uid, line_id, partner_id, type, context=context)
        if context is None:
            context = {}
        for statement_line in self.browse(cr, uid, line_id, context):
            if statement_line.voucher_id:
                self.pool.get('account.voucher').write(cr, uid, [statement_line.voucher_id.id], {'type_bank_statement': type}, context=context)
        return res

#     _constraints = [
#         (_check_amount, 'The amount of the voucher must be the same amount as the one on the statement line.', ['amount']),
#     ]
account_bank_statement_line_extended()
