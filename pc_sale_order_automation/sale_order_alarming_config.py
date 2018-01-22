# b-*- encoding: utf-8 -*-
##############################################################################
#
#    Copyright (c) 2016 brain-tec AG (http://www.braintec-group.com)
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
from openerp.addons.pc_connect_master.product_uom_ext import UOM_AGING_SELECTION_VALUES


class sale_order_alarming_config(osv.Model):
    _inherit = "configuration.data"

    _columns = {
        'sale_order_min_age_in_draft_value': fields.integer('Minimum Age',
                                                            help='Minimum allowed age of a Sale Order to stay in draft state.', required=True),
        'sale_order_min_age_in_draft_uom': fields.selection(UOM_AGING_SELECTION_VALUES, string='Age UOM',
                                                            help='Unit of Measure for the ignore age of a Sale Order.', required=True),

        'sale_order_max_age_in_draft_value': fields.integer('Sale Order Draft Alarming Age',
                                                            help='Maximum allowed age of a Sale Order to stay in draft state.', required=False),
        'sale_order_max_age_in_draft_uom': fields.selection(UOM_AGING_SELECTION_VALUES, string='Age UOM',
                                                            help='Unit of Measure for the ignore age of a Sale Order.', required=True),
    }

    _defaults = {
        'sale_order_min_age_in_draft_uom': UOM_AGING_SELECTION_VALUES[0][0],
        'sale_order_max_age_in_draft_uom': UOM_AGING_SELECTION_VALUES[0][0]
    }

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
