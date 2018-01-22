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
    
    def button_cancel(self, cr, uid, ids, context=None):
        # If the bank statement was cancelled then we should also cancel the voucher -> via action_cancel_draft
        voucher_obj = self.pool.get('account.voucher')
        res = super(account_bank_statement_extended, self).button_cancel(cr, uid, ids, context=context)
        for st in self.browse(cr, uid, ids, context=context):
            voucher_ids = []
            for line in st.line_ids:
                if line.voucher_id:
                    voucher_ids.append(line.voucher_id.id)
            voucher_obj.action_cancel_draft(cr, uid, voucher_ids, context)
        return res
    
account_bank_statement_extended()
