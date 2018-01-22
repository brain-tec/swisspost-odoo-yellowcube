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

class account_bank_statement_extended(osv.osv):
    _inherit = 'account.bank.statement'
    
    def _end_balance(self, cursor, user, ids, name, attr, context=None):
        print 'END_BALANCE BANK OVERWRITTEN'
        res_currency_obj = self.pool.get('res.currency')
        res_users_obj = self.pool.get('res.users')
        res = {}

        company_currency_id = res_users_obj.browse(cursor, user, user,
                context=context).company_id.currency_id.id

        statements = self.browse(cursor, user, ids, context=context)
        for statement in statements:
            res[statement.id] = statement.balance_start
            currency_id = statement.currency.id
            for line in statement.move_line_ids:
                current_currency_invoice = line.currency_id.id
                if line.debit > 0:
                    if line.account_id.id == \
                            statement.journal_id.default_debit_account_id.id:
                        #hack jool: if currency from bank statement is different from invoice currency then compute currency
                        if current_currency_invoice != currency_id:
                            amount = res_currency_obj.compute(cursor,
                                    user, company_currency_id, currency_id,
                                    line.debit, context=context)
                        else:
                            amount = abs(line.amount_currency)
                        res[statement.id] += amount
                else:
                    if line.account_id.id == \
                            statement.journal_id.default_credit_account_id.id:
                        #hack jool: if currency from bank statement is different from invoice currency then compute currency
                        if current_currency_invoice != currency_id:
                            amount = res_currency_obj.compute(cursor,
                                    user, company_currency_id, currency_id,
                                    line.credit, context=context)
                        else:
                            amount = abs(line.amount_currency)
                        res[statement.id] -= amount
            if statement.state in ('draft', 'open'):
                for line in statement.line_ids:
                    res[statement.id] += line.amount
        for r in res:
            res[r] = round(res[r], 2)
        return res
    
    def button_confirm_bank(self, cr, uid, ids, context=None):
#        print 'OVERWRITTEN button_confirm_bank ids: ', ids
        done = []
        obj_seq = self.pool.get('ir.sequence')
        if context is None:
            context = {}

        for st in self.browse(cr, uid, ids, context=context):
#            print 'st: ', st
            j_type = st.journal_id.type
            company_currency_id = st.journal_id.company_id.currency_id.id
            if not self.check_status_condition(cr, uid, st.state, journal_type=j_type):
                continue

            self.balance_check(cr, uid, st.id, journal_type=j_type, context=context)
            if (not st.journal_id.default_credit_account_id) \
                    or (not st.journal_id.default_debit_account_id):
                raise osv.except_osv(_('Configuration Error!'),
                        _('Please verify that an account is defined in the journal.'))

            if not st.name == '/':
                st_number = st.name
            else:
                c = {'fiscalyear_id': st.period_id.fiscalyear_id.id}
                if st.journal_id.sequence_id:
                    st_number = obj_seq.get_id(cr, uid, st.journal_id.sequence_id.id, context=c)
                else:
                    st_number = obj_seq.get(cr, uid, 'account.bank.statement', context=c)

            for line in st.move_line_ids:
#                print 'line: ', line
                if line.state <> 'valid':
                    raise osv.except_osv(_('Error!'),
                            _('The account entries lines are not in valid state.'))
            for st_line in st.line_ids:
#                print 'st_line: ', st_line
                # HACK: 10.03.2014 10:49:03: olivier: just check this if bankstatement line type is not "General" ("Sonstige")
                if st_line.type != 'general':
                    #hack jool: bank statement cannot be booked if not all vouchers are assigned to an invoice
                    if not st_line.voucher_id:
                        raise osv.except_osv(_('Error!'),
                                _('Please verify that all entries are assigned to an invoice.'))
                if st_line.analytic_account_id:
                    if not st.journal_id.analytic_journal_id:
                        raise osv.except_osv(_('No Analytic Journal !'),_("You have to define an analytic journal on the '%s' journal!") % (st.journal_id.name,))
                #hack jool: also allow to confirm bankstatement when amount is 0 -> invoice over CHF 100.-- allocate with gutschrift CHF 100.--
#                if not st_line.amount:
#                    continue
                st_line_number = self.get_next_st_line_number(cr, uid, st_number, st_line, context)
                self.create_move_from_st_line(cr, uid, st_line.id, company_currency_id, st_line_number, context)

            #self.write(cr, uid, [st.id], {'name': st_number}, context=context)
            self.write(cr, uid, [st.id], {
                    'name': st_number,
                    'balance_end_real': st.balance_end
            }, context=context)
            self.log(cr, uid, st.id, _('Statement %s is confirmed, journal items are created.') % (st_number,))
            done.append(st.id)
#        print 'OVERWRITTEN button_confirm_bank END ids: ', ids
        return self.write(cr, uid, ids, {'state':'confirm'}, context=context)

    def onchange_journal_id(self, cr, uid, statement_id, journal_id, context=None):
        journal_data = self.pool.get('account.journal').read(cr, uid, journal_id, ['default_debit_account_id', 'company_id'], context=context)
        account_id = journal_data['default_debit_account_id']
        
        for statement in self.browse(cr, uid , statement_id):
            for statement_line in statement.line_ids:
                self.pool.get('account.voucher').write(cr, uid, [statement_line.voucher_id.id], {'account_id': account_id[0], 'journal_id': journal_id}, context=context)

        return super(account_bank_statement_extended, self).onchange_journal_id(cr, uid, statement_id, journal_id, context)
    
    _columns = {    
        'balance_end': fields.function(_end_balance, method=True, store=True, string='Balance', help="Closing balance based on Starting Balance and Cash Transactions"),
    }
account_bank_statement_extended()
