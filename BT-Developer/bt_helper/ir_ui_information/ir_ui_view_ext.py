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

import ir_ui_view_information


class ir_ui_view_ext(osv.osv):
    _inherit = 'ir.ui.view'

    def action_delete(self, cr, uid, ids, context=None):
        if not isinstance(ids, list):
            ids = [ids]
        if context is None:
            context = {}
        ir_ui_view_information_mod = self.pool.get('bt_helper.ir_ui_view_information')
        ir_model_data_mod = self.pool.get('ir.model.data')
        ir_ui_view_information_id = ir_ui_view_information_mod.create(cr, uid, {'view_id': ids[0]})
        context['show_parent'] = False
        ir_ui_view_information_obj = ir_ui_view_information_mod.browse(cr, uid, ir_ui_view_information_id, context)
        for view in ir_ui_view_information_obj.related_view_ids:
            ir_model_data_ids = ir_model_data_mod.search(cr, uid, [('res_id', '=', view.id), ('model', '=', 'ir.ui.view')])
            ir_model_data_mod.unlink(cr, uid, ir_model_data_ids)
            view.unlink()
        return True
