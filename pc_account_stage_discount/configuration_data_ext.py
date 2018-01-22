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
from osv import osv, fields
from openerp.tools.translate import _


class configuration_data_ext(osv.Model):
    _inherit = 'configuration.data'

    _columns = {
        # Overridden to add the option 'amount'.
        'invoice_report_discount_column_type': fields.selection([('percentage', 'Percentage'),
                                                                 ('amount', 'Amount'),
                                                                 ('hide', 'Hide'),
                                                                 ], string="Type of the 'Discount Column'", required=True,
                                                                help="The content of the column on the report which shows the discount done "
                                                                     "on each line: 'Percentage' shows the percentage applied to the line, while "
                                                                     "'Amount' shows the amount discounted to the line."),
        'invoice_report_discounted_total_amount_active': fields.boolean("Show 'Total Amount' line?"),
        'invoice_report_discounted_total_amount_text': fields.char("Text for the 'Total Amount' line", translate=True),
    }

    _defaults = {
        'invoice_report_discount_column_type': 'percentage',
        'invoice_report_discounted_total_amount_active': False,
        'invoice_report_discounted_total_amount_text': 'Total amount saved',
    }

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
