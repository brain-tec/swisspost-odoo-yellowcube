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
from openerp.osv import osv, fields
from openerp.tools.translate import _


class ir_values_ext(osv.Model):
    _inherit = 'ir.values'

    def get_actions(self, cr, uid, action_slot, model, res_id=False, context=None):
        ret = super(ir_values_ext, self).get_actions(cr, uid, action_slot, model, res_id=res_id, context=context)
        any = super(ir_values_ext, self).get_actions(cr, uid, action_slot, '*', res_id=res_id, context=context)
        ret.extend(any)
        return ret

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: