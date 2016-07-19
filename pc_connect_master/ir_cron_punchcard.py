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

from osv import osv, fields
from datetime import datetime
from openerp.tools import DEFAULT_SERVER_DATETIME_FORMAT


class ir_cron_punchcard(osv.Model):
    _name = 'ir.cron.punchcard'
    _rec_name = 'create_date'
    _order = 'create_date DESC'

    def unlink(self, cr, uid, ids, context=None):
        self.write(cr, uid, ids, {'active': False}, context=context)

    def entry_exists_after_or_at(self, cr, uid, ids, ir_cron_id, today_date, target_hour, context=None):
        ''' Checks if, for the given scheduler, exists an entry for today which has an
            hour which is greater or equal than the provided one (target_hour)
        '''
        if context is None:
            context = {}

        # Sets the timezone to that indicated in the configuration.
        config = self.pool.get('configuration.data').get(cr, uid, [])
        context['tz'] = config.support_timezone

        entries_today_ids = self.search(cr, uid, [('ir_cron', '=', ir_cron_id),
                                                  ('execution_day', '>=', today_date),
                                                  ], order='create_date DESC', context=context)

        for entry in self.browse(cr, uid, entries_today_ids, context=context):
            create_time_local = fields.datetime.context_timestamp(cr, uid, datetime.strptime(entry.create_date, DEFAULT_SERVER_DATETIME_FORMAT), context)
            if create_time_local.time() >= target_hour:
                return True

        return False

    _columns = {
        'ir_cron': fields.integer('Scheduler', required=True, readonly=True),  # fields.many2one('ir.cron', 'Scheduler', required=True, readonly=True),
        'create_date': fields.datetime('Create date', require=True, readonly=True),
        'execution_day': fields.date('Execution day', require=True, readonly=True),
        'create_uid': fields.many2one('res.users', 'Executer', required=True, readonly=True),
        'active': fields.boolean('Active?')
    }

    _defaults = {
        'execution_day': lambda *args: datetime.now(),
        'active': True,
    }

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
