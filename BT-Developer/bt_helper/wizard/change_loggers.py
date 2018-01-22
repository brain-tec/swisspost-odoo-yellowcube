# -*- coding: utf-8 -*-
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


from osv import osv, fields
from tools.translate import _
import time
import logging

class change_loggers(osv.osv):
    _name = "bt_helper.change_loggers"
    _description = "Change logger wizard"

    def _create_loggers(self, cr, uid, ctx):
        btlogger_ids = []
        btlogger_model = self.pool.get('bt_helper.btlogger')
        for logger_key in logging.Logger.manager.loggerDict:
            logger = logging.getLogger(logger_key)
            btlogger_ids.append(btlogger_model.create(cr, uid, {'name': logger_key,
                                                          'level': logger.level}))
        return btlogger_ids

    _columns = {
        'name': fields.char(_('Name'), size=128, required=True,
                                             help=_('By default: NOTSET = 0, DEBUG = 10, INFO = 20, WARNING = 30, ERROR = 40')),

        'btlogger_ids': fields.one2many('bt_helper.btlogger',
                                        'change_loggers_id',
                                        _('Current loggers')),
        'due_date': fields.date(_('Due Date'), required=True),

    }
    _defaults = {
        'btlogger_ids': _create_loggers,
        'due_date': lambda self, cr, uid, context: time.strftime('%Y-%m-%d'),
    }

    def update_loggers(self, cr, uid, ids, context=None):
        if context is None:
            context = {}

        change_loggers = self.browse(cr, uid, ids)[0]
        for aux_btlogger in change_loggers.btlogger_ids:
            if aux_btlogger.new_level != -1:
                if isinstance(aux_btlogger.new_level, int):
                    aux_logger = logging.getLogger(aux_btlogger.name)
                    aux_logger.setLevel(aux_btlogger.new_level)
        return True

    def copy_current_level(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        bt_helper_btlogger_model = self.pool.get('bt_helper.btlogger')
        for btlogger in self.browse(cr, uid, ids, context)[0].btlogger_ids:
            bt_helper_btlogger_model.write(cr, uid, [btlogger.id],
                                           {'new_level': btlogger.level})
        return True


class btlogger(osv.osv):
    _name = 'bt_helper.btlogger'
    _description = 'BT loggers'

    _columns = {
        'name': fields.char(_('Name'), size=128, required=True),
        'level': fields.integer(_('Level'), required=True,
                                             help=_('By default: NOTSET = 0, DEBUG = 10, INFO = 20, WARNING = 30, ERROR = 40')),
        'new_level': fields.integer(_('Set new level')),
        'change_loggers_id': fields.many2one('bt_helper.change_loggers', _('Change logger wizard'),
                                             ondelete='cascade'),
    }
    _defaults = {
                 'new_level': -1,
                 }
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
