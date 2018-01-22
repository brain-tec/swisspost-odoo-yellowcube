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
from bt_helper.tools import bt_format

class account_invoice_tax_extended(osv.osv):
    _inherit = 'account.invoice.tax'

    _columns = {
        'tax_id': fields.many2one('account.tax', 'Tax', help="Tax"),
    }
    
    def move_line_get(self, cr, uid, invoice_id):
        res = []
        cr.execute('SELECT * FROM account_invoice_tax WHERE invoice_id=%s', (invoice_id,))
        for t in cr.dictfetchall():
            if not t['amount'] \
                    and not t['tax_code_id'] \
                    and not t['tax_amount']:
                continue
            res.append({
                'type':'tax',
                'name':t['name'],
                'price_unit': t['amount'],
                'quantity': 1,
                'price': t['amount'] or 0.0,
                'account_id': t['account_id'],
                'tax_code_id': t['tax_code_id'],
                'tax_amount': t['tax_amount'],
                'account_analytic_id': t['account_analytic_id'],
                # HACK: 17.07.2013 11:47:48: olivier: added tax_amount_base
                'tax_amount_base': t['base_amount'],
            })
        return res

    def compute(self, cr, uid, invoice_id, context=None):
        tax_grouped = {}
        tax_obj = self.pool.get('account.tax')
        cur_obj = self.pool.get('res.currency')
        inv = self.pool.get('account.invoice').browse(cr, uid, invoice_id, context=context)
        cur = inv.currency_id
        # HACK: 17.03.2015 15:58:33: jool1: if round_inv_to_05 is set -> take currency CH5 which has a rounding of 0.05 instead of 0.01
        if inv.round_inv_to_05:
            cur_id = cur_obj.search(cr, uid, [('name', '=', 'CH5'), ('active', '=', False)])
            if cur_id:
                cur = cur_obj.browse(cr, uid, cur_id[0])
        company_currency = self.pool['res.company'].browse(cr, uid, inv.company_id.id).currency_id.id
        for line in inv.invoice_line:
            for tax in tax_obj.compute_all(cr, uid, line.invoice_line_tax_id, (line.price_unit* (1-(line.discount or 0.0)/100.0)), line.quantity, line.product_id, inv.partner_id)['taxes']:
                val={}
                val['tax_id'] = tax['id']
                val['invoice_id'] = inv.id
                val['name'] = tax['name']
                val['amount'] = tax['amount']
                val['manual'] = False
                val['sequence'] = tax['sequence']
                val['base'] = cur_obj.round(cr, uid, cur, tax['price_unit'] * line['quantity'])

                if inv.type in ('out_invoice','in_invoice'):
                    val['base_code_id'] = tax['base_code_id']
                    val['tax_code_id'] = tax['tax_code_id']
#                     val['base_amount'] = cur_obj.compute(cr, uid, inv.currency_id.id, company_currency, val['base'] * tax['base_sign'], context={'date': inv.date_invoice or time.strftime('%Y-%m-%d')}, round=False)
#                     val['tax_amount'] = cur_obj.compute(cr, uid, inv.currency_id.id, company_currency, val['amount'] * tax['tax_sign'], context={'date': inv.date_invoice or time.strftime('%Y-%m-%d')}, round=False)
                    val['base_amount'] = cur_obj.compute(cr, uid, inv.currency_id.id, company_currency, val['base'] * tax['base_sign'], context={'date': context.get('date',inv.date_invoice) or time.strftime('%Y-%m-%d')}, round=False)
                    val['tax_amount'] = cur_obj.compute(cr, uid, inv.currency_id.id, company_currency, val['amount'] * tax['tax_sign'], context={'date': context.get('date',inv.date_invoice) or time.strftime('%Y-%m-%d')}, round=False)
                    val['account_id'] = tax['account_collected_id'] or line.account_id.id
                    val['account_analytic_id'] = tax['account_analytic_collected_id']
                else:
                    val['base_code_id'] = tax['ref_base_code_id']
                    val['tax_code_id'] = tax['ref_tax_code_id']
#                     val['base_amount'] = cur_obj.compute(cr, uid, inv.currency_id.id, company_currency, val['base'] * tax['ref_base_sign'], context={'date': inv.date_invoice or time.strftime('%Y-%m-%d')}, round=False)
#                     val['tax_amount'] = cur_obj.compute(cr, uid, inv.currency_id.id, company_currency, val['amount'] * tax['ref_tax_sign'], context={'date': inv.date_invoice or time.strftime('%Y-%m-%d')}, round=False)
                    val['base_amount'] = cur_obj.compute(cr, uid, inv.currency_id.id, company_currency, val['base'] * tax['ref_base_sign'], context={'date': context.get('date',inv.date_invoice) or time.strftime('%Y-%m-%d')}, round=False)
                    val['tax_amount'] = cur_obj.compute(cr, uid, inv.currency_id.id, company_currency, val['amount'] * tax['ref_tax_sign'], context={'date': context.get('date',inv.date_invoice) or time.strftime('%Y-%m-%d')}, round=False)
                    val['account_id'] = tax['account_paid_id'] or line.account_id.id
                    val['account_analytic_id'] = tax['account_analytic_paid_id']

                key = (val['tax_code_id'], val['base_code_id'], val['account_id'], val['account_analytic_id'])
                if not key in tax_grouped:
                    tax_grouped[key] = val
                else:
                    tax_grouped[key]['amount'] += val['amount']
                    tax_grouped[key]['base'] += val['base']
                    tax_grouped[key]['base_amount'] += val['base_amount']
                    tax_grouped[key]['tax_amount'] += val['tax_amount']

        for t in tax_grouped.values():
            t['base'] = cur_obj.round(cr, uid, cur, t['base'])
            t['amount'] = cur_obj.round(cr, uid, cur, t['amount'])
            t['base_amount'] = cur_obj.round(cr, uid, cur, t['base_amount'])
            t['tax_amount'] = cur_obj.round(cr, uid, cur, t['tax_amount'])
            
            # HACK: 24.06.2014 14:04:05: olivier: especially for customer trimada
            #hack jool: just do hack if bool "round not to 0.05" is False
#             if inv.round_taxes:
#                 # HACK: 24.06.2014 13:48:39: olivier: v7 we now have the problem that the price_type is not on the invoice anymore, so we have to look in the tax if the flag is incl. or excl.
#                 #hack by wysi1 to round the tax for swiss standard
# #                 if t['amount'] == t['tax_amount'] and inv.price_type == "tax_excluded":
#                 tax = tax_obj.browse(cr, uid, t['tax_id'], context=context)
#                 if t['amount'] == t['tax_amount'] and tax.price_include == False:
#                     t['amount'] = round(t['amount']/0.05)*0.05
#                     t['tax_amount'] = round(t['tax_amount']/0.05)*0.05

        print 'tax_grouped: ', tax_grouped
        
        # HACK: 18.09.2015 13:47:46: jool1: check if amount_total - total_price_total_less_disc != 0 -> the diff should be added or subtracted to the first tax line (max +/-0.02)
        # HACK: 16.12.2015 16:53:15: jool1: add taxes just if the tax have the flag "tax incl." set, otherwise do not add the amount_tax
        # HACK: 16.12.2015 16:53:15: jool1: get info of first line (we need to assume that there is always price_include set or not for all the taxes in one invoice)
        #check if all taxes are either price_include or not -> otherwise bring a warning
        check_all_equal = all(tax_line.tax_id.price_include==inv.tax_line[0].tax_id.price_include for tax_line in inv.tax_line)
        if not check_all_equal:
            raise osv.except_osv(_('Error!'), _("The value 'Tax Included in Price' for taxes in the invoice lines cannot be mixed. They must either all be 'Tax Included in Price' or not."))
        price_include = False
        for tax_line in inv.tax_line:
            price_include = tax_line.tax_id.price_include
        
        amount_total = inv.amount_untaxed
        if price_include:
            amount_total += inv.amount_tax
        total_price_total_less_disc = 0.0
        for line in inv.invoice_line:
            total_price_total_less_disc += line.price_total_less_disc
        calculated_diff = round(total_price_total_less_disc - amount_total,2)
        if not bt_format.check_if_zero(calculated_diff):
            if inv.tax_line:
                for tax_line in inv.tax_line:
                    # just add calculated_diff if amount of tax_id is not 0 (0.0% tax line)
                    # hack jool1 20161129: only add/substract diff to tax_line if tax_line.amount is not zero
                    if tax_line.tax_id.amount != 0 and not bt_format.check_if_zero(tax_line.amount) and not bt_format.check_if_zero(calculated_diff):
                        if tax_line.amount > 0:
                            new_tax_line_amount = tax_line.amount + calculated_diff
                        else:
                            new_tax_line_amount = tax_line.amount - calculated_diff
                            
                        if tax_line.tax_amount > 0:
                            new_tax_line_tax_amount = tax_line.tax_amount + calculated_diff
                        else:
                            new_tax_line_tax_amount = tax_line.tax_amount - calculated_diff
                        # set calculated_diff to 0, otherwise it will be added to each line which is not correct
                        calculated_diff = 0
                        if tax_line.amount > 0 and new_tax_line_amount < 0 or tax_line.amount < 0 and new_tax_line_amount > 0:
                            new_tax_line_amount = 0
                        if tax_line.tax_amount > 0 and new_tax_line_tax_amount < 0 or tax_line.tax_amount < 0 and new_tax_line_tax_amount > 0:
                            new_tax_line_tax_amount = 0
                        self.pool.get('account.invoice.tax').write(cr, uid, [tax_line.id], {'amount': new_tax_line_amount, 'tax_amount': new_tax_line_tax_amount})
        # END HACK: 18.09.2015 13:47:46: jool1: check if amount_total - total_price_total_less_disc != 0 -> the diff should be added or subtracted to the first tax line (max +/-0.02)
        return tax_grouped

account_invoice_tax_extended()
