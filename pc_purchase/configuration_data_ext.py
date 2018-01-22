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
###############################################################################

from openerp.osv import osv, fields
from openerp.tools.translate import _


class configuration_data_ext (osv.Model):

    _inherit = 'configuration.data'

    _columns = {
        'purchase_franking_country_code': fields.char('Country Code', size=2, help='Two-letters country code, to be used in the franking part of the address window.'),
        'purchase_franking_zip': fields.char('ZIP', help='ZIP within the country, to be used in the franking part of the address window.'),
        'purchase_franking_town': fields.char('Town', help='Town within the country, to be used in the franking part of the address window.'),

        # Other fields of the address window.
        'purchase_postmail_rrn': fields.char('RRN', help='RRN, to be used in the franking part of the address window.'),
        'purchase_qr': fields.many2one('ir.header_img', 'QR', help='The QR code which appears within the address window.'),

        # Logo to use in the report.
        'purchase_logo': fields.many2one('ir.header_img', 'Logo', help='The logo which appears at the top of the report.'),

        # Field of the ending message.
        'purchase_ending_text': fields.text('Ending Text', translate=True, help='Text which is placed at the end of the purchase.'),

        # Number of elements per page.
        'purchase_report_num_lines_per_page_first': fields.integer('Num. Elements per Page (first)', required=True,
                                                              help='Number of lines to display on the first page.', default=10),
        'purchase_report_num_lines_per_page_not_first': fields.integer('Num. Elements per Page (not first)', required=True, default=35,
                                                                  help='Number of lines to display per page in the report for pages different than the first one.'),

        # Custom fields that override the information from the company.
        'purchase_company_address_id': fields.many2one('res.partner', 'Company Address to use (overrides PO company)',
                                                       help='Leave it empty to use the one defined in the company. For the moment it only uses the phone and the email.',
                                                       required=False),

        'purchase_report_print_delivery_address': fields.boolean('Print Delivery Address?', help='Taken from the Destination Warehouse of the purchase order.'),
    }

    _defaults = {
        'purchase_report_num_lines_per_page_first': 15,
        'purchase_report_num_lines_per_page_not_first': 20,
    }

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
