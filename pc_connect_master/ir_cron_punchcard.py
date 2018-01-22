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
from datetime import datetime
from openerp.tools import DEFAULT_SERVER_DATETIME_FORMAT
from utilities.db import create_db_index


class ir_cron_punchcard(osv.Model):
    _name = 'ir.cron.punchcard'
    _rec_name = 'create_date'
    _order = 'create_date DESC'

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

    def init(self, cr):
        """ Creates some indices that can not be created directly using the ORM
        """
        # Index for execution_day but in descending order (the one created by select=True should be the default one,
        # that is in ascending order)
        create_db_index(cr, 'ir_cron_punchcard_execution_day_desc_index', 'ir_cron_punchcard', 'execution_day DESC')

        # Index for create_date in descending order (the one created by select=True should be the default one,
        # that is in ascending order)
        create_db_index(cr, 'ir_cron_punchcard_create_date_desc_index', 'ir_cron_punchcard', 'create_date DESC')

    def limit_the_amount_of_punchcards(self, cr, uid, context=None):
        """ We limit the number of punchcards to the amount indicated in the configuration, thus
            we remove the extra ones (keeping only the newest ones).
        """
        if context is None:
            context = {}

        configuration = self.pool.get('configuration.data').get(cr, uid, [])

        punchcards_limit = configuration.punchcards_limit
        if punchcards_limit:
            all_punchards_to_remove_ids = []

            # Done with a SQL because this ir_cron_obj.search(cr, uid, [], context=context)
            # doesn't work. Apparently ir.cron hides himself.
            cr.execute("""SELECT DISTINCT(ir_cron) FROM ir_cron_punchcard;""")
            job_ids = [job_id[0] for job_id in cr.fetchall()]

            for job_id in job_ids:
                punchcards_to_keep_ids = self.search(cr, uid, [('ir_cron', '=', job_id),
                                                               ], order='create_date DESC')
                if len(punchcards_to_keep_ids) > punchcards_limit:
                    last_allowed_create_date = self.browse(cr, uid, punchcards_to_keep_ids[punchcards_limit-1], context=context).create_date
                    punchards_to_remove_ids = self.search(cr, uid, [('ir_cron', '=', job_id),
                                                                    ('create_date', '<', last_allowed_create_date),
                                                                    ])
                    all_punchards_to_remove_ids.extend(punchards_to_remove_ids)

            if all_punchards_to_remove_ids:
                self.unlink(cr, uid, all_punchards_to_remove_ids)

        return True

    _columns = {
        'ir_cron': fields.integer('Scheduler', required=True, readonly=True, select=True),  # fields.many2one('ir.cron', 'Scheduler', required=True, readonly=True),
        'create_date': fields.datetime('Create date', require=True, readonly=True),
        'end_date': fields.datetime('End date', readonly=True),
        'execution_day': fields.date('Execution day', require=True, readonly=True),
        'create_uid': fields.many2one('res.users', 'Executer', required=True, readonly=True),
        'difference_free_memory': fields.integer('Difference in Free Memory', readonly=True,
                                                 help='Difference of free memory, in kB, between the start and the end of the scheduler, '
                                                 'so a negative number indicates that the amount of free memory was decreased.'),
    }

    _defaults = {
        'execution_day': lambda *args: datetime.now(),
    }

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
