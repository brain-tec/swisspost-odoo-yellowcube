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
from openerp.osv import osv, fields, orm
from openerp.tools.translate import _
import functools
import traceback
from openerp import SUPERUSER_ID
import logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


def __new_unlink(f):
    """
    This function decorates the function orm.BaseModel.unlink, in order to prevent deletions by error

    """
    @functools.wraps(f)
    def __unlink(self, cr, uid, ids, context=None):
        user = self.pool['res.users'].browse(cr, uid, uid, context)
        if not ids or not hasattr(user, 'unlink_failsafe') or not getattr(user, 'unlink_failsafe'):
            return f(self, cr, uid, ids, context)

        if uid == SUPERUSER_ID and [x for x in traceback.extract_stack() if x[2] == 'load_modules']:
            # We check if this piece of code is been execute on import.
            #  Programmers are always safe to remove records
            logger.debug("Under import, SUPERUSER is always safe to unlink")
            return f(self, cr, uid, ids, context)

        if type(ids) is not list:
            ids = [ids]
        _sql = """
        select module
        from ir_model_data
        where model = '{0}'
        and
        module not in ('', '__export__')
        and
        res_id in ({1});""".format(self._name, ','.join([str(x) for x in ids]))
        cr.execute(_sql)
        err = ', '.join([x[0] for x in cr.fetchall()])
        if err:
            raise orm.except_orm(_('Record defined in module. Must not unlink.'), err)
        else:
            return f(self, cr, uid, ids, context)
    return __unlink

orm.BaseModel.unlink = __new_unlink(orm.BaseModel.unlink)


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
