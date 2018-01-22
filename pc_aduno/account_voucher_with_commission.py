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
###############################################################################
from openerp.osv import osv, fields
import openerp.addons.decimal_precision as dp
import time
from openerp.tools.translate import _

class account_voucher_with_commission(osv.Model):
    _inherit = 'account.voucher'

    def _get_writeoff_amount_with_commission(self, cr, uid, ids, name, args, context=None):
        res = {}
        for voucher in self.browse(cr, uid, ids, context=context):
            debit = sum([x.amount for x in voucher.line_dr_ids])
            credit = sum([x.amount for x in voucher.line_cr_ids])

            res[voucher.id] =  abs(credit - debit) - abs(voucher.amount)
            continue
            if voucher.amount < 0: 
                res[voucher.id] -= voucher.commission
            else:
                res[voucher.id] += voucher.commission
        return res

    
    _columns = {
        'writeoff_amount': fields.function(_get_writeoff_amount_with_commission,
                                           string='Difference Amount', type='float', readonly=True,
                                           help="Computed as the difference between the amount stated \
                                           in the voucher and the sum of allocation on the voucher lines."),
        'commission': fields.float('Commission', digits_compute=dp.get_precision('Account')),
    }

account_voucher_with_commission()
