# b-*- encoding: utf-8 -*-
##############################################################################
#
#    Copyright (c) 2014 brain-tec AG (http://www.brain-tec.ch)
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
from openerp.tools.translate import _
from openerp.tools.safe_eval import safe_eval
import logging
from openerp.addons.pc_connect_master.utilities.misc import format_exception
from openerp import netsvc
import logging
import time
import datetime
import pytz
logger = logging.getLogger(__name__)

TIME_OF_DAY_1 = '{0}_time_of_day'
TIME_OF_DAY_2 = '{0}_time_of_day_2'
TIME_OF_DAY_3 = '{0}_time_of_day_3'

DAYS = [
    '{0}_monday',
    '{0}_tuesday',
    '{0}_wednesday',
    '{0}_thursday',
    '{0}_friday',
    '{0}_saturday',
    '{0}_sunday'
]


def str2tuple(s):
    return eval('tuple(%s)' % (s or ''))


class ir_cron_ext(osv.osv):
    _name = 'ir.cron'
    _inherit = ['ir.cron', 'mail.thread']

    def _handle_callback_exception(self, cr, uid, model_name, method_name, args, job_id, job_exception):
        return super(ir_cron_ext, self)._handle_callback_exception(cr, uid, model_name, method_name, args, job_id, job_exception)

    def _check_punchcard(self, cr, uid, job_id):
        ''' Checks if the ir.cron has a punchcard set. If that is the case,
            checks if, according to its timing, we can execute the scheduler or not.
                Returns False if we can not run the scheduler according to its
            punchcard, and a dictionary otherwise with the date of the execution.
        '''
        job = self.browse(cr, uid, job_id)

        config = self.pool.get('configuration.data').get(cr, uid, [])
        punch_obj = self.pool.get('ir.cron.punchcard')

        # Time to check if work can be done
        now_local = datetime.datetime.now().replace(tzinfo=pytz.utc).astimezone(pytz.timezone(config.support_timezone))

        punch_values = {'ir_cron': job_id, 'execution_day': now_local.date()}

        if not job.punchcard_prefix:
            return punch_values

        # Checks that we have at least one time that the punchard requires.
        if TIME_OF_DAY_1.format(job.punchcard_prefix) not in config:
            raise orm.except_orm(_('Missing Punchcard prefix on configuration.data'), job.punchcard_prefix)

        if not config[DAYS[now_local.weekday()].format(job.punchcard_prefix)]:
            # Only work on accepted days
            return False

        # We checked before that we have this time.
        tod = config[TIME_OF_DAY_1.format(job.punchcard_prefix)]
        tod_1 = datetime.time(int(tod), int(round(60 * tod)) % 60).replace(tzinfo=pytz.timezone(config.support_timezone))

        # Second time is optional, thus may not exist, of exist but be empty.
        tod_2 = None
        if TIME_OF_DAY_2.format(job.punchcard_prefix) in config:
            tod = config[TIME_OF_DAY_2.format(job.punchcard_prefix)]
            if tod:
                tod_2 = datetime.time(int(tod), int(round(60 * tod)) % 60).replace(tzinfo=pytz.timezone(config.support_timezone))

        # Third time is optional, thus may not exist, of exist but be empty.
        tod_3 = None
        if TIME_OF_DAY_3.format(job.punchcard_prefix) in config:
            tod = config[TIME_OF_DAY_3.format(job.punchcard_prefix)]
            if tod:
                tod_3 = datetime.time(int(tod), int(round(60 * tod)) % 60).replace(tzinfo=pytz.timezone(config.support_timezone))

        exists_punchard_for_today = punch_obj.search(cr, uid, [('ir_cron', '=', job_id),
                                                               ('execution_day', '=', now_local.date()),
                                                               ], count=True)

        def __entry_exists_after_or_at(hour):
            return punch_obj.entry_exists_after_or_at(cr, uid, [], job.id, now_local.date(), hour)

        if not exists_punchard_for_today:
            if tod_3 and (now_local.time() >= tod_3):
                return punch_values
            elif tod_2 and (now_local.time() >= tod_2):
                return punch_values
            elif tod_1 and (now_local.time() >= tod_1):
                return punch_values
            else:
                return False
        else:  # If we already have a punchcard for today.
            if tod_3 and __entry_exists_after_or_at(tod_3):
                return False  # No more executions for today.
            elif tod_2 and tod_3 and __entry_exists_after_or_at(tod_2) and (not __entry_exists_after_or_at(tod_3)) and (now_local.time() >= tod_3):
                return punch_values
            elif tod_1 and tod_2 and __entry_exists_after_or_at(tod_1) and (not __entry_exists_after_or_at(tod_2)) and (now_local.time() >= tod_2):
                return punch_values
            elif tod_1 and (not __entry_exists_after_or_at(tod_1)) and (now_local.time() >= tod_1):
                # This will only be executed if the punchcard is set
                # *after* the first execution is done.
                return punch_values
            else:
                return False

        return False

    def _callback(self, cr, uid, model_name, method_name, args, job_id):
        ''' Executes the scheduler only if it can be executed according to its punchcard
            AND the system's parameter do_not_execute_schedulers is not set to True.
        '''
        # If we have a system's parameter which is called 'do_not_execute_schedulers' and it
        # is set to True, then we do not execute the scheduler.
        do_not_execute_schedulers = safe_eval(self.pool.get('ir.config_parameter').get_param(cr, uid, 'do_not_execute_schedulers', 'False'))
        if do_not_execute_schedulers is True:
            return False

        # If, according to punchcards, it can not execute the scheduler, returns False.
        punch_values = self._check_punchcard(cr, uid, job_id)
        if not punch_values:
            return False

        ir_cron_punchcard_obj = self.pool.get('ir.cron.punchcard')

        # If we can execute, we log the punchcard...
        ir_cron_punchcard_obj.create(cr, uid, punch_values)

        # We limit the number of punchcards to the amount indicated in the configuration, thus
        # we remove the extra ones (keeping only the newest ones).
        configuration = self.pool.get('configuration.data').get(cr, uid, [])
        if configuration.punchcards_limit:
            punchcards_to_keep_ids = ir_cron_punchcard_obj.search(cr, uid, [('ir_cron', '=', job_id)], limit=configuration.punchcards_limit, order='execution_day DESC')
            if punchcards_to_keep_ids:
                punchards_to_remove_ids = ir_cron_punchcard_obj.search(cr, uid, [('ir_cron', '=', job_id),
                                                                                 ('id', 'not in', punchcards_to_keep_ids),
                                                                                 ])
                ir_cron_punchcard_obj.unlink(cr, uid, punchards_to_remove_ids)

        # ... and continue with the normal execution of the scheduler.
        args = str2tuple(args)
        model = self.pool.get(model_name)
        ret = False
        if model and hasattr(model, method_name):
            method = getattr(model, method_name)
            try:
                log_depth = (None if logger.isEnabledFor(logging.DEBUG) else 1)
                netsvc.log(logger, logging.DEBUG, 'cron.object.execute', (cr.dbname, uid, '*', model_name, method_name) + tuple(args), depth=log_depth)
                if logger.isEnabledFor(logging.DEBUG):
                    start_time = time.time()
                ret = method(cr, uid, *args)
                if ret and isinstance(ret, str):
                    ctx = {'thread_id': job_id, 'thread_model': 'ir.cron'}
                if logger.isEnabledFor(logging.DEBUG):
                    end_time = time.time()
                    logger.debug('%.3fs (%s, %s)' % (end_time - start_time, model_name, method_name))
            except Exception as e:
                self._handle_callback_exception(cr, uid, model_name, method_name, args, job_id, e)
        return ret

    def _get_punchcards(self, cr, uid, ids, name, arg, context=None):
        ret = {}
        for _id in ids:
            ret[_id] = self.pool.get('ir.cron.punchcard').search(cr, uid, [('ir_cron', '=', _id)], context=context)
        return ret

    def button_execute_job(self, cr, uid, ids, context=None):
        for this in self.browse(cr, uid, ids, context=context):
            logger.debug("Manually executing scheduler {0}.".format(this.name))
            self._callback(cr, this.user_id.id, this.model, this.function, this.args, this.id)
        return True

    _columns = {
        'punchcard_prefix': fields.char('Punchcard prefix', required=False),
        'punchcards_ids': fields.function(_get_punchcards, type='one2many', relation='ir.cron.punchcard', string='Punchcard')
    }

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
