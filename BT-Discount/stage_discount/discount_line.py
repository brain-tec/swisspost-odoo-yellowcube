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
from openerp.tools.translate import _

PRODUCT_PRODUCTID_SEPARATOR = '$$$$$'

_DISCOUNT_TYPE = [('fixed', 'Fixed Amount'),
                  ('percentage', 'Percent'),
                  ('subtotal', 'Subtotal'),
                  ('product', 'Product'),
                  ]


class discount_line(osv.osv):
    _name = "stage_discount.discount_line"
    _description = "Discount Line"
    _columns = {
        'discount_type': fields.selection(_DISCOUNT_TYPE, 'Computation',
                                          required=True, help="""Select here the kind of valuation related to this discount line. """),

        'discount_value': fields.float('Amount To Discount', digits_compute=dp.get_precision('Term'), help="For percent enter a ratio between 0-100."),
        'discount_id': fields.many2one('stage_discount.discount', 'Discount', ondelete='cascade'),
        'sequence': fields.integer('Sequence'),
        'description': fields.text('Description', translate=True),
        'description_template': fields.text('Description', translate=True, help="This field contains the description in different languages."),
        'tax_ids': fields.many2many('account.tax', 'discount_term_line_tax',
                                                   'discount_term_line_id',
                                                   'tax_id',
                                                   'Taxes',
                                                   domain=[('parent_id', '=', False)]),
        'account_analytic_id': fields.many2one('account.analytic.account', 'Analytic Account'),
        'account_id': fields.many2one('account.account', 'Financial Account'),
        'is_rounded': fields.boolean('Round (this line)', help="To round the amount calculated with this discount."),
        'invoice_id': fields.many2one('account.invoice', 'Invoice', ondelete='cascade'),
        'order_id': fields.many2one('sale.order', 'Sale order', ondelete='cascade'),
        'product_id': fields.many2one('product.product', 'Product', help='The sale price of this product will be used as the discount.'),
    }

    _defaults = {
        'discount_type': 'percentage',
        'sequence': lambda self, cr, uid, context={}: self.pool.get('ir.sequence').get(cr, uid, 'stage.discount'),
        'description': 'Description...',
        'is_rounded': True,
    }

    _order = "sequence"

    def _check_percent(self, cr, uid, ids, context=None):
        obj = self.browse(cr, uid, ids[0], context=context)
        if obj.discount_type == 'percentage' and (obj.discount_value < -100.0 or obj.discount_value > 100.0):
            return False
        return True

    def _set_data_from_product(self, cr, uid, ids):
        ''' - This is a method to be used in a constraint, but it does not checks, but sets.
            - Every time the field product_id is changed, we set the account_id to be that of the product,
              and we set the discount_value to be the list_price of the product,
              and we set the description to be that of the product,
              and we set the tax to be that of the product.
            - We implement this as a constraint to assure that it's executed always, since using an on_change
              only has effect if the user uses the user interface, not if he accesses the system remotely (e.g.
              from a web-service).
        '''
        if type(ids) is not list:
            ids = [ids]

        # Gets the language of the current res.user.
        res_user_obj = self.pool.get('res.users')
        current_res_user_id = res_user_obj.search(cr, uid, [('id', '=', uid)])[0]
        current_res_user = res_user_obj.browse(cr, uid, current_res_user_id)

        obj = self.browse(cr, uid, ids[0], {'lang': current_res_user.lang})
        if obj.discount_type == 'product':
            product_account_id = obj.product_id.property_account_income.id
            if (obj.account_id.id != product_account_id) \
               or (-obj.discount_value != obj.product_id.list_price) \
               or (obj.description != obj.product_id.name) \
               or (obj.tax_ids != obj.product_id.taxes_id):
                self.write(cr, uid, ids[0], {'account_id': product_account_id,
                                             'discount_value': -obj.product_id.list_price,
                                             'description': obj.product_id.name,
                                             'tax_ids': [(6, 0, [x.id for x in obj.product_id.taxes_id])],
                                             })

        return True

    def onchange_product_id(self, cr, uid, ids, product_id, context=None):
        ''' - If discount_type is 'product', then we set the account_id to be that of the product.
            - If discount_type is 'product', then we set the discount_value to be the price of the product.
            - If discount_type is 'product', then we set the description to be that of the product.
            - If discount_type is 'product', then we set the taxes to be that of the product.
            - This only assures the change when the user uses the user interface. To assure the change
              when we access through a remote way (e.g. a web-service) a constraint has been done.
        '''
        if context is None:
            context = {}

        # Gets the language of the current res.user.
        res_user_obj = self.pool.get('res.users')
        current_res_user_id = res_user_obj.search(cr, uid, [('id', '=', uid)], context=context)[0]
        current_res_user = res_user_obj.browse(cr, uid, current_res_user_id, context=context)
        context.update({'lang': current_res_user.lang})

        product = self.pool.get('product.product').browse(cr, uid, product_id, context=context)
        product_account_id = product.property_account_income.id
        return {'value': {'account_id': product_account_id,
                          'discount_value': -product.list_price,
                          'description': product.name,
                          'tax_ids': [(6, 0, [x.id for x in product.taxes_id])],
                          }}

    def get_description(self, cr, uid, ids, context=None):
        ''' If the type of discount is 'product', then we store its ID just after its description,
            using a $$$$$ delimiter. That magic-string is stored in the variable
            PRODUCT_PRODUCTID_SEPARATOR.
                This is ugly, but it's the way of passing information that this module uses.
        '''
        obj = self.browse(cr, uid, ids[0], context=context)
        description = ''
        if obj.discount_type == 'product':
            description = "{0}{1}{2}#{3}#{4}".format(obj.description,
                                                     PRODUCT_PRODUCTID_SEPARATOR,
                                                     obj.product_id.id,
                                                     obj.discount_type,
                                                     obj.discount_value)
        else:
            description = "{0}#{1}#{2}".format(obj.description, obj.discount_type, obj.discount_value)
        return description

    _constraints = [
        (_check_percent, 'Percentages for Discount Term Line must be between -100 and 100, Example: 2.5 for 2.5%.', ['value_amount']),
        (_set_data_from_product, 'Sets some data from the product.', ['product_id']),
    ]

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
