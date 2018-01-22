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

class account_invoice_extended(osv.osv):
    _inherit = 'account.invoice'
    
    def action_cancel(self, cr, uid, ids, context=None):
        if context is None:
            context={}
        self.write(cr, uid, ids, {'booking_currency_date': False}, context=context)
        return super(account_invoice_extended, self).action_cancel(cr, uid, ids, context)
    
    def copy(self, cr, uid, id, defaults, context={}):
        defaults['booking_currency_date'] = False
        return super(account_invoice_extended, self).copy(cr, uid, id, defaults, context)
    
    def compute_invoice_totals(self, cr, uid, inv, company_currency, ref, invoice_move_lines, context=None):
        if context is None:
            context={}
        total = 0
        total_currency = 0
        cur_obj = self.pool.get('res.currency')
        for i in invoice_move_lines:
            if inv.currency_id.id != company_currency:
                context.update({'date': context.get('date',inv.date_invoice) or time.strftime('%Y-%m-%d')})
                i['currency_id'] = inv.currency_id.id
                i['amount_currency'] = i['price']
                # HACK: 07.08.2013 16:16:10: olivier: added round=False and rounded it to 2 decimals
                i['price'] = round(cur_obj.compute(cr, uid, inv.currency_id.id,
                        company_currency, i['price'], round=False,
                        context=context),2)
            else:
                i['amount_currency'] = False
                i['currency_id'] = False
            i['ref'] = ref
            if inv.type in ('out_invoice','in_refund'):
                total += i['price']
                total_currency += i['amount_currency'] or i['price']
                i['price'] = - i['price']
            else:
                total -= i['price']
                total_currency -= i['amount_currency'] or i['price']
        return total, total_currency, invoice_move_lines
    
    #ok
    def action_move_create(self, cr, uid, ids, context=None):
        """Creates invoice related analytics and financial move lines"""
        ait_obj = self.pool.get('account.invoice.tax')
        cur_obj = self.pool.get('res.currency')
        period_obj = self.pool.get('account.period')
        payment_term_obj = self.pool.get('account.payment.term')
        journal_obj = self.pool.get('account.journal')
        move_obj = self.pool.get('account.move')
        if context is None:
            context = {}
        for inv in self.browse(cr, uid, ids, context=context):
            if not inv.journal_id.sequence_id:
                raise osv.except_osv(_('Error!'), _('Please define sequence on the journal related to this invoice.'))
            if not inv.invoice_line:
                raise osv.except_osv(_('No Invoice Lines !'), _('Please create some invoice lines.'))
            if inv.move_id:
                continue

            if not inv.date_invoice:
                date = fields.date.context_today(self,cr,uid,context=context)
                self.write(cr, uid, [inv.id], {'date_invoice': date})
            else:
                date = inv.date_invoice

            ctx = context.copy()
            ctx.update({'lang': inv.partner_id.lang})
            ctx.update({'date': date})
            # HACK: 14.01.2014 17:29:01: olivier: set date from original invoice if there is any!!
            if inv.booking_currency_date:
                ctx.update({'date': inv.booking_currency_date})
            else:
                # HACK: 15.01.2014 08:17:11: olivier: set date of currency_rate which will be taken to book this invoice
                cur_rate_date = cur_obj.browse(cr,uid, inv.currency_id.id, context=ctx)
                self.write(cr, uid, [inv.id], {'booking_currency_date': cur_rate_date.rate_date}, context=ctx)
                
            company_currency = inv.company_id.currency_id.id
            # create the analytical lines
            # one move line per invoice line
            iml = self._get_analytic_lines(cr, uid, inv.id, context=ctx)
            # check if taxes are all computed
            compute_taxes = ait_obj.compute(cr, uid, inv.id, context=ctx)
            self.check_tax_lines(cr, uid, inv, compute_taxes, ait_obj)

            # I disabled the check_total feature
            group_check_total_id = self.pool.get('ir.model.data').get_object_reference(cr, uid, 'account', 'group_supplier_inv_check_total')[1]
            group_check_total = self.pool.get('res.groups').browse(cr, uid, group_check_total_id, context=context)
            if group_check_total and uid in [x.id for x in group_check_total.users]:
                if (inv.type in ('in_invoice', 'in_refund') and abs(inv.check_total - inv.amount_total) >= (inv.currency_id.rounding/2.0)):
                    raise osv.except_osv(_('Bad total !'), _('Please verify the price of the invoice !\nThe encoded total does not match the computed total.'))

            if inv.payment_term:
                total_fixed = total_percent = 0
                for line in inv.payment_term.line_ids:
                    if line.value == 'fixed':
                        total_fixed += line.value_amount
                    if line.value == 'procent':
                        total_percent += line.value_amount
                total_fixed = (total_fixed * 100) / (inv.amount_total or 1.0)
                if (total_fixed + total_percent) > 100:
                    raise osv.except_osv(_('Error!'), _("Cannot create the invoice.\nThe related payment term is probably misconfigured as it gives a computed amount greater than the total invoiced amount. In order to avoid rounding issues, the latest line of your payment term must be of type 'balance'."))

            # one move line per tax line
            iml += ait_obj.move_line_get(cr, uid, inv.id)

            entry_type = ''
            if inv.type in ('in_invoice', 'in_refund'):
                ref = inv.reference
                entry_type = 'journal_pur_voucher'
                if inv.type == 'in_refund':
                    entry_type = 'cont_voucher'
            else:
                ref = self._convert_ref(cr, uid, inv.number)
                entry_type = 'journal_sale_vou'
                if inv.type == 'out_refund':
                    entry_type = 'cont_voucher'

            diff_currency_p = inv.currency_id.id <> company_currency
            # create one move line for the total and possibly adjust the other lines amount
            total = 0
            total_currency = 0
            total, total_currency, iml = self.compute_invoice_totals(cr, uid, inv, company_currency, ref, iml, context=ctx)
            acc_id = inv.account_id.id
 
            #hack jool: set inv.id first, because at this time the inv.number is not set
            #name = inv['name'] or '/'
            name = "id_" + str(inv.id) or '/'
            totlines = False
            if inv.payment_term:
                totlines = payment_term_obj.compute(cr,
                        uid, inv.payment_term.id, total, inv.date_invoice or False, context=ctx)
            if totlines:
                res_amount_currency = total_currency
                i = 0
                ctx.update({'date': inv.date_invoice})
                for t in totlines:
                    if inv.currency_id.id != company_currency:
                        amount_currency = cur_obj.compute(cr, uid, company_currency, inv.currency_id.id, t[1], context=ctx)
                    else:
                        amount_currency = False

                    # last line add the diff
                    res_amount_currency -= amount_currency or 0
                    i += 1
                    if i == len(totlines):
                        amount_currency += res_amount_currency

                    iml.append({
                        'type': 'dest',
                        'name': name,
                        'price': t[1],
                        'account_id': acc_id,
                        'date_maturity': t[0],
                        #hack jool1
                        'date_maturity_start': t[2],
                        'amount_currency': diff_currency_p \
                                and amount_currency or False,
                        'currency_id': diff_currency_p \
                                and inv.currency_id.id or False,
                        'ref': ref,
                    })
            else:
                iml.append({
                    'type': 'dest',
                    'name': name,
                    'price': total,
                    'account_id': acc_id,
                    'date_maturity': inv.date_due or False,
                    #hack jool1
                    'date_maturity_start': inv.date_due or False,
                    'amount_currency': diff_currency_p \
                            and total_currency or False,
                    'currency_id': diff_currency_p \
                            and inv.currency_id.id or False,
                    'ref': ref
            })

            date = inv.date_invoice or time.strftime('%Y-%m-%d')

            part = self.pool.get("res.partner")._find_accounting_partner(inv.partner_id)

            line = map(lambda x:(0,0,self.line_get_convert(cr, uid, x, part.id, date, context=ctx)),iml)

            line = self.group_lines(cr, uid, iml, line, inv)

            journal_id = inv.journal_id.id
            journal = journal_obj.browse(cr, uid, journal_id, context=ctx)
            if journal.centralisation:
                raise osv.except_osv(_('User Error!'),
                        _('You cannot create an invoice on a centralized journal. Uncheck the centralized counterpart box in the related journal from the configuration menu.'))

            line = self.finalize_invoice_move_lines(cr, uid, inv, line)

            move = {
                'ref': inv.reference and inv.reference or inv.name,
                'line_id': line,
                'journal_id': journal_id,
                'date': date,
                'narration':inv.comment
            }
            period_id = inv.period_id and inv.period_id.id or False
            ctx.update(company_id=inv.company_id.id,
                       account_period_prefer_normal=True)
            if not period_id:
                period_ids = period_obj.find(cr, uid, inv.date_invoice, context=ctx)
                period_id = period_ids and period_ids[0] or False
            if period_id:
                move['period_id'] = period_id
                for i in line:
                    i[2]['period_id'] = period_id

            ctx.update(invoice=inv)
            move_id = move_obj.create(cr, uid, move, context=ctx)
            new_move_name = move_obj.browse(cr, uid, move_id, context=ctx).name
            # make the invoice point to that move
            self.write(cr, uid, [inv.id], {'move_id': move_id,'period_id':period_id, 'move_name':new_move_name}, context=ctx)
            # Pass invoice in context in method post: used if you want to get the same
            # account move reference when creating the same invoice after a cancelled one:
            move_obj.post(cr, uid, [move_id], context=ctx)
        self._log_event(cr, uid, ids)
        return True
        return super(account_invoice_extended, self).action_move_create(self, cr, uid, ids, context=context)

    #ok
    def line_get_convert(self, cr, uid, x, part, date, context=None):
        res = super(account_invoice_extended, self).line_get_convert(cr, uid, x, part, date, context=context)
        
        #hack jool1
        res['date_maturity_start'] = x.get('date_maturity_start', False)
        res['tax_amount_base'] = x.get('tax_amount_base', False)
        
        return res

    #ok
    def action_number(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        #TODO: not correct fix but required a frech values before reading it.
        self.write(cr, uid, ids, {})
  
        for obj_inv in self.browse(cr, uid, ids, context=context):
            id = obj_inv.id
            invtype = obj_inv.type
            number = obj_inv.number
            move_id = obj_inv.move_id and obj_inv.move_id.id or False
            reference = obj_inv.reference or ''
            #hack jool: if obj_inv.reference is empty -> take obj_inv.origin
            if not reference:
                reference = obj_inv.origin or ''
  
            self.write(cr, uid, ids, {'internal_number':number})
  
            if invtype in ('in_invoice', 'in_refund'):
                if not reference:
                    ref = self._convert_ref(cr, uid, number)
                else:
                    ref = reference
            else:
                ref = self._convert_ref(cr, uid, number)
  
            cr.execute('UPDATE account_move SET ref=%s ' \
                    'WHERE id=%s AND (ref is null OR ref = \'\')',
                    (ref, move_id))
            cr.execute('UPDATE account_move_line SET ref=%s ' \
                    'WHERE move_id=%s AND (ref is null OR ref = \'\')',
                    (ref, move_id))
            cr.execute('UPDATE account_analytic_line SET ref=%s ' \
                    'FROM account_move_line ' \
                    'WHERE account_move_line.move_id = %s ' \
                        'AND account_analytic_line.move_id = account_move_line.id',
                        (ref, move_id))
            #hack jool:update account_move_line.name (id_*) with invoice.number
            cr.execute("UPDATE account_move_line SET name=%s " \
                    "WHERE name='id_%s'",
                    (str(number), id))
        return True
 
#couldn't find out if this is still needed in 7 
#     def create(self, cr, uid, vals, context=None):
#         if context is None:
#             context = {}
#         try:
#             # begin hack by jool1 
#             # Set the correct partner_bank_id
#             invoice_obj = self.pool.get('account.invoice')
#             if 'type' in vals:
#                 type = vals['type']
#             elif 'type' in context:
#                 type = context['type']
#             else:
#                 type = False
#              
#             if 'payment_term' in vals:
#                 payment_term = vals['payment_term']
#             elif 'payment_term' in context:
#                 payment_term = context['payment_term']
#             else:
#                 payment_term = False
#                  
#             if not vals.get('company_id', False):
#                 vals['company_id'] = self.pool.get('res.users').browse(cr, uid, uid).company_id.id
#                  
#             if type:
#                 vals.update(invoice_obj.onchange_partner_id(cr, uid, [], type, vals['partner_id'],date_invoice=False, payment_term=payment_term, partner_bank_id=False, company_id=vals['company_id'])['value'])
#                 if payment_term:
#                     vals['payment_term'] = payment_term
#              
#             # end hack
#              
#             if type and type == 'out_invoice':
#                 if vals.get('date_due', False):
#                     vals['date_due'] = False
#             res = super(account_invoice_extended, self).create(cr, uid, vals, context)
#             return res
#         except Exception, e:
#             if '"journal_id" viol' in e.args[0]:
#                 raise orm.except_orm(_('Configuration Error!'),
#                      _('There is no Accounting Journal of type Sale/Purchase defined!'))
#             else:
#                 raise orm.except_orm(_('Unknown Error'), str(e))        
         
    def change_rounding(self, cr, uid, ids, context=None):
        for inv in self.browse(cr, uid, ids, context=context):
            cur_obj = self.pool.get('res.currency')
            cur_round_id = cur_obj.search(cr, uid, [('name', '=', 'CH5'), ('active', '=', False)])
            if cur_round_id:
                cur_round = cur_obj.browse(cr, uid, cur_round_id[0])
                amount_total_rounded = cur_obj.round(cr, uid, cur_round, inv.amount_total)
            else:
                raise osv.except_osv(_('Error!'), _("Currency CH5 is not existing, so you cannot change rounding."))
            if (inv.amount_total - amount_total_rounded) == 0 and not inv.round_inv_to_05:
                raise osv.except_osv(_('Error!'), _("You cannot change rounding because it is already rounded to 0.05."))
                
            if inv.tax_line:
                #check if the amount of the tax lines is not 0
                total_tax_amount = 0
                for line in inv.tax_line:
                    total_tax_amount += line.amount
                if total_tax_amount == 0:
                    raise osv.except_osv(_('Error!'), _("You cannot change rounding for this tax code."))
                self.write(cr, uid, [inv.id], {'round_inv_to_05': not inv.round_inv_to_05})
            else:
                #do not allow to set round_inv_to_05 when there are no tax lines (because we are adding the diff to the first tax line)
                raise osv.except_osv(_('Error!'), _("You cannot change rounding if there aren't any taxes."))
            
        for inv in self.browse(cr, uid, ids, context=context):
            for line in inv.invoice_line:
                self.pool.get('account.invoice.line').write(cr, uid, [line.id], {'price_unit': line.price_unit})
            
        self.button_reset_taxes(cr, uid, ids, context)
        return True
    
    def write(self, cr, uid, ids, vals, context=None):
        # HACK: 03.03.2016 14:00:28: jool1: set round_inv_to_05 to False if there are no tax_line entries
        if isinstance(ids, (int, long)):
            ids = [ids]
        for inv in self.browse(cr, uid, ids, context=context):
            if not inv.tax_line:
                vals['round_inv_to_05'] = False
        return super(account_invoice_extended, self).write(cr, 1, ids, vals, context=context)
    
    def _get_invoice_line(self, cr, uid, ids, context=None):
        result = {}
        for line in self.pool.get('account.invoice.line').browse(cr, uid, ids, context=context):
            result[line.invoice_id.id] = True
        return result.keys()

    def _get_invoice_tax(self, cr, uid, ids, context=None):
        result = {}
        for tax in self.pool.get('account.invoice.tax').browse(cr, uid, ids, context=context):
            result[tax.invoice_id.id] = True
        return result.keys()
    
    _columns = {
        'booking_currency_date': fields.date('Booking Currency Date'),
        'round_inv_to_05': fields.boolean('Round to 0.05', help='Round invoice to 0.05 after booking (add difference to first tax line)'),
    }
account_invoice_extended()
