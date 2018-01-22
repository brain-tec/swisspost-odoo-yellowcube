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
    
    def onchange_amount(self, cr, uid, ids, amount, context=None):
        # If the line already has a voucher_id and the state of it is 'draft'
        # it means this bank statement was cancelled before and we should delete
        # the voucher AND clear the field voucher_id.
        if ids:
            for line in self.browse(cr, uid, ids, context=context):
                if line.voucher_id and line.voucher_id.state == 'draft':
                    # Instead of orphaning this draft voucher, we will delete it
                        line.voucher_id.unlink()
        return {'value' : {'voucher_id' : False}}
    
account_bank_statement_line_extended()
