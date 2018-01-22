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

from osv import orm, osv, fields
from datetime import datetime, timedelta
from openerp.tools import DEFAULT_SERVER_DATETIME_FORMAT


class queue_worker_ext(orm.Model):
    _inherit = 'queue.worker'

    def get_error_messages_to_requeue(self, cr, uid, context):
        ''' Returns a list with error messages to requeue.
        '''
        error_messages_to_requeue = ['%could not serialize access due to concurrent update%']
        return error_messages_to_requeue

    def enqueue_jobs(self, cr, uid, context=None):
        ''' Overrides the original method so that we also search for any jobs
            which had failed because of a concurrent update error, and then requeue them.
        '''
        job_obj = self.pool.get('queue.job')
        now = datetime.now()
        conf_data = self.pool.get('configuration.data').get(cr, uid, [], context=context)

        super(queue_worker_ext, self).enqueue_jobs(cr, uid, context)

        requeue_job_ids = []
        for error_message in self.get_error_messages_to_requeue(cr, uid, context):
            job_ids = job_obj.search(cr, uid, [('state', '=', 'failed'),
                                               ('exc_info', 'like', error_message),
                                               ('id', 'not in', requeue_job_ids),
                                               ], context=context)
            requeue_job_ids.extend(job_ids)

        # From those jobs, only requeues those which were created a number
        # of minutes ago, to avoid requeueing them forever.
        for job in job_obj.browse(cr, uid, requeue_job_ids, context=context):
            job_date_created = datetime.strptime(job.date_created, DEFAULT_SERVER_DATETIME_FORMAT)
            if now <= (job_date_created + timedelta(minutes=conf_data.concurrent_access_requeue_num_minutes)):
                job.requeue()

        return True

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
