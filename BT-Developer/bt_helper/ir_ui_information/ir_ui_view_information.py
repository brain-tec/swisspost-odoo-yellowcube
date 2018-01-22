# b-*- encoding: utf-8 -*-
##############################################################################
#
#    Copyright (c) 2010 brain-tec AG (http://www.brain-tec.ch) 
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

from osv import fields, osv
from osv.orm import *
from openerp.tools.translate import _

from bt_helper.log_rotate import get_log
logger = get_log('DEBUG')


class ir_ui_view_information(osv.osv):
    _name = 'bt_helper.ir_ui_view_information'
    _description = 'BT Helper IR UI view information'

    def _get_related_views(self, cr, uid, ids, name, arg, context=None):
        res = {}
        if context is None:
            context = {}
        ir_ui_view_model = self.pool.get('ir.ui.view')

        for ir_ui_view_information in self.browse(cr, uid, ids, context):
            res[ir_ui_view_information.id] = []

            stack_not_added = []
            stack_not_added.append(ir_ui_view_information.view_id.id)

            while stack_not_added:
                view_id = stack_not_added.pop()
                view_obj = ir_ui_view_model.browse(cr, uid, view_id, context)
                if view_obj.id in res[ir_ui_view_information.id]:
                    continue
                res[ir_ui_view_information.id].append(view_obj.id)
                if context.get('show_parent', True):
                    if view_obj.inherit_id:
                        stack_not_added.append(view_obj.inherit_id.id)
                stack_not_added.extend(ir_ui_view_model.search(cr, uid, [('inherit_id', '=', view_obj.id)]))
        return res

    _columns = {
        'view_id': fields.many2one('ir.ui.view', 'View', require=True),
        'related_view_ids': fields.function(_get_related_views, method=True, string="Related views", type="one2many", obj="ir.ui.view"),
    }
