# b-*- encoding: utf-8 -*-
##############################################################################
#
#    Copyright (c) 2014 brain-tec AG (http://www.brain-tec.ch)
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

import decimal_precision as dp
from osv import fields, osv
from tools.translate import _
from one2many_filter.generic import make_safe
from math import ceil
from discount_line import PRODUCT_PRODUCTID_SEPARATOR


class account_invoice_ext(osv.osv):

    _inherit = "account.invoice"
    '''
    Add different discounts in the invoice.
    '''

    def _get_discount_invoice_line(self, cr, uid, ids, names, arg, context=None):
        res = {}

        for record in self.browse(cr, uid, ids, context=context):
            res[record.id] = []
            for line in record.invoice_line:
                if line.is_discount:
                    res[record.id].append(line.id)
        return res

    _columns = {'discount_template_id': fields.many2one('stage_discount.discount', 'Template for discounts', help="Use to filter the discount."),
                'discount_line_ids': fields.one2many('stage_discount.discount_line', 'invoice_id', 'Discount'),
                'test_note': fields.text('Description'),
                'amount_discount': fields.float(_('Applied Discount')),
                'discount_invoice_line_ids': fields.function(_get_discount_invoice_line, type="one2many",
                                                             relation="account.invoice.line",
                                                             string="Account Invoice Line Discount", readonly=True),
                'is_rounded': fields.boolean('Round', help="To round the final amount set this flag to True"),
                }

    _defaults = {
        'test_note': '',
        'is_rounded': True,
    }

    def button_reset_taxes(self, cr, uid, ids, context=None):
        #
        # @ To check
        #
        (context, ids) = make_safe(context, ids)
        for elem in ['custom_search_line_discount']:
            if elem in context:
                del context[elem]
        
        self.action_apply_discount(cr, uid, ids, context)
        result = super(account_invoice_ext, self).button_reset_taxes(cr, uid, ids, context)
        return result

    def action_add_template(self, cr, uid, ids, template_id=False, discount_line=False, partner_id=False, context=None):
        (context, ids) = make_safe(context, ids)
        discount_line = self.resolve_2many_commands(cr, uid, 'discount_line_ids', discount_line, context=context)
        discount_line = [x['id'] for x in discount_line]
        discount_line_ids = self.action_add_discount(cr, uid, ids, template_id, partner_id, context)
        if ids:
            os_object = self.browse(cr, uid, ids, context)[0]
            os_object.write({'discount_line_ids': [(2, x) for x in discount_line]})
            os_object.refresh()
            return {'value': {
                'discount_template_id': False,
                'discount_line_ids': [(4, x.id) for x in os_object.discount_line_ids]}}
        else:
            return {'value': {
                'discount_template_id': False,
                'discount_line_ids': [(4, x) for x in discount_line_ids] + [(2, x) for x in discount_line]}}

    def action_add_discount(self, cr, uid, ids, template_id=False, partner_id=False, context=None):
        '''
        Add to this invoice all the lines of a a template discount.
        These new lines  will be a copy of the original ones.
        The partner_id is used to change the translation of the description line.
        '''
        (context, ids) = make_safe(context, ids)
        stage_discount_discount_model = self.pool.get('stage_discount.discount')
        stage_discount_discount_line_model = self.pool.get('stage_discount.discount_line')

        if not template_id:
            if not ids:
                return []
            os_object = self.browse(cr, uid, ids[0], context)
            if not os_object.discount_template_id:
                return []
            else:
                template_id = os_object.discount_template_id.id

        ctx = context.copy()
        if ids:
            os_object = self.browse(cr, uid, ids[0], context)
            if os_object.partner_id:
                ctx.update({'lang': os_object.partner_id.lang})
        elif partner_id:
            partner = self.pool.get('res.partner').browse(cr, uid, partner_id, context)
            ctx.update({'lang': partner.lang})
        discount_obj = stage_discount_discount_model.browse(cr, uid, template_id, ctx)
        discount_line_ids = []
        self.write(cr, uid, ids, {'is_rounded': discount_obj.is_rounded})

        for line in discount_obj.discount_line_ids:
            invoice_id = False
            if ids:
                invoice_id = ids[0]
            values = {
                      'discount_id': False,
                      'invoice_id': invoice_id,
                      'description': line.description_template
                      }

            new_line_id = stage_discount_discount_line_model.copy(cr, uid, line.id, values, ctx)
            discount_line_ids.append(new_line_id)
        return discount_line_ids

    def __action_compute(self, cr, uid, ids, context=None):
        (context, ids) = make_safe(context, ids)
        os_object = self.browse(cr, uid, ids, context)[0]
        initial_value = 0
        final_value = 0
        final_result = []
        amount_line_per_account_id_tax = {}
        for line in os_object.invoice_line:
            invoice_line = self.pool.get('account.invoice.line').browse(cr, uid, line.id, context)
            if invoice_line.account_analytic_id:
                context['analytic_account'] = invoice_line.account_analytic_id.id
            if not line.is_discount:
                price = line.price_subtotal
                for tax in line.invoice_line_tax_id:
                    if tax.price_include:
                        price = line.price_total_less_disc
                        break
                initial_value += price  # line.price_unit * line.quantity
                key = sorted([x.id for x in line.invoice_line_tax_id] + [0])
                key = ','.join(map(str, key))
                if line.account_id.id not in amount_line_per_account_id_tax:
                    amount_line_per_account_id_tax[line.account_id.id] = {}
                if key not in amount_line_per_account_id_tax[line.account_id.id]:
                    amount_line_per_account_id_tax[line.account_id.id][key] = price
                else:
                    amount_line_per_account_id_tax[line.account_id.id][key] += price
        res = ""

        (result, value) = self.pool.get('stage_discount.discount').generic_compute(cr, uid, os_object.discount_line_ids, os_object.is_rounded, os_object.currency_id, amount_line_per_account_id_tax, context)
        final_value += value
        final_result.extend(result)
        res = "{0}\n {1}".format(res, self.pool.get('stage_discount.discount').get_message(cr, uid, ids, result, context))
        res = "Initial value {0} {1} \n End value {2}".format(initial_value, res, final_value)
        self.write(cr, uid, ids, {'test_note': res}, context)
        return final_result

    def action_move_create(self, cr, uid, ids, context=None):
        '''
        Allow us to remove the subtotal lines when the moves are created
        '''
        (context, ids) = make_safe(context, ids)
        context['custom_remove_subtotal'] = True
        return super(account_invoice_ext, self).action_move_create(cr, uid, ids, context)

    def invoice_validate(self, cr, uid, ids, context=None):
        self.action_apply_discount(cr, uid, ids, context)
        result = super(account_invoice_ext, self).invoice_validate(cr, uid, ids, context)
        (context, ids) = make_safe(context, ids)
        account_invoice = self.browse(cr, uid, ids[0], context)
        if account_invoice.amount_total != account_invoice.residual:
            raise osv.except_osv(_('Usage Error'),
                                _('Please update taxes before continuing.'))
        else:
            return result

    def action_apply_discount(self, cr, uid, ids, context=None):
        '''
        Apply the discount in this invoice.
        First we remove all the lines that are discount.
        Next we create the account.invoice.line with the flag is_discount = True.
        '''
        (context, ids) = make_safe(context, ids)
        if 'custom_search_line_discount' in context:
            del context['custom_search_line_discount']
        os_object = self.browse(cr, uid, ids, context)[0]
        for line in os_object.invoice_line:
            if line.is_discount:
                line.unlink()

        final_result = self.__action_compute(cr, uid, ids, context)
        values = []
        x = 0
        account_invoice_model = self.pool.get('account.account')
        for (result, value, tax_ids, analytic_account) in final_result:
            result_split = False
            if result:
                result_split = result.split("#")
            discount_description = ''
            discount_ammount = ''
            account_id = False
            if result_split:
                discount_description = result_split[0]
                discount_type = result_split[1]
                discount_ammount = result_split[2]

                if discount_type == 'product':
                    # In the case of having a discount of type 'product', we attach the ID to its description,
                    # so we need to unpack it.
                    discount_description, product_id = discount_description.split(PRODUCT_PRODUCTID_SEPARATOR)
                    result = result.split(PRODUCT_PRODUCTID_SEPARATOR)[0]

            if result and discount_type != 'subtotal':
                account_id = result_split[3].split('-')[0]
                result = result.split('#')[0]  # This stores the 'description' field.
                values.append({'name': result or 'No name',
                               'price_unit': -value,
                               'is_discount': True,
                               'discount_type': discount_type,
                               'invoice_line_tax_id': [(4, y) for y in tax_ids],
                               'account_analytic_id': analytic_account,
                               'discount_description': discount_description,
                               'discount_amount': discount_ammount,
                               'is_fixed_amount': result_split[1] == 'fixed',
                               'account_id': account_id,
                               'discount_account_id': account_id
                               }),

                # If the type of discount is a product, then we need to pass the product's id.
                if discount_type == 'product':
                    values[-1].update({'product_id': int(product_id)})

                # We only substract (i.e. add, since it's a negative value) the quantity to be
                # substracted if the type is not 'product'.
                if result_split[1] != 'product':
                    x -= value
            else:
                result = " ".join(result_split[0:2])
                account_id = account_invoice_model.search(cr, uid, [('type', '!=', 'view')])
                if not account_id:
                        raise osv.except_osv(_('Usage Error'),
                                             _('Please create at least one account which type is not view.'))
                else:
                    account_id = account_id[0]

                values.append({'name': result or 'No name',
                               'price_unit': value,
                               'quantity': 0,
                               'is_discount': True,
                               'discount_type': discount_type,
                               'is_subtotal': True,
                               'discount_amount': discount_ammount,
                               'account_id': account_id,
                               'discount_account_id': False,
                               'discount_description': discount_description,
                               })
#         if self.browse(cr, uid, ids[0], context).type == 'out_invoice':
#             rounding_value = self.action_add_rounding_line(cr, uid, ids, context)
#             if rounding_value:
#                 values.append(rounding_value)

        self.write(cr, uid, ids, {'invoice_line': [(0, 0, v) for v in values],
                                  'amount_discount': x})
        return True

    def write(self, cr, uid, ids, vals, context=None):
        (context, ids) = make_safe(context, ids)
        if 'custom_search_line_discount' in context:
            del context['custom_search_line_discount']
        result = super(account_invoice_ext, self).write(cr, uid, ids, vals, context)

        return result

    def copy(self, cr, uid, id, defaults, context={}):
        value_id = super(account_invoice_ext, self).copy(cr, uid, id, defaults, context)
        self.action_apply_discount(cr, uid, [value_id], context)
        return value_id

    def onchange_partner_id(self, cr, uid, ids, type, partner_id, \
            date_invoice=False, payment_term=False, partner_bank_id=False, company_id=False):
        result = super(account_invoice_ext, self).onchange_partner_id(cr, uid, ids, type, partner_id, date_invoice, payment_term, partner_bank_id, company_id)
        '''
        Add default template to use
        '''
        if partner_id:
            discount_id = self.pool.get("res.partner").get_discount_template(cr, uid, partner_id)
            if discount_id > 0:
                # To apply default discount
                if 'value' not in result:
                    result['value'] = {}
                result['value']['discount_template_id'] = discount_id
        return result

    def action_add_rounding_line(self, cr, uid, ids, context=None):
        (context, ids) = make_safe(context, ids)
        account_invoice = self.browse(cr, uid, ids[0], context)
        amount_total = account_invoice.amount_total
        upper_value = 0.05 * ceil(amount_total / 0.05)
        value = upper_value - account_invoice.amount_total
        account_id = False
        for invoice_line in account_invoice.invoice_line:
            if invoice_line.account_id:
                account_id = invoice_line.account_id.id
            if invoice_line.is_rounding_line:
                invoice_line.unlink()
        if not account_id or value <= 0:
            return {}
        return  {'name': 'Rounding line',
                  'price_unit': value,
                  'is_rounding_line': True,
                  'is_discount': True,
                  'is_fixed_amount': True,
                  'discount_amount': value,
                  'account_id': account_id,
                  'description': 'Rounding problem',
                   'discount_account_id': account_id
                                }

    def _prepare_refund(self, cr, uid, invoice, date=None, period_id=None, description=None, journal_id=None, context=None):
            invoice_data = super(account_invoice_ext, self)._prepare_refund( cr, uid, invoice, date, period_id, description, journal_id, context)
            discount_lines_ids = []
            sddl_obj = self.pool.get('stage_discount.discount_line')
            for discount_line in invoice.discount_line_ids:
                discount_line_values = discount_line.read()[0]
                discount_line_values['invoice_id'] = False
                del discount_line_values['id']
                for elem in discount_line_values:
                    if isinstance(discount_line_values[elem], tuple):
                        discount_line_values[elem] = discount_line_values[elem][0]
                    elif isinstance(discount_line_values[elem], list):
                        discount_line_values[elem] = [(4, x) for x in discount_line_values[elem]]
                discount_lines_ids.append(sddl_obj.create(cr, uid, discount_line_values, context=context))
            invoice_data['discount_line_ids'] = [(4, x) for x in discount_lines_ids]
            return invoice_data

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
