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
import decimal_precision as dp
from bt_helper.tools import bt_format

class account_voucher_line_extended(osv.osv):
    _inherit = 'account.voucher.line'
    
    def onchange_amount(self, cr, uid, ids, amount, amount_unreconciled, context=None):
        vals = {}
        if amount:
#             vals['reconcile'] = (amount == amount_unreconciled)
            # HACK: 28.01.2014 07:57:28: olivier: the line above does sometimes not work, so we do it like this
            vals['reconcile'] = bt_format.check_if_zero(abs(round(amount-amount_unreconciled)))
        return {'value': vals}
        return super(account_voucher_line_extended, self).onchange_amount(cr, uid, ids, amount, amount_unreconciled, context)
    
    def _compute_balance_new(self, cr, uid, ids, name, args, context=None):
        currency_pool = self.pool.get('res.currency')
        rs_data = {}
        print '---------------------------------------------------------------------------------------------'
        print '_compute_balance: ', ids
        for line in self.browse(cr, uid, ids, context=context):
            ctx = context.copy()
#            ctx.update({'date': line.voucher_id.date})
            res = {}
            company_currency = line.voucher_id.journal_id.company_id.currency_id.id
            voucher_currency = line.voucher_id.currency_id.id
            move_line = line.move_line_id or False
            #hack jool: set date from move_line for the amount_original if move_line is set, otherwise take date from voucher
            if move_line:
                ctx.update({'date': move_line.date})
            else:
                ctx.update({'date': line.voucher_id.date})

            if not move_line:
                res['amount_original'] = 0.0
                res['amount_unreconciled'] = 0.0
            elif move_line.currency_id:
                print 'company_currency: ', company_currency
                print 'voucher_currency: ', voucher_currency
                print 'move_line.currency_id: ', move_line.currency_id

                if move_line.currency_id.id <> voucher_currency:
                    if move_line.credit == 0:
                        res['amount_original'] = move_line.debit
                    else:
                        res['amount_original'] = move_line.credit
                else:
                    res['amount_original'] = currency_pool.compute(cr, uid, move_line.currency_id.id, voucher_currency, move_line.amount_currency, context=ctx)
            elif move_line and move_line.credit > 0:
                res['amount_original'] = currency_pool.compute(cr, uid, company_currency, voucher_currency, move_line.credit, context=ctx)
            else:
                res['amount_original'] = currency_pool.compute(cr, uid, company_currency, voucher_currency, move_line.debit, context=ctx)

            #hack jool: set date from voucher for the amount_unreconciled
            ctx.update({'date': line.voucher_id.date})
            if move_line:
                res['amount_unreconciled'] = round(currency_pool.compute(cr, uid, move_line.currency_id and move_line.currency_id.id or company_currency, voucher_currency, abs(move_line.amount_residual_currency), round=False, context=ctx),2)
            print 'res: ', res
            print '---------------------------------------------------------------------------------------------'
            rs_data[line.id] = res
        return rs_data
        
    _columns = {
            'amount_original': fields.function(_compute_balance_new, method=True, multi='dc', type='float', string='Original Amount', store=True),
            'amount_unreconciled': fields.function(_compute_balance_new, method=True, multi='dc', type='float', string='Open Balance', store=True),
            'skonto':fields.boolean('Is skonto?', required=False),
        }
        

account_voucher_line_extended()
