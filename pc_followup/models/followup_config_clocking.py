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


class followup_config_clocking(osv.Model):
    _inherit = "configuration.data"

    _columns = {
        # Variables related with the clocking of the follow-ups.
        'followup_processing_time_of_day': fields.float('Time of Day', help='Time of day to do the follow-up processing.', required=True),
        'followup_processing_monday': fields.boolean('Process on Monday?', help='Are follow-ups processed on Monday?'),
        'followup_processing_tuesday': fields.boolean('Process on Tuesday?', help='Are follow-ups processed on Tuesday?'),
        'followup_processing_wednesday': fields.boolean('Process on Wednesday?', help='Are follow-ups processed on Wednesday?'),
        'followup_processing_thursday': fields.boolean('Process on Thursday?', help='Are follow-ups processed on Thursday?'),
        'followup_processing_friday': fields.boolean('Process on Friday?', help='Are follow-ups processed on Friday?'),
        'followup_processing_saturday': fields.boolean('Process on Saturday?', help='Are follow-ups processed on Saturday?'),
        'followup_processing_sunday': fields.boolean('Process on Sunday?', help='Are follow-ups processed on Sunday?'),

        'followup_handling_time_of_day': fields.float('Time of Day', help='Time of day to do the follow-up processing.', required=True),
        'followup_handling_monday': fields.boolean('Handle on Monday?', help='Are follow-ups handled on Monday?'),
        'followup_handling_tuesday': fields.boolean('Handle on Tuesday?', help='Are follow-ups handled on Tuesday?'),
        'followup_handling_wednesday': fields.boolean('Handle on Wednesday?', help='Are follow-ups handled on Wednesday?'),
        'followup_handling_thursday': fields.boolean('Handle on Thursday?', help='Are follow-ups handled on Thursday?'),
        'followup_handling_friday': fields.boolean('Handle on Friday?', help='Are follow-ups handled on Friday?'),
        'followup_handling_saturday': fields.boolean('Handle on Saturday?', help='Are follow-ups handled on Saturday?'),
        'followup_handling_sunday': fields.boolean('Handle on Sunday?', help='Are follow-ups handled on Sunday?'),

        'followup_print_time_of_day': fields.float('Time of Day', help='Time of day to do the follow-up printing.', required=True),
        'followup_print_monday': fields.boolean('Print on Monday?', help='Are follow-ups printed on Monday?'),
        'followup_print_tuesday': fields.boolean('Print on Tuesday?', help='Are follow-ups printed on Tuesday?'),
        'followup_print_wednesday': fields.boolean('Print on Wednesday?', help='Are follow-ups printed on Wednesday?'),
        'followup_print_thursday': fields.boolean('Print on Thursday?', help='Are follow-ups printed on Thursday?'),
        'followup_print_friday': fields.boolean('Print on Friday?', help='Are follow-ups printed on Friday?'),
        'followup_print_saturday': fields.boolean('Print on Saturday?', help='Are follow-ups printed on Saturday?'),
        'followup_print_sunday': fields.boolean('Print on Sunday?', help='Are follow-ups printed on Sunday?'),

        # Variables related to the service-desk service which receives the summary email with the follow-ups processed.
        'followup_servicedesk_email_template_id': fields.many2one('email.template', 'Email Template', domain=[('model', '=', 'account.invoice')],
                                                                  help='The email template to use when sending the summary email to the follow-up service-desk service.'),
        'followup_servicedesk_email_address': fields.char('Email', help='The email address to use when sending the summary email to the follow-up service-desk service.'),
    }

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
