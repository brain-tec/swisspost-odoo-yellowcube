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
from sale.sale import sale_order, sale_order_line
from discount_line import PRODUCT_PRODUCTID_SEPARATOR


class sale_order_ext(osv.osv):

    _inherit = "sale.order"

    def _get_sale_order_line(self, cr, uid, ids, names, arg, context=None):
        res = {}

        for record in self.browse(cr, uid, ids, context=context):
            res[record.id] = []
            for line in record.order_line:
                if line.is_discount:
                    res[record.id].append(line.id)
        return res

    def _amount_all(self, cr, uid, ids, field_name, arg, context=None):
        if context is None:
            context = {}
        context['custom_remove_subtotal'] = True
        return sale_order._amount_all(self, cr, uid, ids, field_name, arg, context)

    def _get_order(self, cr, uid, ids, context=None):
        result = {}
        for line in self.pool.get('sale.order.line').browse(cr, uid, ids, context=context):
            result[line.order_id.id] = True
        return result.keys()

    _columns = {
                'discount_template_id': fields.many2one('stage_discount.discount', 'Template for discounts', help="Use to filter the discount."),
                'discount_line_ids': fields.one2many('stage_discount.discount_line', 'order_id', 'Discount'),
                'test_note': fields.text('Description'),
                'amount_discount': fields.float(_('Applied Discount')),
                'discount_order_line_ids': fields.function(_get_sale_order_line, type="one2many",
                                                             relation="sale.order.line",
                                                             string="Sale Order Line Discount", readonly=True),
                'is_rounded': fields.boolean('Round', help="To round the final amount set this flag to True"),
                        'amount_untaxed': fields.function(_amount_all, digits_compute=dp.get_precision('Account'), string='Untaxed Amount',
            store={
                'sale.order': (lambda self, cr, uid, ids, c={}: ids, ['order_line'], 10),
                'sale.order.line': (_get_order, ['price_unit', 'tax_id', 'discount', 'product_uom_qty'], 10),
            },
            multi='sums', help="The amount without tax.", track_visibility='always'),
        'amount_tax': fields.function(_amount_all, digits_compute=dp.get_precision('Account'), string='Taxes',
            store={
                'sale.order': (lambda self, cr, uid, ids, c={}: ids, ['order_line'], 10),
                'sale.order.line': (_get_order, ['price_unit', 'tax_id', 'discount', 'product_uom_qty'], 10),
            },
            multi='sums', help="The tax amount."),
        'amount_total': fields.function(_amount_all, digits_compute=dp.get_precision('Account'), string='Total',
            store={
                'sale.order': (lambda self, cr, uid, ids, c={}: ids, ['order_line'], 10),
                'sale.order.line': (_get_order, ['price_unit', 'tax_id', 'discount', 'product_uom_qty'], 10),
            },
            multi='sums', help="The total amount."),

                }
    _defaults = {
        'test_note': '',
        'is_rounded': True,
    }

    def button_dummy(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        #
        # @ To check
        #
        for elem in ['custom_search_line_discount', 'custom_search_line_editor']:
            if elem in context:
                del context[elem]
        self.action_apply_discount(cr, uid, ids, context)

        result = super(sale_order_ext, self).button_dummy(cr, uid, ids, context)
        return result

    def action_add_template(self, cr, uid, ids, template_id, discount_line, partner_id=False, context=None):
        '''
        The partner_id will be used for translating the discount line.
        '''

        (context, ids) = make_safe(context, ids)
        discount_line = self.resolve_2many_commands(cr, uid, 'order_line', discount_line, context=context)
        discount_line = [x['id'] for x in discount_line]
        discount_line_ids = self.action_add_discount(cr, uid, ids, template_id, partner_id, context)
        if ids:
            os_object = self.browse(cr, uid, ids, context)[0]
            os_object.write({'discount_line_ids': [(4, x) for x in discount_line]})
            os_object.refresh()
            return {'value': {
                'discount_template_id': False,
                'discount_line_ids': [(4, x) for x in discount_line] + [(4, x.id) for x in os_object.discount_line_ids]
            }}
        else:
            return {'value': {
                'discount_template_id': False,
                'discount_line_ids': [(4, x) for x in discount_line_ids + discount_line]
            }}

    def action_add_discount(self, cr, uid, ids, template_id=False, partner_id=False, context=None):
        '''
        Add to this sale order all the lines of a a template discount.
        These new lines  will be a copy of the original ones.
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
            order_id = False
            if ids:
                order_id = ids[0]
            values = {
                      'discount_id': False,
                      'order_id': order_id,
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
        amount_line_per_account_id_tax[0] = {}
        for line in os_object.order_line:
            if not line.is_discount:
                price = line.price_subtotal
                for tax in line.tax_id:
                    if tax.price_include:
                        uosqty = self.pool.get('sale.order.line')._get_line_qty(cr, uid, line, context=context)
                        price = uosqty * line.price_unit * (1.0 - (line.discount / 100.0))
                        break
                initial_value += price  # line.price_unit * line.quantity
                key = sorted([x.id for x in line.tax_id] + [0])
                key = ','.join(map(str, key))

                if key not in amount_line_per_account_id_tax[0]:
                    amount_line_per_account_id_tax[0][key] = price
                else:
                    amount_line_per_account_id_tax[0][key] += price
        res = ""

        (result, value) = self.pool.get('stage_discount.discount').generic_compute(cr, uid, os_object.discount_line_ids, os_object.is_rounded, os_object.currency_id, amount_line_per_account_id_tax, context)
        final_value += value
        final_result.extend(result)
        res = "{0}\n {1}".format(res, self.pool.get('stage_discount.discount').get_message(cr, uid, ids, result, context))
        res = "Initial value {0} {1} \n End value {2}".format(initial_value, res, final_value)
        self.write(cr, uid, ids, {'test_note': res}, context)
        return final_result

    def action_apply_discount(self, cr, uid, ids, context=None):
        '''
        Apply the discount in this invoice.
        First we remove all the lines that are discount.
        Next we create the account.invoice.line with the flag is_discount = True.
        '''
        if context is None:
            context = {}
        if 'custom_search_line_discount' in context:
            del context['custom_search_line_discount']
        os_object = self.browse(cr, uid, ids, context)[0]
        for line in os_object.order_line:
            if line.is_discount:
                line.unlink()

        final_result = self.__action_compute(cr, uid, ids, context)
        values = []
        x = 0
        # account_invoice_model = self.pool.get('account.account')
        for (result, value, tax_ids, __) in final_result:
            result_split = False
            if result:
                result_split = result.split("#")
            discount_description = ''
            discount_ammount = ''
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
                result = result.split('#')[0]  # This stores the 'description' field.
                values.append({'name': result or 'No name',
                               'price_unit': -value,
                               'is_discount': True,
                               'discount_type': discount_type,
                               'tax_id': [(4, y) for y in tax_ids],
                               'discount_description': discount_description,
                               'discount_amount': discount_ammount,
                               'is_fixed_amount': result_split[1] == 'fixed',
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
                values.append({'name': result or 'No name',
                               'price_unit': value,
                               'quantity': 0,
                               'is_discount': True,
                               'discount_type': discount_type,
                               'is_subtotal': True,
                               'discount_amount': discount_ammount,
                               'discount_description': discount_description,
                               })
        self.write(cr, uid, ids, {'order_line': [(0, 0, v) for v in values],
                                  'amount_discount': x})
        return True

    def write(self, cr, uid, ids, vals, context=None):
        if context is None:
            context = {}
        if 'custom_search_line_discount' in context:
            del context['custom_search_line_discount']
        result = super(sale_order_ext, self).write(cr, uid, ids, vals, context)

        return result

    def copy(self, cr, uid, id, defaults, context={}):
        value_id = super(sale_order_ext, self).copy(cr, uid, id, defaults, context)
        self.action_apply_discount(cr, uid, [value_id], context)
        return value_id

    def onchange_partner_id(self, cr, uid, ids, partner_id, context=None):
        '''
        Add default template to use
        '''
        result = super(sale_order_ext, self).onchange_partner_id(cr, uid, ids, partner_id, context)
        if partner_id:
            discount_id = self.pool.get("res.partner").get_discount_template(cr, uid, partner_id)
            if discount_id > 0:
                # To apply default discount
                if 'value' not in result:
                    result['value'] = {}
                result['value']['discount_template_id'] = discount_id
        return result

    def action_invoice_create(self, cr, uid, ids, grouped=False, states=None, date_invoice = False, context=None):
        if context is None:
            context = {}
        sd_dl_model = self.pool.get('stage_discount.discount_line')
        result = super(sale_order_ext, self).action_invoice_create(cr, uid, ids, grouped, states, date_invoice, context)
        current_discount = []
        for so in self.browse(cr, uid, ids, context):
            for line in so.discount_line_ids:
                current_discount.append(sd_dl_model.copy(cr, uid, line.id, {'order_id': False}, context))

        self.pool.get('account.invoice').write(cr, uid, result, {'discount_line_ids': [(4, x) for x in current_discount]})
        return result

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
