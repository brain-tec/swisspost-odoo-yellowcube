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
from osv import osv, fields, orm
from openerp.tools.translate import _
from bt_helper.log_rotate import get_log
logger = get_log("DEBUG")
import functools
from base_import.models import ir_import

from bt_export_all.export_all import export_all


def __new_export(f):
    """
    This function decorates orm.BaseModel.export_data.
    When the option Export_all is selected it does not export anything automatically but starts a new pathway
    to do the export in background and then send the export to
    """
    @functools.wraps(f)
    def __export_delegate(self, cr, uid, ids, fields_to_export, context=None):
        # logger.debug("export_delegate({0}, {1}, {2}, {3}, {4}, context={5})".format(self, cr, uid, ids, fields_to_export, context))

        if context and context.get('export_all', False):
            model = context['model']
            md = self.pool.get(model)
            ids = md.search(cr, uid, [], context=context)
            return f(self, cr, uid, ids, fields_to_export, context=context)
            # return True
        else:
            return f(self, cr, uid, ids, fields_to_export, context=context)

    return __export_delegate


orm.BaseModel.export_data = __new_export(orm.BaseModel.export_data)


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
