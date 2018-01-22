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

from osv import osv, fields
from openerp.tools.translate import _


class configuration_data_ext(osv.Model):
    _inherit = 'configuration.data'

    _columns = {
        'barcode_report_logo': fields.many2one('ir.header_img', 'Logo Image', help='The logo of the company which appears in the report.'),
        'barcode_report_logo_top': fields.integer('Logo Position (top)',
                                                  help='Position for the logo of the report, measured in millimetres from the top of the page.'),
        'barcode_report_logo_left': fields.integer('Logo Position (left)',
                                                   help='Position for the logo of the report, measured in millimetres from the left of the page.'),
        'barcode_report_logo_width': fields.integer('Logo Width',
                                                    help='Maximum width for the logo of the report, measured in millimetres.'),

        'barcode_report_barcode_top': fields.integer('Barcode Position (top)',
                                                     help='Position for the barcode of the report, measured in millimetres from the top of the page.'),
        'barcode_report_barcode_left': fields.integer('Barcode Position (left)',
                                                      help='Position for the barcode of the report, measured in millimetres from the left of the page.'),

        'barcode_report_partner_id': fields.many2one('res.partner', 'Sending Partner',
                                                     help='Partner who makes the sending (optional)'),
        'barcode_report_partner_top': fields.integer('Sending Partner Position (top)',
                                                     help='Position for the area of the report dedicated to the sending partner, '
                                                          'measured in millimetres from the top of the page.'),
        'barcode_report_partner_left': fields.integer('Sending Partner Position (left)',
                                                      help='Position for the area of the report dedicated to the sending partner, '
                                                           'measured in millimetres from the left of the page.'),
        'barcode_report_partner_width': fields.integer('Sending Partner Position (width)',
                                                       help='The width for the area of the report dedicated to the sending partner, measured in millimetres.'),
        'barcode_report_partner_font_size': fields.integer('Sending Partner Position (font size)',
                                                           help='Font size (in pt) for the text of the area of the report dedicated to the sending partner.'),

        'barcode_report_information_top_with_partner': fields.integer('Information Position (top, with sending partner set)',
                                                                      help='Position for the information area of the report, measured in millimetres from the top of the page, '
                                                                           'when a sending partner has been selected.'),
        'barcode_report_information_top': fields.integer('Information Position (top, without sending partner set)',
                                                         help='Position for the information area of the report, measured in millimetres from the top of the page, '
                                                              'when no sending partner has been selected.'),
        'barcode_report_information_left': fields.integer('Information Position (left)',
                                                          help='Position for the information area of the report, measured in millimetres from the left of the page.'),
        'barcode_report_information_width': fields.integer('Information Position (width)',
                                                           help='The width of the information box, in millimetres.'),
        'barcode_report_information_font_size': fields.integer('Information Position (font size)',
                                                               help='Font size (in pt) for the text of the area of the report dedicated to the information box.'),

        'barcode_report_package_top': fields.integer('Package Iterator (top)',
                                                     help='Position for the iterator over the packages, measure in millimetres from the top of the page.'),
        'barcode_report_package_left': fields.integer('Package Iterator (left)',
                                                      help='Position for the iterator over the packages, measure in millimetres from the left of the page.'),
        'barcode_report_package_font_size': fields.integer('Package Iterator (font size)',
                                                           help='Font size (in pt) for the iterator over the packages.'),
        'barcode_report_package_font_weight': fields.selection([('normal', 'Normal'),
                                                                ('bold', 'Bold'),
                                                                ], string='Package Iterator (font weight)')
    }

    _defaults = {
        'barcode_report_logo_top': 15,
        'barcode_report_logo_left': 145,
        'barcode_report_barcode_top': 15,
        'barcode_report_barcode_left': 20,
        'barcode_report_partner_top': 50,
        'barcode_report_partner_left': 145,
        'barcode_report_partner_width': 60,
        'barcode_report_partner_font_size': 8,
        'barcode_report_information_top_with_partner': 80,
        'barcode_report_information_top': 50,
        'barcode_report_information_left': 145,
        'barcode_report_information_width': 60,
        'barcode_report_information_font_size': 8,
        'barcode_report_package_top': 90,
        'barcode_report_package_left': 100,
        'barcode_report_package_font_size': 11,
        'barcode_report_package_font_weight': 'bold',
    }

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
