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
from osv import osv, fields
from openerp import netsvc
from tools import ustr
import openerp.addons.decimal_precision as dp
from one2many_filter.generic import make_safe
from bt_helper.log_rotate import get_log
from openerp.tools.translate import _
logger = get_log()

class discount(osv.osv):
    _name = "stage_discount.discount"
    _description = "Discount"
    _columns = {
        'name': fields.char('Discount', size=64, translate=True, required=True),
        'active': fields.boolean('Active', help="If the active field is set to False, it will allow you to hide the discount without removing it."),
        'description': fields.text('Description', translate=True),
        'discount_line_ids': fields.one2many('stage_discount.discount_line', 'discount_id', 'Discount lines'),
        'sequence': fields.integer('Sequence'),
        #
        # Testing values
        #
        'test_note': fields.text('Test note', help="Value used for testing purposes"),
        'test_value': fields.integer('Value', help="Value used for testing purposes"),
        'test_tax_ids': fields.many2many('account.tax',
                                         'discount_tax',
                                         'discount_id',
                                         'tax_id',
                                         'Taxes for testing',
                                         domain=[('parent_id', '=', False)], help="Value used for testing purposes"),
        'is_rounded': fields.boolean('Round', help="To round the final amount set this flag to True"),
    }
    _defaults = {
        'active': 1,
        'sequence': 0,
        'is_rounded': False,
    }
    _order = "sequence"

    def action_test_the_value(self, cr, uid, ids, context=None):
        '''
        Test action.
        Will take the test values and show the results.
        '''
        (context, ids) = make_safe(context, ids)
        var_id = ids[0]
        os_object = self.browse(cr, uid, var_id, context)
        test_tax_ids = [0] + [x.id for x in os_object.test_tax_ids]
        test_tax_key = ",".join(map(str, test_tax_ids))
        (result, final_quantity) = self.compute(cr, uid, var_id, {'0': {test_tax_key: os_object.test_value}}, context)
        res = "Initial value {0} {1} \n  End value {2}".format(os_object.test_value, self.get_message(cr, uid, ids, result, context), final_quantity)
        self.write(cr, uid, var_id, {'test_note': res}, context)
        return res

    def get_message(self, cr, uid, ids, result, context):
        res = ''
        for (description, quantity, tax_ids, analytic_account) in result:
            obj_taxes = self.pool.get('account.tax').browse(cr, uid, tax_ids, context)
            names = [x.name for x in obj_taxes]
            tax_str = ', '.join(names)
            if analytic_account:
                analytic_account = self.pool.get('account.analytic.account').browse(cr, uid, analytic_account, context).name
            else:
                analytic_account = ''
            if tax_str:
                tax_str = "{0} {1}".format('Taxes', tax_str)
            else:
                tax_str = "No taxes"
            res = "{0}\n{1}. Quantity to discount {2}. {3}. {4}".format(res, description, quantity, tax_str, analytic_account)
        return res

    def compute(self, cr, uid, var_id, amount_line_per_tax, context=None):
        (context, ids) = make_safe(context, var_id)
        os_object = self.browse(cr, uid, ids, context)[0]
        user = self.pool.get('res.users').browse(cr, uid, uid, context=context)
        return self.generic_compute(cr, uid, os_object.discount_line_ids, os_object.is_rounded, user.company_id.currency_id, amount_line_per_tax, context)

    def get_account_name(self, cr, uid, account_id, account_name_by_id, context):
        if account_id == 0:
            return 'No account'
        if account_id not in account_name_by_id:
            account_name_by_id[account_id] = self.pool.get('account.account').browse(cr, uid, account_id, context).name
        return account_name_by_id[account_id]

    def generic_compute(self, cr, uid, discount_line_ids, is_rounded, currency, amount_line_per_account_id_tax, context=None):
        '''
        Will take one discount, and will process the discount.
        @param var_id : The id of the discount to calculate.
        @type var_id: id of discount.
        @param amount_line_per_tax :
                        key => List of taxes.
                        value => Value of the lines
        @type amount_line_per_tax: dictionary
        @rtype Tuple of two elements:
                First element: list of 3 elements tuple:
                    Each element (a, b, c, d):
                        a) Description of the discount.
                        b) Value of the discount
                        c) Taxes applied in this discount.
                        d) Analytic account
                Second element: Calculated value after applying the discount.
        '''
        if context is None:
            context = {}
        current_calculation = {}
        last_subtotal = {}
        for elem in amount_line_per_account_id_tax:
            current_calculation[elem] = amount_line_per_account_id_tax[elem].copy()
            last_subtotal[elem] = amount_line_per_account_id_tax[elem].copy()
        result = []
        obj_precision = self.pool.get('decimal.precision')
        prec = obj_precision.precision_get(cr, uid, 'Account')
        last_operation = False
        cur_obj = self.pool.get('res.currency')
        account_name_by_id = {}
        """
        Initially we always add a subtotal line
        """
        discount_line_obj = self.pool.get("stage_discount.discount_line")
        aux_discount_line = []
        aux_discount_line_id = False
        if len(discount_line_ids) > 0:
            aux_discount_line_id = discount_line_obj.create(cr, uid, {
                                                                       'discount_type': 'subtotal',
                                                                       'description': 'Subtotal',
                                                                   })
            aux_discount_line.append(discount_line_obj.browse(cr, uid, aux_discount_line_id, context))
        '''
        End adding the initial subtotal line
        '''
        for discount_line in aux_discount_line + discount_line_ids:
            global_account_id = False
            logger.debug("Current calculation")
            logger.debug(current_calculation)
            if discount_line.account_id:
                global_account_id = discount_line.account_id.id

            total_amount = 0
            for account_id in last_subtotal:
                total_amount += sum(last_subtotal[account_id].values())

            if last_operation and last_operation == 'subtotal' and last_operation == discount_line.discount_type:
                continue
            last_operation = discount_line.discount_type
            '''
            -- amt will contain the amount to discount.
            If fixed => Then we get the line.discount_value.
            If percentage =>  Calculate the percentage * value or percentage * amount
            If balance => We round the price.
            '''
            amt = False
            analytic_account = context.get('analytic_account', False)
            if discount_line.account_analytic_id:
                analytic_account = discount_line.account_analytic_id.id
            if discount_line.discount_type == 'subtotal':
                total_amount = 0
                for elem in current_calculation:
                    last_subtotal[elem] = current_calculation[elem].copy()
                    total_amount += sum(last_subtotal[elem].values())

                result.append((discount_line.get_description(), total_amount, [], analytic_account))

            elif discount_line.discount_type in ('fixed', 'product'):
                # The types 'fixed' and 'product' are similar, since in both cases the quantity to be
                # substracted is fixed. The difference is the message which is shown to the user in the
                # 'Description' field, which is the name of the product when discount_type=='product'.
                amt = round(discount_line.discount_value, prec)
                '''
                Get the proportion of each tax-value substract substract it
                a) First get the total amount of current taxes
                    This is calculated in the first loop.
                    Variable total_amount contains the sum of these values.
                b) Update for each acount_id the value:
                    value = current_value - amt * current_value / total_amount.
                '''
                last_account_id = False
                last_key = False
                last_value = False
                last_tax_ids = False
                last_account_name = False
                total_amount_pending = 0
                for account_id in last_subtotal:
                    last_account_id = account_id
                    account_name = self.get_account_name(cr, uid, account_id, account_name_by_id, context)
                    last_account_name = account_name
                    for key in last_subtotal[account_id]:
                        last_key = key
                        # Get the key
                        tax_ids = map(int, key.split(","))
                        if 0 in tax_ids:
                            tax_ids.remove(0)
                        last_tax_ids = tax_ids
                        current_value = last_subtotal[account_id][key]
                        value = 0
                        if total_amount != 0:
                            value = amt * current_value / total_amount
                        if discount_line.is_rounded:
                            # HACK: 17.03.2015 15:58:33: jool1: if round_inv_to_05 is set -> take currency CH5 which has a rounding of 0.05 instead of 0.01
                            cur_id = cur_obj.search(cr, uid, [('name', '=', 'CH5'), ('active', '=', False)])
                            if cur_id:
                                currency = cur_obj.browse(cr, uid, cur_id[0], context=context)
                            value = cur_obj.round(cr, uid, currency, value)
                        value = round(value, prec)
                        last_value = value
                        if not global_account_id:
                            message = discount_line.get_description() + "#{0}-{1}#Applied to {2}".format(account_id, account_name, last_subtotal[account_id][key])
                            result.append((message, value, tax_ids, analytic_account))
                        current_calculation[account_id][key] -= value
                        total_amount_pending -= value
                logger.debug("Current fix discounted amount {0}".format(amt))
                if (amt + total_amount_pending) > 0:
                    logger.debug("We need to update the final amount because it differs into {0}".format(amt + total_amount_pending))
                    del result[-1]
                    last_value -= (amt + total_amount_pending)
                    if not global_account_id:
                        message = discount_line.get_description() + "#{0}-{1}#Applied to {2}".format(last_account_id, last_account_name, last_subtotal[last_account_id][last_key])
                        result.append((message, last_value, last_tax_ids, analytic_account))
                    current_calculation[last_account_id][last_key] -= last_value
                if global_account_id:
                    account_name = self.get_account_name(cr, uid, global_account_id, account_name_by_id, context)
                    message = discount_line.get_description() + "#{0}-{1}#Applied to {2}".format(global_account_id, account_name, total_amount)
                    result.append((message, amt, [x.id for x in discount_line.tax_ids], analytic_account))

            elif discount_line.discount_type == 'percentage':
                logger.debug("Checking percentage")
                amt = 0
                for account_id in last_subtotal:
                    account_name = self.get_account_name(cr, uid, account_id, account_name_by_id, context)
                    for key in last_subtotal[account_id]:
                        tax_ids = map(int, key.split(","))
                        if 0 in tax_ids:
                            tax_ids.remove(0)
                        value = (last_subtotal[account_id][key] * discount_line.discount_value / 100.0)
                        if discount_line.is_rounded:
                            # HACK: 17.03.2015 15:58:33: jool1: if round_inv_to_05 is set -> take currency CH5 which has a rounding of 0.05 instead of 0.01
                            cur_id = cur_obj.search(cr, uid, [('name', '=', 'CH5'), ('active', '=', False)], context=context)
                            if cur_id:
                                currency = cur_obj.browse(cr, uid, cur_id[0])
                            value = cur_obj.round(cr, uid, currency, value)
                        value = round(value, prec)
                        if not global_account_id:
                            result.append((discount_line.get_description() + "#{0}-{1}#Applied to {2}".format(account_id, account_name, last_subtotal[account_id][key]), value, tax_ids, analytic_account))
                        current_calculation[account_id][key] -= value
                        amt += value
                if global_account_id:
                    if discount_line.is_rounded:
                        # HACK: 17.03.2015 15:58:33: jool1: if round_inv_to_05 is set -> take currency CH5 which has a rounding of 0.05 instead of 0.01
                        cur_id = cur_obj.search(cr, uid, [('name', '=', 'CH5'), ('active', '=', False)], context=context)
                        if cur_id:
                            currency = cur_obj.browse(cr, uid, cur_id[0], context=context)
                        amt = cur_obj.round(cr, uid, currency, amt)
                    account_name = self.get_account_name(cr, uid, global_account_id, account_name_by_id, context)
                    result.append((discount_line.get_description() + "#{0}-{1}#Applied to {2}".format(global_account_id, account_name, total_amount), amt, [x.id for x in discount_line.tax_ids], analytic_account))

            last_operation = discount_line.discount_type
            logger.debug("Final current_calculation")
            logger.debug(current_calculation)
            logger.debug("Result")
            logger.debug(result)
        '''
        Remove the extra subtotal field
        '''
        if aux_discount_line_id:
            discount_line_obj.unlink(cr, uid, aux_discount_line_id, context)
        '''
        Get the final amount
        Final result => Current amount of time and today.
        '''
        final_value = 0
        for account_id in current_calculation:
            final_value += sum(current_calculation[account_id].values())

        if is_rounded:
            final_value = cur_obj.round(cr, uid, currency, final_value)

        return (result, final_value)

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
