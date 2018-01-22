# b-*- encoding: utf-8 -*-
##############################################################################
#
#    Copyright (c) 2017 brain-tec AG (http://www.braintec-group.com)
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


class configuration_data_ext(osv.Model):
    _inherit = 'configuration.data'

    _columns = {
        # Fields related with the franking of the invoice's report.
        'invoice_pf_franking_country_code': fields.char(
            'Country Code', size=2,
            help='Two-letters country code, to be used in the franking '
                 'part of the address window.'),
        'invoice_pf_franking_zip': fields.char(
            'ZIP',
            help='ZIP within the country, to be used in the franking '
                 'part of the address window.'),
        'invoice_pf_franking_town': fields.char(
            'Town',
            help='Town within the country, to be used in the franking '
                 'part of the address window.'),

        # Other fields of the address window.
        'invoice_pf_postmail_rrn': fields.char(
            'RRN',
            help='RRN, to be used in the franking part of '
                 'the address window.'),
        'invoice_pf_qr': fields.many2one(
            'ir.header_img', 'QR',
            help='The QR code which appears within the address window.'),

        # Logo to use in the report.
        'invoice_pf_logo': fields.many2one(
            'ir.header_img', 'Logo',
            help='The logo which appears at the top of the report.'),

        # Field of the ending message.
        'invoice_pf_ending_text': fields.text(
            'Ending Text (ePayment set)', translate=True,
            help='Text which is placed at the end of the invoice '
                 'if ePayment was set.'),

        # Number of elements per page.
        'invoice_pf_report_num_lines_per_page_first': fields.integer(
            'Num. Elements per Page (first)', required=True,
            help='Number of lines to display on the first page.'),
        'invoice_pf_report_num_lines_per_page_not_first': fields.integer(
            'Num. Elements per Page (not first)', required=True,
            help='Number of lines to display per page in the report '
                 'for pages different than the first one.'),

        # Fields related to discounts.
        'invoice_pf_report_discount_column_text': fields.char(
            "Text for the 'Discount Column'", required=True, translate=True),
        'invoice_pf_report_discount_column_type': fields.selection(
            [('percentage', 'Percentage'),
             ('hide', 'Hide'),
             ], string="Type of the 'Discount Column'", required=True,
            help="The content of the column on the report which shows "
                 "the discount done on each line: 'Percentage' shows the "
                 "percentage applied to the line."),

        # Field to set the maximum width for the logo.
        'invoice_pf_logo_max_width': fields.float(
            'Logo: Maximum width',
            help='Maximum width of the logo of the company for the report, '
                 'set in millimetres.'),
        'invoice_pf_logo_top': fields.float(
            'Logo: Distance from the top of page to the top of the logo',
            help='Distance from the bottom of the page to the top '
                 'of the logo, set in millimetres.'),
    }

    _defaults = {
        'invoice_pf_report_discount_column_type': 'percentage',
        'invoice_pf_report_discount_column_text': 'Discount',
        'invoice_pf_report_num_lines_per_page_first': 9,
        'invoice_pf_report_num_lines_per_page_not_first': 20,

        'invoice_pf_logo_max_width': 70.0,
        'invoice_pf_logo_top': 4.7,
    }

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
