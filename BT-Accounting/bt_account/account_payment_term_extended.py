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
import time
from datetime import datetime
from dateutil.relativedelta import relativedelta
from tools import float_round, float_is_zero, float_compare

class account_payment_term_extended(osv.osv):
    _inherit = 'account.payment.term'

    def compute(self, cr, uid, id, value, date_ref=False, context=None):
        if not date_ref:
            date_ref = datetime.now().strftime('%Y-%m-%d')
        pt = self.browse(cr, uid, id, context=context)
        amount = value
        result = []
        obj_precision = self.pool.get('decimal.precision')
        for line in pt.line_ids:
            prec = obj_precision.precision_get(cr, uid, 'Account')
            #hack jool: 6.1 - round amt to 0.05
            if line.value == 'fixed':
#                amt = round(line.value_amount, prec)
                amt = float_round(line.value_amount, precision_rounding=0.05)
            elif line.value == 'procent':
                amt = round(value * line.value_amount, prec)
#                amt = float_round(value * line.value_amount, precision_rounding=0.05)
            elif line.value == 'balance':
                amt = round(amount, prec)
#                amt = float_round(amount, precision_rounding=0.05)
            if amt:
                next_date = (datetime.strptime(date_ref, '%Y-%m-%d') + relativedelta(days=line.days))
                if line.days2 < 0:
                    next_first_date = next_date + relativedelta(day=1,months=1) #Getting 1st of next month
                    next_date = next_first_date + relativedelta(days=line.days2)
                if line.days2 > 0:
                    next_date += relativedelta(day=line.days2, months=1)
                
                #hack jool1 - add date_maturity_start to result
                date_maturity_start = (datetime.strptime(date_ref, '%Y-%m-%d') + relativedelta(days=line.days_maturity))
                result.append( (next_date.strftime('%Y-%m-%d'), amt, date_maturity_start.strftime('%Y-%m-%d')) )
                #result.append( (next_date.strftime('%Y-%m-%d'), amt) )
                amount -= amt
        return result
        return super(account_payment_term_extended, self).compute(self, cr, uid, id, value, date_ref=False, context=None)
        
account_payment_term_extended()
