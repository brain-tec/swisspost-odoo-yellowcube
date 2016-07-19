# b-*- encoding: utf-8 -*-
##############################################################################
#
#    Copyright (c) 2015 brain-tec AG (http://www.brain-tec.ch)
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

from openerp.osv import osv, fields
import decimal
from openerp.osv.orm import except_orm
import openerp.addons.decimal_precision as dp


class product_template_ext(osv.Model):
    _inherit = 'product.template'

    def _compute_packing(self, cr, uid, ids, field_name, arg, context=None):
        ''' Computes the 'packing' for a product.
            The packing is the multiplication of product's lenght X width X height X weight.
        '''
        if context is None:
            context = {}
        res = {}
        for product in self.browse(cr, uid, ids, context=context):
            res[product.id] = product.length * product.width * product.height * product.weight
        return res

    def onchange_check_decimals(self, cr, uid, ids, value, decimal_accuracy_class, context=None):
        ''' Checks that a given magnitude has its correct number of decimals.
        '''
        if context is None:
            context = {}

        # Gets the number of decimals for this class.
        num_digits, num_digits_fraction = dp.get_precision(decimal_accuracy_class)(cr)

        # Gets the actual number of digits and decimals.
        if value:
            d = decimal.Decimal(str(value))
            d_tuple = d.as_tuple()
            num_digits_actual = len(d_tuple.digits)
            num_digits_fraction_actual = abs(d_tuple.exponent)

            # Checks.
            if (num_digits_actual > num_digits) or (num_digits_fraction_actual > num_digits_fraction):
                return {'warning': {'title': _('Bad number of digits'),
                                    'message': _('The field should have {0} digits, {1} of them being the fractional part.').format(num_digits, num_digits_fraction)}
                        }

        return {'value': {'value': value}}

    _columns = {
        # Attributes related to the features a product can have.
        'weight': fields.float("Weight", digits_compute=dp.get_precision('Stock Weight')),
        'length': fields.float('Length', digits_compute=dp.get_precision('Stock Length'), help='Length of the product (in centimeters)'),
        'width': fields.float('Width', digits_compute=dp.get_precision('Stock Width'), help='Width of the product (in centimeters)'),
        'height': fields.float('Height', digits_compute=dp.get_precision('Stock Height'), help='Height of the product (in centimeters)'),
        'diameter': fields.float('Diameter', digits_compute=dp.get_precision('Stock Diameter'), help='Diameter of the product (in centimeters)'),
        'packing': fields.function(_compute_packing, string='Packing', readonly=True, digits_compute=dp.get_precision('Stock Packing'),
                                   store={'product.template': (lambda self, cr, uid, ids, context: ids,
                                                               ['length', 'width', 'height', 'weight'], 10)},
                                   help='Length x Width x Height x Weight (gross, not net)'),
        'brand': fields.char('Brand', help='The brand of the product'),
        'manufacturer_website': fields.char('Manufacturer\'s Website', help='Link to the manufacturer\'s web site.'),

    }

    _defaults = {
        'weight': 0.00,
        'type': 'product',
    }

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
