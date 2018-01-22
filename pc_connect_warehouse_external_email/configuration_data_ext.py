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

from osv import osv, orm, fields
from openerp.tools.translate import _


class configuration_data_ext(osv.Model):
    _inherit = 'configuration.data'

    def write(self, cr, uid, ids, values, context=None):
        ''' This makes sure that every time we set a new number of times a day
            to execute the punchcard, the values which are not used are cleared out.
        '''
        if context is None:
            context = {}
        if type(ids) is not list:
            ids = [ids]

        def get_time_of_day(str_time_of_day):
            key = 'email_connector_time_of_day_{0}'.format(str_time_of_day)
            if key == 'email_connector_time_of_day_1':
                key = 'email_connector_time_of_day'  # Special case for backwards compatibility.
            return values.get(key, False) or self.browse(cr, uid, ids[0], context=context)[key]

        times_a_day = values.get('email_connector_times_a_day', False)
        first_time_of_day = values.get('email_connector_time_of_day', False)
        second_time_of_day = values.get('email_connector_time_of_day_2', False)
        third_time_of_day = values.get('email_connector_time_of_day_3', False)

        if times_a_day or first_time_of_day or second_time_of_day or third_time_of_day:
            error_message = []

            if times_a_day == '1':
                values.update({'email_connector_time_of_day_2': False,
                               'email_connector_time_of_day_3': False})
            elif times_a_day == '2':
                values.update({'email_connector_time_of_day_3': False})
                if get_time_of_day('2') <= get_time_of_day('1'):
                    error_message.append(_('2nd Time of Day must happen after 1st Time of Day.'))

            elif times_a_day == '3':
                if get_time_of_day('2') <= get_time_of_day('1'):
                    error_message.append(_('2nd Time of Day must happen after 1st Time of Day.'))
                if get_time_of_day('3') <= get_time_of_day('2'):
                    error_message.append(_('3rd Time of Day must happen after 2nd Time of Day.'))

            if error_message:
                raise orm.except_orm(_('Error in Times of Day'), '\n'.join(error_message))

        return super(configuration_data_ext, self).write(cr, uid, ids, values, context=context)

    _columns = {
        'email_connector_times_a_day': fields.selection([('1', '1'),
                                                         ('2', '2'),
                                                         ('3', '3'),
                                                         ], 'How Many Times a Day?',
                                                        required=True),
        'email_connector_time_of_day': fields.float('1st Time of Day', help='First sending will be sent not earlier than this hour.'),
        'email_connector_time_of_day_2': fields.float('2nd Time of Day', help='Second sending will be sent not earlier than this hour.'),
        'email_connector_time_of_day_3': fields.float('3rd Time of Day', help='Third sending will be sent not earlier than this hour.'),

        'email_connector_monday': fields.boolean('Send on Mondays?', help='Are e-mails sent on Mondays?'),
        'email_connector_tuesday': fields.boolean('Send on Tuesdays?', help='Are e-mails sent on Tuesdays?'),
        'email_connector_wednesday': fields.boolean('Send on Wednesdays?', help='Are e-mails sent on Wednesdays?'),
        'email_connector_thursday': fields.boolean('Send on Thursdays?', help='Are e-mails sent on Thursdays?'),
        'email_connector_friday': fields.boolean('Send on Fridays?', help='Are e-mails sent on Fridays?'),
        'email_connector_saturday': fields.boolean('Send on Saturdays?', help='Are e-mails sent on Saturdays?'),
        'email_connector_sunday': fields.boolean('Send on Sundays?', help='Are e-mails sent on Sundays?'),

        'email_connector_email_template_id': fields.many2one('email.template', 'Email Template to Use', domain=[('model', '=', 'stock.connect.file')]),
        'email_connector_email_address_primary': fields.char('Primary E-mail Address'),
        'email_connector_email_address_secondary': fields.char('Secondary E-mail Address'),

        'email_connector_report_picking_list': fields.many2one('ir.actions.report.xml', "Picking List",
                                                               domain=[('model', '=', 'stock.picking.out')]),
        'email_connector_report_picking_list_logo': fields.many2one('ir.header_img', 'Logo',
                                                                    help='The logo which appears at the top of the report.'),
        'email_connector_report_picking_list_num_lines': fields.integer('Number of Lines per Page',
                                                                        help='The number of lines per page in the report. '
                                                                             'Take into account that some lines (those of titles) '
                                                                             'are bigger than others.')

    }

    _defaults = {
        'email_connector_times_a_day': '1',
        'email_connector_report_picking_list_num_lines': 30,
    }

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
