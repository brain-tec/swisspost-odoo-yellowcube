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
        'stock_picking_include_backorder_items': fields.boolean('Include back order items'),
        'stock_picking_backorder_line_text': fields.text('Back order line text', translate=True),

        # Fields related with the franking of the stock picking's report.
        'stock_picking_franking_country_code': fields.char('Country Code', size=2, help='Two-letters country code, to be used in the franking part of the address window.'),
        'stock_picking_franking_zip': fields.char('ZIP', help='ZIP within the country, to be used in the franking part of the address window.'),
        'stock_picking_franking_town': fields.char('Town', help='Town within the country, to be used in the franking part of the address window.'),

        # Logo to use in the report.
        'stock_picking_logo': fields.many2one('ir.header_img', 'Logo', help='The logo which appears at the top of the report.'),

        # Other fields of the address window.
        'stock_picking_postmail_rrn': fields.char('RRN', help='RRN, to be used in the franking part of the address window.'),
        'stock_picking_qr': fields.many2one('ir.header_img', 'QR', help='The QR code which appears within the address window.'),

        # Field of the ending message.
        'stock_picking_ending_text': fields.text('Ending Text', translate=True, help='Text which is placed at the end of the delivery slip.'),

        # Number of elements per page.
        'stock_picking_report_num_lines_per_page_first': fields.integer('Num. Elements per Page (first)', required=True,
                                                                        help='Number of lines to display on the first page.'),
        'stock_picking_report_num_lines_per_page_not_first': fields.integer('Num. Elements per Page (not first)', required=True,
                                                                            help='Number of lines to display per page in the report for pages different than the first one.'),

        'stock_picking_report_text_for_partial_deliveries': fields.text('Additional Text for Partial Deliveries', translate=True,
                                                                        help='In the case of the picking being part of a partial delivery '
                                                                             'this text will be printed at the end of all the pickings but '
                                                                             'the last one.'),

        'stock_picking_report_show_lots': fields.boolean('Print Lots?'),
        'stock_picking_report_print_invoice_address': fields.boolean('Print Invoice Address?'),

        # Optional info: name of delivery method and customer phone.
        'stock_picking_report_delivery_method_size': fields.integer('Delivery Method (Font Size)',
                                                                    help='The size has to be indicated in pt.'),
        'stock_picking_report_delivery_method_weight': fields.selection([('normal', 'Normal'),
                                                                         ('bold', 'Bold'),
                                                                         ], string='Delivery Method (Font Weight)'),
        'stock_picking_report_customer_phone_size': fields.integer('Customer Phone (Font Size)',
                                                                   help='The size has to be indicated in pt.'),
        'stock_picking_report_customer_phone_weight': fields.selection([('normal', 'Normal'),
                                                                        ('bold', 'Bold'),
                                                                        ], string='Customer Phone (Font Weight)'),
        'stock_picking_report_delivery_optional_info_width_left': fields.integer('Delivery Method & Customer Phone (width of left side)',
                                                                                 help='Width (in millimetres) of the left hand side of the content.'),
    }

    _defaults = {
        'stock_picking_report_num_lines_per_page_first': 10,
        'stock_picking_report_num_lines_per_page_not_first': 15,
        'stock_picking_report_text_for_partial_deliveries': _('The remaining items will be delivered at no additional cost.'),
        'stock_picking_report_show_lots': True,
        'stock_picking_report_print_invoice_address': True,

        'stock_picking_report_delivery_method_size': 12,
        'stock_picking_report_delivery_method_weight': 'bold',
        'stock_picking_report_customer_phone_size': 12,
        'stock_picking_report_customer_phone_weight': 'bold',
        'stock_picking_report_delivery_optional_info_width_left': 65,
    }

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
