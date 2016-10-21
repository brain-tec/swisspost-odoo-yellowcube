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
from configuration_data_ext import _DATE_SELECTION
from dateutil import relativedelta
from openerp.tools.translate import _


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

    # The following functions tie the dates of the 'Inventory' tab to the company's system's parameters.
    # Values on the product have precedence over those defined by default.
    def _onchange_times(self, cr, uid, ids, time_field_value, field_odoo, field_uom_odoo, kind, context=None):
        IS_UOM = True
        if not time_field_value:
            # Loads the default time value, and the default unit of measure for that value.
            default_value = self.get_expiration_time_value(cr, uid, kind, not IS_UOM, context)
            default_uom_id = self.get_expiration_time_value(cr, uid, kind, IS_UOM, context)

            # Finds the value stored in the selection corresponding to the value displayed in the selection.
            uom_value_selection = self._expiration_uom_get_selection(cr, uid, default_uom_id, context)

            return {'value': {field_odoo: float(default_value), field_uom_odoo: uom_value_selection}}
        else:
            return {'value': {field_odoo: float(time_field_value)}}

    def onchange_expiration_block_time(self, cr, uid, ids, expiration_block_time, context=None):
        return self._onchange_times(cr, uid, ids, expiration_block_time, 'expiration_block_time', 'expiration_block_time_uom', 'block', context)

    def onchange_expiration_alert_time(self, cr, uid, ids, expiration_alert_time, context=None):
        return self._onchange_times(cr, uid, ids, expiration_alert_time, 'expiration_alert_time', 'expiration_alert_time_uom', 'alert', context)

    def onchange_expiration_accept_time(self, cr, uid, ids, expiration_accept_time, context=None):
        return self._onchange_times(cr, uid, ids, expiration_accept_time, 'expiration_accept_time', 'expiration_accept_time_uom', 'accept', context)

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

    def _expiration_uom(self, cr, uid, tuples=True, uom='days', value=0, context=None):
        ret = []
        for f in _DATE_SELECTION:
            if tuples:
                ret.append(f)
            elif f[0] == uom:
                args = {uom: value * -1}
                return relativedelta.relativedelta(**args)
        return ret

    def get_expiration_time_value(self, cr, uid, kind, is_uom=False, context=None):
        if is_uom:
            key = 'post_default_expiration_{0}_time_uom'.format(kind)
        else:
            key = 'post_default_expiration_{0}_time'.format(kind)

        value = self.pool.get('configuration.data').get(cr, uid, [], context=context)[key]
        if not is_uom:
            # If not is_uom then we don't query the UOM but the value associated to it...
            return value
        else:
            # If it's a UOM then we get the value to be stored in the selection field.
            uom_value_selection = self._expiration_uom_get_selection(cr, uid, value, context)  # Returns None if not found.
            return uom_value_selection

    def _expiration_uom_get_selection(self, cr, uid, value_to_search, context):
        ''' Given a value displayed in a selection field, it returns the value stored in the selection, or None if it was not found.
        '''
        uom_allowed_values = self.pool['product.template'].\
            _expiration_uom(cr, uid, context=context)
        uom_value_selection = None
        for uom_allowed_value in uom_allowed_values:
            uom_value_displayed = uom_allowed_value[1]
            if uom_value_displayed == value_to_search:
                uom_value_selection = uom_allowed_value[0]
                break
        return uom_value_selection

    _columns = {
        # Expiration dates for the warehouse process.
        'expiration_block_time': fields.float('Expiration Block Time', required=True),
        'expiration_block_time_uom': fields.selection(_expiration_uom,
                                                      string='Unit of Measure for the Expiration Block Time',
                                                      required=False),
        'expiration_alert_time': fields.float('Expiration Alert Time', required=True),
        'expiration_alert_time_uom': fields.selection(_expiration_uom,
                                                      string='Unit of Measure for the Expiration Alert Time', required=False),
        'expiration_accept_time': fields.float('Expiration Accept Time', required=True),
        'expiration_accept_time_uom': fields.selection(_expiration_uom,
                                                       string='Unit of Measure for the Expiration Accept Time', required=False),
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
        'expiration_block_time': lambda self, cr, uid,
                                        context: self.get_expiration_time_value(cr,
                                                                                uid,
                                                                                'block',
                                                                                context=context),
        'expiration_block_time_uom': lambda self, cr, uid,
                                            context: self.get_expiration_time_value(
            cr, uid, 'block', True, context),
        'expiration_alert_time': lambda self, cr, uid,
                                        context: self.get_expiration_time_value(cr,
                                                                                uid,
                                                                                'alert',
                                                                                context=context),
        'expiration_alert_time_uom': lambda self, cr, uid,
                                            context: self.get_expiration_time_value(
            cr, uid, 'alert', True, context),
        'expiration_accept_time': lambda self, cr, uid,
                                         context: self.get_expiration_time_value(cr,
                                                                                 uid,
                                                                                 'accept',
                                                                                 context=context),
        'expiration_accept_time_uom': lambda self, cr, uid,
                                             context: self.get_expiration_time_value(
            cr, uid, 'accept', True, context),
    }

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
