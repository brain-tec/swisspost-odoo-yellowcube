# b-*- encoding: utf-8 -*-
##############################################################################
#
#    Copyright (c) 2015 brain-tec AG (http://www.brain-tec.ch)
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
from openerp.addons.pc_config.configuration_data import configuration_data


class company_support_config(osv.Model):
    ''' This indicates the working days and hours of the support staff.
    '''
    _inherit = "configuration.data"

    def get_open_days_support(self, cr, uid, ids, context=None):
        ''' Returns a dictionary which can be used to easily check if the support is opened a given day of week.
            For example, d[4] == True checks if the support is opened on Friday.
        '''
        days_open = {}
        config = self.pool.get('configuration.data').get(cr, uid, ids, context)
        for k in ((0, 'monday'), (1, 'tuesday'), (2, 'wednesday'), (3, 'thursday'), (4, 'friday'), (5, 'saturday'), (6, 'sunday')):
            day_num, day_name = k[0], k[1]
            days_open[day_num] = config['support_open_{0}'.format(day_name)]
        return days_open

    _columns = {
        'support_timezone': fields.selection(configuration_data.get_available_timezones, string='Timezone', help='Timezone of the support.', required=True),
        'support_start_time': fields.float('Opening Time', help='Opening time of the support.', required=True),
        'support_soft_end_time': fields.float('Soft Closing Time', help='Soft closing time of the support', required=True),
        'support_end_time': fields.float('Hard Closing Time', help='Hard closing time of the support.', required=True),

        'support_open_monday': fields.boolean('Opens on Monday?', help='Does the support open on Monday?'),
        'support_open_tuesday': fields.boolean('Opens on Tuesday?', help='Does the support open on Tuesday?'),
        'support_open_wednesday': fields.boolean('Opens on Wednesday?', help='Does the support open on Wednesday?'),
        'support_open_thursday': fields.boolean('Opens on Thursday?', help='Does the support open on Thursday?'),
        'support_open_friday': fields.boolean('Opens on Friday?', help='Does the support open on Friday?'),
        'support_open_saturday': fields.boolean('Opens on Saturday?', help='Does the support open on Saturday?'),
        'support_open_sunday': fields.boolean('Opens on Sunday?', help='Does the support open on Sunday?'),
    }

    _defaults = {
        'support_start_time': 8,
        'support_soft_end_time': 16,
        'support_end_time': 17,
        'support_timezone': 'Europe/Zurich',
    }

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
