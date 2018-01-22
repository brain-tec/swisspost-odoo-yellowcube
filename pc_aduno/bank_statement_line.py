# b-*- encoding: utf-8 -*-
##############################################################################
#
#    Copyright (c) 2016 brain-tec AG (http://www.braintec-group.com) 
#    All Right Reserved
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
from openerp.osv.orm import Model, fields
import openerp.addons.decimal_precision as dp


class  account_bank_statement_line_with_commission(Model):
    _inherit = "account.bank.statement.line"

    def _open_amount_invoice_get(self, cr, uid, ids, name, args, context=None):
        res = super(account_bank_statement_line_with_commission, self)._open_amount_invoice_get(cr, uid, ids, name, args, context=context)
        commission_dp = self.pool['decimal.precision'].precision_get(cr, uid, 'Account')
        for line in self.browse(cr, uid, ids, context=context):
            if line.amount:
                if res[line.id] > 0 and line.voucher_id.commission:
                    res[line.id] -= round(line.voucher_id.commission, commission_dp)
        return res

    _columns = {
        'open_amount_invoice': fields.function(_open_amount_invoice_get, method=True,
                                               string='Open Amount Invoice'),
        'commission': fields.float('Commission', digits_compute=dp.get_precision('Account')),
    }
