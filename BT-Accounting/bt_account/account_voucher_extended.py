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

class account_voucher_line_extended(osv.osv):
    _inherit = 'account.voucher.line'

    def onchange_move_line_id(self, cr, user, ids, move_line_id, voucher_id, context=None):
        """
        Returns a dict that contains new values and context

        @param move_line_id: latest value from user input for field move_line_id
        @param args: other arguments
        @param context: context arguments, like lang, time zone

        @return: Returns a dict which contains new values, and context
        """
        print "onchange_move_line_id"
        print 'move_line_id'
        print move_line_id
        print 'voucher_id'
        print voucher_id
        print 'context'
        print context
        print 'ids'
        print ids
        #hack jool
        currency_pool = self.pool.get('res.currency')
                
        res = {}
        move_line_pool = self.pool.get('account.move.line')
        voucher_pool = self.pool.get('account.voucher')
        if move_line_id:
            move_line = move_line_pool.browse(cr, user, move_line_id, context=context)
            if move_line.credit:
                ttype = 'dr'
                amount = move_line.credit
            else:
                ttype = 'cr'
                amount = move_line.debit

            #hack jool: set company and voucher currency for computing the amount
            if voucher_id:
                voucher = voucher_pool.browse(cr, user, voucher_id, context=context)
                ctx = context.copy()
                ctx.update({'date': voucher.date})
                company_currency = voucher.journal_id.company_id.currency_id.id
                voucher_currency = voucher.currency_id.id
                amount = currency_pool.compute(cr, user, move_line.currency_id and move_line.currency_id.id or company_currency, voucher_currency, abs(move_line.amount_residual_currency), context=ctx)
                            
            account_id = move_line.account_id.id
            res.update({
                'account_id':account_id,
                'type': ttype,
                #hack jool1
                'amount': amount,
            })
        return {
            'value':res,
        }
        return super(account_voucher_line_extended, self).onchange_move_line_id(self, cr, user, ids, move_line_id, context=None)

account_voucher_line_extended()
