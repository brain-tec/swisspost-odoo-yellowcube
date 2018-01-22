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
from lxml import etree

from osv import osv, fields

class account_payment_populate_statement_extended(osv.osv_memory):
    _inherit = 'account.payment.populate.statement'
    
    def populate_statement(self, cr, uid, ids, context=None):
        print 'populate_statement bt_account/account_payment_populate_statement_extended.py'
        line_obj = self.pool.get('payment.line')
        statement_obj = self.pool.get('account.bank.statement')
        statement_line_obj = self.pool.get('account.bank.statement.line')
        currency_obj = self.pool.get('res.currency')
        voucher_obj = self.pool.get('account.voucher')
        voucher_line_obj = self.pool.get('account.voucher.line')
        move_line_obj = self.pool.get('account.move.line')

        if context is None:
            context = {}
        data = self.read(cr, uid, ids, [], context=context)[0]
        line_ids = data['lines']
        if not line_ids:
            return {'type': 'ir.actions.act_window_close'}

        statement = statement_obj.browse(cr, uid, context['active_id'], context=context)

        for line in line_obj.browse(cr, uid, line_ids, context=context):
            ctx = context.copy()
            ctx['date'] = line.ml_maturity_date # was value_date earlier,but this field exists no more now
            amount = currency_obj.compute(cr, uid, line.currency.id,
                    statement.currency.id, line.amount_currency, context=ctx)

            #hack jool
            context.update({'partner_id': line.partner_id.id})
            context.update({'move_line_ids': [line.move_line_id.id]})
            #hack jool1 - added today because it crashed
            today = time.strftime("%Y-%m-%d")
            result = voucher_obj.onchange_partner_id(cr, uid, [], partner_id=line.partner_id.id, journal_id=statement.journal_id.id, amount=abs(amount), currency_id= statement.currency.id, ttype='payment', date=today, context=context)

            if line.move_line_id:
                voucher_res = {
                        'type': 'payment',
                        'name': line.name,
                        'partner_id': line.partner_id.id,
                        'journal_id': statement.journal_id.id,
                        'account_id': result.get('account_id', statement.journal_id.default_credit_account_id.id),
                        'company_id': statement.company_id.id,
                        'currency_id': statement.currency.id,
                        #hack jool: take date from statement instead of line
                        #'date': line.date or time.strftime('%Y-%m-%d'),
                        'date': statement.date or time.strftime('%Y-%m-%d'),
                        'amount': abs(amount),
                        'period_id': statement.period_id.id
                }
                print 'bt_account/account_payment_populate_statement_extended.py create voucher'
                voucher_id = voucher_obj.create(cr, uid, voucher_res, context=context)
#                 voucher_line_dict =  False
#                 if result['value']['line_ids']:
#                     for line_dict in result['value']['line_ids']:
#                         move_line = move_line_obj.browse(cr, uid, line_dict['move_line_id'], context)
#                         if line.move_line_id.move_id.id == move_line.move_id.id:
#                             voucher_line_dict = line_dict
                voucher_line_dict =  {}
                for line_dict in result['value']['line_cr_ids'] + result['value']['line_dr_ids']:
                    move_line = move_line_obj.browse(cr, uid, line_dict['move_line_id'], context)
                    if line.move_line_id.move_id.id == move_line.move_id.id:
                        voucher_line_dict = line_dict
                        
                if voucher_line_dict:
                    voucher_line_dict.update({'voucher_id': voucher_id})
                    voucher_line_obj.create(cr, uid, voucher_line_dict, context=context)

                st_line_id = statement_line_obj.create(cr, uid, {
                    'name': line.order_id.reference or '?',
                    'amount': - amount,
                    'type': 'supplier',
                    'partner_id': line.partner_id.id,
                    'account_id': line.move_line_id.account_id.id,
                    'statement_id': statement.id,
                    'ref': line.communication,
                    'voucher_id': voucher_id,
                    #hack jool
                    'date': statement.date or time.strftime('%Y-%m-%d'),
                    }, context=context)

                line_obj.write(cr, uid, [line.id], {'bank_statement_line_id': st_line_id})
        return {'type': 'ir.actions.act_window_close'}
        return super(account_payment_populate_statement_extended, self).populate_statement(self, cr, uid, ids, context=None)

account_payment_populate_statement_extended()
