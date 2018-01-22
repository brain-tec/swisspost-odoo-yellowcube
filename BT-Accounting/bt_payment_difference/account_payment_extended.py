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

class payment_line_extended(osv.osv):
    _inherit = 'payment.line'

    def _partner_name(self, cr, uid, context=None):
        print '_partner_name: ', context
        if context is None:
            context = {}
        partner_obj = self.pool.get('res.partner')
        if context.has_key('partner_id') and context['partner_id']:
            partner = partner_obj.browse(cr, uid, context['partner_id'], context=context)
            if partner.name:
                return partner.name
        return ''
        
    _columns = {
        'partner_name': fields.char('Partner Name', size=64, required=True),
    }
    
    _order = 'partner_name, name, date'
    
    _defaults = {
        'partner_name': _partner_name,
    }
    
payment_line_extended()

class payment_order_create_ext(osv.osv_memory):
    _inherit = 'payment.order.create'

    def create_payment(self, cr, uid, ids, context=None):
        order_obj = self.pool.get('payment.order')
        line_obj = self.pool.get('account.move.line')
        payment_obj = self.pool.get('payment.line')
        if context is None:
            context = {}
        data = self.browse(cr, uid, ids, context=context)[0]
        line_ids = [entry.id for entry in data.entries]
        if not line_ids:
            return {'type': 'ir.actions.act_window_close'}

        payment = order_obj.browse(cr, uid, context['active_id'], context=context)
        t = None
        line2bank = line_obj.line2bank(cr, uid, line_ids, t, context)

        ## Finally populate the current payment with new lines:
        for line in line_obj.browse(cr, uid, line_ids, context=context):
            if payment.date_prefered == "now":
                #no payment date => immediate payment
                date_to_pay = False
            elif payment.date_prefered == 'due':
                date_to_pay = line.date_maturity
            elif payment.date_prefered == 'fixed':
                date_to_pay = payment.date_scheduled
            #hack jool > v7 ok -> seems to be fixed in v7 -> no it's not!
            if line.partner_id:
                context.update({'partner_id': line.partner_id.id})
            payment_obj.create(cr, uid,{
                    'move_line_id': line.id,
                    'amount_currency': line.amount_to_pay,
                    'bank_id': line2bank.get(line.id),
                    'order_id': payment.id,
                    'partner_id': line.partner_id and line.partner_id.id or False,
                    'communication': line.ref or '/',
                    'state': line.invoice and line.invoice.reference_type != 'none' and 'structured' or 'normal',
                    'date': date_to_pay,
                    'currency': (line.invoice and line.invoice.currency_id.id) or line.journal_id.currency.id or line.journal_id.company_id.currency_id.id,
                }, context=context)
        return {'type': 'ir.actions.act_window_close'}
