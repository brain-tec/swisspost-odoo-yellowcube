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
        'block_duplicated_quotations_from_webshop': fields.boolean('Block duplicated web-shop sale orders from automation'),

        # Doc-out: Sending the invoices to the doc-out.
        'docout_invoice_time_of_day': fields.float('Time of Day', help='Files will be sent to the doc-out not earlier than this hour.'),
        'docout_invoice_monday': fields.boolean('Send on Monday?', help='Are invoices sent to doc-out on Monday?'),
        'docout_invoice_tuesday': fields.boolean('Send on Tuesday?', help='Are invoices sent to doc-out on Tuesday?'),
        'docout_invoice_wednesday': fields.boolean('Send on Wednesday?', help='Are invoices sent to doc-out on Wednesday?'),
        'docout_invoice_thursday': fields.boolean('Send on Thursday?', help='Are invoices sent to doc-out on Thursday?'),
        'docout_invoice_friday': fields.boolean('Send on Friday?', help='Are invoices sent to doc-out on Friday?'),
        'docout_invoice_saturday': fields.boolean('Send on Saturday?', help='Are invoices sent to doc-out on Saturday?'),
        'docout_invoice_sunday': fields.boolean('Send on Sunday?', help='Are invoices sent to doc-out on Sunday?'),
        'docout_invoice_activate_send_to_email': fields.boolean('Activate Send to Doc-out Email?'),
        'docout_invoice_email_template_to_docout_id': fields.many2one('email.template', 'Doc-out Email Template', domain=[('model', '=', 'ir.attachment')],
                                                                      help='The email template for the email which sends the invoice to the doc-out.'),
        'docout_invoice_email_address': fields.char('Doc-out Email Address', help='The email address for the doc-out.'),
        'docout_invoice_activate_send_to_server': fields.boolean('Activate Send to Doc-out Remote Server?'),
        'docout_invoice_connect_transport_id': fields.many2one('connect.transport', 'Doc-out Server Connection',
                                                               help='The connection to the doc-out server.'),
        'docout_invoice_folder': fields.char('Doc-out Remote Folder', help='The folder on the remote server to put to files to.'),
        'docout_invoice_sending_option': fields.selection([('multi_sending', 'Send each file separately'),
                                                           ('single_sending', 'Send the concatenation of all files'),
                                                           ], string='Sending Option', required=True),

        'packaging_enabled': fields.boolean('Must Packaging Be Done?',
                                            help='If chekced, then the sale order automation will do packaging.'),
        'packaging_parcel_limit': fields.integer('Max. Number of Parcels before Bulk Freight',
                                                 help='Maximum number of parcels until the delivery will be considered bulk freight.'),
        'packaging_type_ids': fields.one2many('packaging_type', 'configuration_id', string='Packaging Types',
                                              help='List of packaging types.'),
        'packaging_carrier_bulk_freight_id': fields.many2one('delivery.carrier', 'Default Delivery Carrier for Bulk Freight',
                                                             help='Default delivery carrier to be used in case the delivery '
                                                                  'is not sent as multi-parcel but as bulk freight AND no other '
                                                                  'mapping is implemented on the carrier defined by the sale.order.'),

        # Optional checks when starting the SOA.
        'soa_check_taxes': fields.boolean(
            'Do Check on Taxes at the start of the SOA?'),
        'soa_check_uoms': fields.boolean(
            'Do Check on the Units of Measure at the start of the SOA?'),
        'soa_ignore_ship_excep': fields.boolean(
            'Ignore Shipping Exceptions Automatically on SOA?'),
        'soa_ignore_inv_excep': fields.boolean(
            'Ignore Invoicing Exceptions Automatically on SOA?'),

        # Performance tuning for the SOA.
        'soa_ratio_increase': fields.integer(
            'Enqueue Jobs Ratio Increase',
            help='The maximum number of jobs allowed per execution of '
                 'the scheduler which enqueues the jobs of the SOA, M, is '
                 'increased in as much as '
                 '<Enqueue Jobs Ratio Increase> * M + M. The multiplier '
                 'affects just those steps in the SOA that have '
                 'been found to be the fastest ones, with a workload which is '
                 '(almost) negligible.'
        )
    }

    _defaults = {
        'block_duplicated_quotations_from_webshop': False,
        'docout_invoice_sending_option': 'multi_sending',
        'docout_invoice_activate_send_to_email': False,
        'docout_invoice_activate_send_to_server': False,
        'soa_check_taxes': False,
        'soa_check_uoms': False,
        'soa_ratio_increase': 0,
    }

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
