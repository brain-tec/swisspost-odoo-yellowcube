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

from osv import fields, osv
from osv.orm import *
from openerp.tools.translate import _

from bt_helper.log_rotate import get_log
logger = get_log('DEBUG')


class ir_ui_menu_information(osv.osv):
    _name = 'bt_helper.ir_ui_menu_information'
    _description = 'BT Helper IR UI menu information'

    def _get_related_menus(self, cr, uid, ids, name, arg, context=None):
        res = {}
        if context is None:
            context = {}
        ir_ui_menu_model = self.pool.get('ir.ui.menu')

        for ir_ui_menu_information in self.browse(cr, uid, ids, context):
            res[ir_ui_menu_information.id] = [ir_ui_menu_information.menu_id.id]
            menu_obj = ir_ui_menu_model.browse(cr, uid, ir_ui_menu_information.menu_id.id)
            cr.execute("SELECT id, name FROM ir_ui_menu WHERE parent_left > {0} AND parent_right < {1};".format(menu_obj.parent_left, menu_obj.parent_right))
            try:
                res[ir_ui_menu_information.id].extend([i[0] for i in cr.fetchall()])
            except:
                pass
        return res

    _columns = {
        'menu_id': fields.many2one('ir.ui.menu', 'View', require=True),
        'related_menu_ids': fields.function(_get_related_menus, method=True, string="Related menus", type="one2many", obj="ir.ui.menu"),
    }
