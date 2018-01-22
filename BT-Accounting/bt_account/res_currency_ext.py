# b-*- encoding: utf-8 -*-
##############################################################################
#
#    Copyright (c) 2010 brain-tec AG (http://www.brain-tec.ch) 
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

from osv import osv, fields
from openerp import netsvc
from tools import ustr
from tools.translate import _
import time

class res_currency_ext(osv.osv):
    _inherit = 'res.currency'
    
    def create_ch5_currency_if_does_not_exist(self, cr, uid, context=None):
        ''' Creates the CH5 currency, used to do the rounding, but only if
            not other currency exists with that name.
        '''
        if context is None:
            context = {}

        ch5_exists = self.search(cr, uid, [('name', '=', 'CH5'),
                                           '|',
                                           ('active','=',True),
                                           ('active','=',False)], context=context, count=True)
        if not ch5_exists:
            values = {'name': 'CH5',
                      'rounding': 0.05,
                      'accuracy': 4,
                      'position': 'after',
                      'base': False,
                      'active': False,
                      }
            self.create(cr, uid, values, context=context)

        return True


    def _current_rate_date(self, cr, uid, ids, name, arg, context=None):
        if context is None:
            context = {}
        res = {}
        if 'date' in context:
            date = context['date']
        else:
            date = time.strftime('%Y-%m-%d')
        date = date or time.strftime('%Y-%m-%d')
        # Convert False values to None ...
        currency_rate_type = context.get('currency_rate_type_id') or None
        # ... and use 'is NULL' instead of '= some-id'.
        operator = '=' if currency_rate_type else 'is'
        for id in ids:
            cr.execute("SELECT currency_id, name FROM res_currency_rate WHERE currency_id = %s AND name <= %s AND currency_rate_type_id " + operator +" %s ORDER BY name desc LIMIT 1" ,(id, date, currency_rate_type))
            if cr.rowcount:
                id, name = cr.fetchall()[0]
                res[id] = name
            else:
                res[id] = 0
        return res
    
    _columns = {
        'rate_date': fields.function(_current_rate_date, string='Current Rate Date', type='date', help='The rate date of the currency to the currency of rate 1.', store=False),
    }
    
res_currency_ext()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: