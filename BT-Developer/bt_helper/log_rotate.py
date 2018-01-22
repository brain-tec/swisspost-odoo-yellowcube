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

import time
import logging
import logging.handlers as handlers
import inspect
import sys
import traceback


class SizedTimedRotatingFileHandler(handlers.TimedRotatingFileHandler):
    """
    Handler for logging to a set of files, which switches from one file
    to the next when the current file reaches a certain size, or at certain
    timed intervals
    """
    def __init__(self, filename, mode='a', maxBytes=0, backupCount=0, encoding=None,
                 delay=0, when='h', interval=1, utc=False):
        # If rotation/rollover is wanted, it doesn't make sense to use another
        # mode. If for example 'w' were specified, then if there were multiple
        # runs of the calling application, the logs from previous runs would be
        # lost if the 'w' is respected, because the log file would be truncated
        # on each run.
        handlers.TimedRotatingFileHandler.__init__(
            self, filename, when, interval, backupCount, encoding, delay, utc)
        self.maxBytes = maxBytes

    def shouldRollover(self, record):
        """
        Determine if rollover should occur.

        Basically, see if the supplied record would cause the file to exceed
        the size limit we have.
        """
        if self.stream is None:                 # delay was set...
            self.stream = self._open()
        if self.maxBytes > 0:                   # are we rolling over?
            msg = "%s\n" % self.format(record)
            self.stream.seek(0, 2)
            if self.stream.tell() + len(msg) >= self.maxBytes:
                return 1
        t = int(time.time())
        if t >= self.rolloverAt:
            return 1
        return 0


def get_log(level='INFO', name=None, _maxBytes=400000, _backupCount=5, _interval=10, file_handler=False):
    if not name:
        curframe = inspect.currentframe()
        calframe = inspect.getouterframes(curframe, 2)
        name = calframe[1][1].replace('/', '.')
    logger = logging.getLogger(name)
    formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
#     if file_handler:
#         file_handler = SizedTimedRotatingFileHandler(
#             "/tmp/odoo{0}.log".format(name), maxBytes=_maxBytes, backupCount=_backupCount,
#             when='s', interval=_interval)
#         file_handler.setFormatter(formatter)
#         logger.addHandler(file_handler)
    if level == 'ERROR':
        level = logging.ERROR
    elif level == 'WARNING':
        level = logging.WARNING
    elif level == 'DEBUG':
        level = logging.DEBUG
    elif level == 'CRITICAL':
        level = logging.CRITICAL
    elif level == 'NOTSET':
        level = logging.NOTSET
    elif level == 'INFO':
        level = logging.INFO
    logger.setLevel(level)
    return logger





def format_exception(exception):
    """
    This method accepts an exception, and depending the kind of exception it is formated in a way

    @param exception: exception to be serialized into an string
    @type exception: Exception

    @return: string version of the exception
    """

    _traceback = traceback.format_exc(limit=10)
    if isinstance(exception, IOError):
        return "{0}\n{1}\n{2}\n{3}\n{4}".format(exception, exception.errno or '', exception.strerror or '', sys.exc_info()[0] or '', _traceback)
    else:
        return "{0}\n{1}\n{2}".format(exception, sys.exc_info()[0] or '', _traceback)


def write_log(delegate, cr_original, uid, table_name, object_name, object_id, information, correct=True, extra_information='', context=None):
    """
    This method creates a log entry, based on the filters defined for an specific table,
    and if such table does not have a related filter, a default one will be created.

    @param delegate: object with pool variable that called this method
    @type delegate: osv.Model
    @param cr_original: original cursor used by the delegate object
    @type cr_original: cursor
    @param uid: user ID
    @type uid: integer
    @param table_name: name of the table that is related to this log
    @type table_name: string
    @param object_name: identifier name of the related object
    @type object_name: string
    @param information: description of the log entry
    @type information: string
    @param correct: is the log entry for a correct behaviour?
    @type correct: Boolean
    @param extra_information:addiional information about this log entry
    @type extra_information: string

    @return: True
    """
    filter_obj = delegate.pool.get('log.data.filter')
    model_obj = delegate.pool.get('ir.model')
    cr = delegate.pool.db.cursor()
    model_ids = model_obj.search(cr, uid, [('model', '=', table_name)])
    filter_id = filter_obj.search(cr, uid, [('model_id', 'in', model_ids)])
    if context is None:
        context = {}
    if not filter_id:
        #logger.debug("Filter does not exist for class {0}".format(table_name))
        if not filter_obj.search(cr, uid, [('model_id', 'in', model_ids)]):
            #logger.warning("This model does not contain a filter: {0}".format(model_ids[0]))
            filter_obj.create(cr, uid, {'model_id': model_ids[0]})
        cr.commit()
        cr.close()
        return True

    var_filter = filter_obj.browse(cr, uid, filter_id)[0]
    if correct and var_filter.log_normal_execution or not correct and var_filter.log_error:
        data = {
            'model_id': var_filter.model_id.id,
            'model_name': var_filter.model_id.name,
            'table_name': table_name,
            'object_name': object_name,
            'ref_id': object_id,
            'information': str(information),
            'correct': correct,
            'extra_information': str(extra_information)
        }
        delegate.pool.get('log.data').create(cr, uid, data, context=context)

    cr.commit()
    cr.close()
    return True

