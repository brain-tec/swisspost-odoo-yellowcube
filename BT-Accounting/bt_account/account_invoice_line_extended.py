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

from osv import osv, fields, orm
from tools.translate import _
import time
import decimal_precision as dp

class account_invoice_line_ext(osv.osv):
    _inherit = 'account.invoice.line'
    
    def move_line_get(self, cr, uid, invoice_id, context=None):
        res = []
        tax_obj = self.pool.get('account.tax')
        cur_obj = self.pool.get('res.currency')
        if context is None:
            context = {}
        inv = self.pool.get('account.invoice').browse(cr, uid, invoice_id, context=context)
        company_currency = self.pool['res.company'].browse(cr, uid, inv.company_id.id).currency_id.id
        for line in inv.invoice_line:
            mres = self.move_line_get_item(cr, uid, line, context)
            if not mres:
                continue
            res.append(mres)
            tax_code_found= False
            for tax in tax_obj.compute_all(cr, uid, line.invoice_line_tax_id,
                    (line.price_unit * (1.0 - (line['discount'] or 0.0) / 100.0)),
                    line.quantity, line.product_id,
                    inv.partner_id)['taxes']:

                if inv.type in ('out_invoice', 'in_invoice'):
                    tax_code_id = tax['base_code_id']
                    tax_amount = line.price_subtotal * tax['base_sign']
                else:
                    tax_code_id = tax['ref_base_code_id']
                    tax_amount = line.price_subtotal * tax['ref_base_sign']

                if tax_code_found:
                    if not tax_code_id:
                        continue
                    res.append(self.move_line_get_item(cr, uid, line, context))
                    res[-1]['price'] = 0.0
                    res[-1]['account_analytic_id'] = False
                elif not tax_code_id:
                    continue
                tax_code_found = True

                res[-1]['tax_code_id'] = tax_code_id
                #res[-1]['tax_amount'] = cur_obj.compute(cr, uid, inv.currency_id.id, company_currency, tax_amount, context={'date': inv.date_invoice})
                res[-1]['tax_amount'] = cur_obj.compute(cr, uid, inv.currency_id.id, company_currency, tax_amount, context={'date': context.get('date',inv.date_invoice)}, round=False)
        return res
    
    def _amount_line_new(self, cr, uid, ids, prop, unknow_none, unknow_dict):
        res = {}
        tax_obj = self.pool.get('account.tax')
        cur_obj = self.pool.get('res.currency')
        for line in self.browse(cr, uid, ids):
            res[line.id] = {
                'price_subtotal': 0.0,
                'price_total': line.quantity*line.price_unit,
                'price_total_less_disc': line.quantity *(line.price_unit * (1-(line.discount or 0.0)/100.0)),
            }
            price = line.price_unit * (1-(line.discount or 0.0)/100.0)
            taxes = tax_obj.compute_all(cr, uid, line.invoice_line_tax_id, price, line.quantity, product=line.product_id, partner=line.invoice_id.partner_id)
            res[line.id]['price_subtotal'] = taxes['total']
            if line.invoice_id:
                cur = line.invoice_id.currency_id
                # HACK: 17.03.2015 15:58:33: jool1: if round_inv_to_05 is set -> take currency CH5 which has a rounding of 0.05 instead of 0.01
                #check if invoice is in foreign currency
                cur_round = False
                cur_round_id = False
#                 if cur.id == line.invoice_id.company_id.currency_id.id:
                if line.invoice_id.round_inv_to_05:
                    cur_round_id = cur_obj.search(cr, uid, [('name', '=', 'CH5'), ('active', '=', False)])
                else:
                    if cur.id == line.invoice_id.company_id.currency_id.id:
                        cur_round_id = cur_obj.search(cr, uid, [('name', '=', 'CHF'), ('active', '=', False)])
                if cur_round_id:
                    cur_round = cur_obj.browse(cr, uid, cur_round_id[0])
                    
                res[line.id]['price_subtotal'] = cur_obj.round(cr, uid, cur, res[line.id]['price_subtotal'])
#                 res[line.id]['price_subtotal'] = cur_obj.round(cr, uid, cur_chf or cur, res[line.id]['price_subtotal'])
                 # HACK: 18.09.2015 13:47:46: jool1: do rounding for price_total and price_total_less_disc with CHF5
                 # HACK: 07.10.2015 14:23:00: jool1: resort to the default currency if CHF5 is not defined.
                res[line.id]['price_total'] = cur_obj.round(cr, uid, cur_round or cur, res[line.id]['price_total'])
                res[line.id]['price_total_less_disc'] = cur_obj.round(cr, uid, cur_round or cur, res[line.id]['price_total_less_disc'])
        return res
    
    _columns = {
        'price_subtotal': fields.function(_amount_line_new, string='Amount', type="float",
            digits_compute= dp.get_precision('Account'), store=True, multi='all'),
        'price_total': fields.function(_amount_line_new, string='Amount line total', type="float",
            digits_compute= dp.get_precision('Account'), store=True, multi='all'),
        'price_total_less_disc': fields.function(_amount_line_new, string='Amount line total less discount', type="float",
            digits_compute= dp.get_precision('Account'), store=True, multi='all'),
    }
account_invoice_line_ext()