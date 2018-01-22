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


class configuration_data_ext(osv.Model):
    _inherit = 'configuration.data'

    _columns = {
        # Fields related with the franking of the follow-up's report.
        'followup_franking_country_code': fields.char('Country Code', size=2, help='Two-letters country code, to be used in the franking part of the address window.'),
        'followup_franking_zip': fields.char('ZIP', help='ZIP within the country, to be used in the franking part of the address window.'),
        'followup_franking_town': fields.char('Town', help='Town within the country, to be used in the franking part of the address window.'),

        # Other fields of the address window.
        'followup_postmail_rrn': fields.char('RRN', help='RRN, to be used in the franking part of the address window.'),
        'followup_qr': fields.many2one('ir.header_img', 'QR', help='The QR code which appears within the address window.'),

        # Logo to use in the report.
        'followup_logo': fields.many2one('ir.header_img', 'Logo', help='The logo which appears at the top of the report.'),

        # Doc-out: Sending the follow-ups to the doc-out.
        'docout_followup_time_of_day': fields.float('Time of Day', help='Files will be sent to the doc-out not earlier than this hour.'),
        'docout_followup_monday': fields.boolean('Send on Monday?', help='Are follow-ups sent to doc-out on Monday?'),
        'docout_followup_tuesday': fields.boolean('Send on Tuesday?', help='Are follow-ups sent to doc-out on Tuesday?'),
        'docout_followup_wednesday': fields.boolean('Send on Wednesday?', help='Are follow-ups sent to doc-out on Wednesday?'),
        'docout_followup_thursday': fields.boolean('Send on Thursday?', help='Are follow-ups sent to doc-out on Thursday?'),
        'docout_followup_friday': fields.boolean('Send on Friday?', help='Are follow-ups sent to doc-out on Friday?'),
        'docout_followup_saturday': fields.boolean('Send on Saturday?', help='Are follow-ups sent to doc-out on Saturday?'),
        'docout_followup_sunday': fields.boolean('Send on Sunday?', help='Are follow-ups sent to doc-out on Sunday?'),
        'docout_followup_activate_send_to_email': fields.boolean('Activate Send to Doc-out Email?'),
        'docout_followup_email_template_to_docout_id': fields.many2one('email.template', 'Doc-out Email Template', domain=[('model', '=', 'ir.attachment')],
                                                                       help='The email template for the email which sends the follow-up to the doc-out.'),
        'docout_followup_email_address': fields.char('Doc-out Email Address', help='The email address for the doc-out.'),
        'docout_followup_activate_send_to_server': fields.boolean('Activate Send to Doc-out Remote Server?'),
        'docout_followup_connect_transport_id': fields.many2one('connect.transport', 'Doc-out Server Connection',
                                                                help='The connection to the doc-out server.'),
        'docout_followup_folder': fields.char('Doc-out Remote Folder', help='The folder on the remote server to put to files to.'),
        'docout_followup_sending_option': fields.selection([('multi_sending', 'Send each file separately'),
                                                            ('single_sending', 'Send the concatenation of all files'),
                                                            ], string='Sending Option', required=True),
    }

    _defaults = {
        'docout_followup_sending_option': 'multi_sending',
        'docout_followup_activate_send_to_email': False,
        'docout_followup_activate_send_to_server': False,
    }

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
