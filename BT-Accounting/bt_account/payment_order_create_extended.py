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

class payment_order_create_extended(osv.osv_memory):
    """
    Create a payment object with lines corresponding to the account move line
    to pay according to the date and the mode provided by the user.
    Hypothesis:
    - Small number of non-reconcilied move line, payment mode and bank account type,
    - Big number of partner and bank account.

    If a type is given, unsuitable account Entry lines are ignored.
    """

    _inherit = 'payment.order.create'
    
    def search_entries(self, cr, uid, ids, context=None):
        line_obj = self.pool.get('account.move.line')
        mod_obj = self.pool.get('ir.model.data')
        if context is None:
            context = {}
        data = self.browse(cr, uid, ids, context=context)[0]
        search_due_date = data.duedate
        print 'search_due_date'
        print search_due_date
#        payment = self.pool.get('payment.order').browse(cr, uid, context['active_id'], context=context)

        # Search for move line to pay:
        domain = [('reconcile_id', '=', False), ('account_id.type', '=', 'payable'), ('amount_to_pay', '>', 0)]
        #hack jool1 - check with date_maturity_start and not date_maturity
        domain = domain + ['|', ('date_maturity_start', '<=', search_due_date), ('date_maturity_start', '=', False), ('date_maturity', '<=', search_due_date)]
        line_ids = line_obj.search(cr, uid, domain, context=context)
        context.update({'line_ids': line_ids})
        model_data_ids = mod_obj.search(cr, uid,[('model', '=', 'ir.ui.view'), ('name', '=', 'view_create_payment_order_lines')], context=context)
        resource_id = mod_obj.read(cr, uid, model_data_ids, fields=['res_id'], context=context)[0]['res_id']
        return {'name': ('Entrie Lines'),
                'context': context,
                'view_type': 'form',
                'view_mode': 'form',
                'res_model': 'payment.order.create',
                'views': [(resource_id,'form')],
                'type': 'ir.actions.act_window',
                'target': 'new',
        }
        return super(payment_order_create_extended, self).search_entries(self, cr, uid, ids, context=None)
        
payment_order_create_extended()
