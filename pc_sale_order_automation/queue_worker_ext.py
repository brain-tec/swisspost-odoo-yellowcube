# b-*- encoding: utf-8 -*-
##############################################################################
#
#    Copyright (c) 2017 brain-tec AG (http://www.braintec-group.com
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


from openerp.osv import osv, fields, orm
from openerp.addons.connector.queue.worker import watcher
import logging
_logger = logging.getLogger(__name__)


class QueueWorkerExt(orm.Model):
    _inherit = 'queue.worker'

    def _assign_jobs(self, cr, uid, max_jobs=None, context=None):
        """ This method is (almost) the same than is on the module connector,
            with the difference that, before calling that code,
            we add to the queue all those jobs that have a step in
            the Sale Order Automation which has a nearly negligible cost.

            Just in case, we don't add more than 4 times the max_jobs, thus
            we may execute up to 5 times the max_jobs.
        """
        soa_ratio_increase = self.pool.get('configuration.data').get(
            cr, uid, [], context=context).soa_ratio_increase

        if soa_ratio_increase:
            sql = ("SELECT id FROM queue_job "
                   "WHERE worker_id IS NULL "
                   "AND state NOT IN ('failed', 'done') "
                   "AND active = TRUE "
                   "AND (   func_string LIKE '%''saleorder_check_inventory_for_quotation''%'"
                   "     OR func_string LIKE '%''saleorder_checkcredit''%'"
                   "     OR func_string LIKE '%''saleorder_draft''%')"
                   "ORDER BY eta NULLS LAST, priority, date_created ")
            if max_jobs is not None:
                sql += ' LIMIT %d' % (soa_ratio_increase * max_jobs)
            sql += ' FOR UPDATE NOWAIT'

            # use a SAVEPOINT to be able to rollback this part of the
            # transaction without failing the whole transaction if the LOCK
            # cannot be acquired
            worker = watcher.worker_for_db(cr.dbname)
            cr.execute("SAVEPOINT queue_assign_jobs")
            try:
                cr.execute(sql, log_exceptions=False)
            except Exception:
                # Here it's likely that the FOR UPDATE NOWAIT failed to get
                # the LOCK, so we ROLLBACK to the SAVEPOINT to restore the
                # transaction to its earlier state. The assign will be done
                # the next time.
                cr.execute("ROLLBACK TO queue_assign_jobs")
                _logger.debug("Failed attempt to assign jobs, likely due to "
                              "another transaction in progress. "
                              "Trace of the failed assignment of jobs on worker "
                              "%s attempt: ", worker.uuid, exc_info=True)
                return
            job_rows = cr.fetchall()
            job_ids = [id for id, in job_rows]

            try:
                worker_id = self._worker_id(cr, uid, context=context)
            except AssertionError as e:
                _logger.exception(e)
                return
            _logger.debug('Assign %d jobs to worker %s', len(job_ids),
                          worker.uuid)
            # ready to be enqueued in the worker
            try:
                self.pool.get('queue.job').write(cr, uid, job_ids,
                                                 {'state': 'pending',
                                                  'worker_id': worker_id},
                                                 context=context)
            except Exception:
                pass  # will be assigned to another worker

        # Calls the regular code of the connector.
        super(QueueWorkerExt, self)._assign_jobs(cr, uid, max_jobs=max_jobs,
                                                 context=context)

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
