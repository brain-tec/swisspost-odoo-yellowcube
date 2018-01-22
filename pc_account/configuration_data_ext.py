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


class configuration_data_ext(osv.Model):
    _inherit = 'configuration.data'

    _columns = {
        # Fields to print the products in backorders on the invoice.
        'invoice_include_backorder_items': fields.boolean('Include back order items'),
        'invoice_backorder_line_text': fields.text('Back order line text', translate=True),

        # Fields related with the franking of the invoice's report.
        'invoice_franking_country_code': fields.char('Country Code', size=2, help='Two-letters country code, to be used in the franking part of the address window.'),
        'invoice_franking_zip': fields.char('ZIP', help='ZIP within the country, to be used in the franking part of the address window.'),
        'invoice_franking_town': fields.char('Town', help='Town within the country, to be used in the franking part of the address window.'),

        # Other fields of the address window.
        'invoice_postmail_rrn': fields.char('RRN', help='RRN, to be used in the franking part of the address window.'),
        'invoice_qr': fields.many2one('ir.header_img', 'QR', help='The QR code which appears within the address window.'),

        # Logo to use in the report.
        'invoice_logo': fields.many2one('ir.header_img', 'Logo', help='The logo which appears at the top of the report.'),

        # Field of the ending message.
        'invoice_ending_text_with_epayment': fields.text('Ending Text (ePayment set)', translate=True, help='Text which is placed at the end of the invoice if ePayment was set.'),
        'invoice_ending_text_without_epayment': fields.text('Ending Text (ePayment not set)', translate=True, help='Text which is placed at the end of the invoice if ePayment was not set.'),
        'invoice_ending_text_for_refunds': fields.text('Ending Text For Refunds', translate=True, help='Text which is placed at the end of the invoice if it is a refund.'),

        # Number of elements per page.
        'invoice_report_num_lines_per_page_first': fields.integer('Num. Elements per Page (first)', required=True,
                                                                  help='Number of lines to display on the first page.'),
        'invoice_report_num_lines_per_page_not_first': fields.integer('Num. Elements per Page (not first)', required=True,
                                                                      help='Number of lines to display per page in the report for pages different than the first one.'),

        # Fields related to discounts.
        'invoice_report_discount_column_text': fields.char("Text for the 'Discount Column'", required=True, translate=True),

        'invoice_report_discount_column_type': fields.selection([('percentage', 'Percentage'),
                                                                 ('hide', 'Hide'),
                                                                 ], string="Type of the 'Discount Column'", required=True,
                                                                help="The content of the column on the report which shows the discount done "
                                                                     "on each line: 'Percentage' shows the percentage applied to the line."),

        'invoice_report_text_for_partial_deliveries': fields.text('Additional Text for Partial Deliveries', translate=True,
                                                                  help='In the case of the picking being part of a partial delivery '
                                                                       'this text will be printed at the first (and only one) invoice.'),
        'invoice_report_print_delivery_address': fields.boolean('Print Delivery Address?'),
    }

    _defaults = {
        'invoice_report_discount_column_type': 'percentage',
        'invoice_report_discount_column_text': 'Discount',
        'invoice_report_num_lines_per_page_first': 9,
        'invoice_report_num_lines_per_page_not_first': 20,
        'invoice_report_print_delivery_address': True,
    }

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
