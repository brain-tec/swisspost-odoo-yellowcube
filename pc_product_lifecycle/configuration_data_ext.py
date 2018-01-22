# b-*- encoding: utf-8 -*-
##############################################################################
#
#    Copyright (c) 2015 brain-tec AG (http://www.braintec-group.com)
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
from openerp.tools.translate import _


_DATE_SELECTION = [('days', 'Day(s)'),
                   ('hours', 'Hour(s)'),
                   ]


class configuration_data_ext(osv.Model):
    _inherit = 'configuration.data'

    _columns = {
        'clocking_product_lifecycle_from_endoflife_to_deactivated': fields.integer("Time to wait from 'End of Life' to 'Deactivated'", "Time to wait from 'End of Life' to 'Deactivated'."),
        'clocking_product_lifecycle_from_endoflife_to_deactivated_uom': fields.selection(_DATE_SELECTION, string="UOM to wait from 'End of Life' to 'Deactivated'", help="UOM to wait from 'End of Life' to 'Deactivated'."),

        'product_lifecycle_force_products_to_have_price': fields.boolean('Is Price Mandatory?',
                                                                         help='Are products required to have a price which is greater than zero?'),
        'product_lifecycle_force_products_to_have_weight': fields.boolean('Is Weight Mandatory?',
                                                                          help='Are products required to have a weight and net weight set?'),
        'plc_allow_free_change_of_webshop_state': fields.boolean(
            'Accept any WebShop State Always?',
            help='If checked, the user can freely change the WebShop state. '
                 'However note that some states in the workflow can still '
                 'change the value set by the user on this field.'),
        'product_lifecycle_name_min_length': fields.integer("Minimum Length for Product's Name"),
        'product_lifecycle_name_max_length': fields.integer("Maximum Length for Product's Name"),
        'product_lifecycle_default_code_min_length': fields.integer("Minimum Length for Product's Default Code"),
        'product_lifecycle_default_code_max_length': fields.integer("Maximum Length for Product's Default Code"),
    }

    _defaults = {
        'clocking_product_lifecycle_from_endoflife_to_deactivated': 0,
        'clocking_product_lifecycle_from_endoflife_to_deactivated_uom': 'days',

        'product_lifecycle_force_products_to_have_price': True,
        'product_lifecycle_force_products_to_have_weight': True,
        'plc_allow_free_change_of_webshop_state': False,
        'product_lifecycle_name_min_length': 1,
        'product_lifecycle_name_max_length': 128,
        'product_lifecycle_default_code_min_length': 1,
        'product_lifecycle_default_code_max_length': 35,
    }

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
