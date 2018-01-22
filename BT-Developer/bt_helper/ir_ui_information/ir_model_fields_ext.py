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
from openerp.tools.translate import _
from bt_helper.log_rotate import get_log
logger = get_log("DEBUG")


class ir_model_fields_ext(osv.Model):
    _inherit = 'ir.model.fields'

    def _get_dict(self, cr, uid, ids, field, arg, context=None):
        ret = {}

        def _get_list(dic):
            ret = ''
            for x, v in dic.iteritems():
                _r = _get_list(v) if type(v) is dict else str(v)
                ret = '{0}<li><b>{1}</b>: {2}</li>'.format(ret, x, _r)
            return '<ul>{0}</ul>'.format(ret)

        for _id in ids:
            field = self.browse(cr, uid, _id, context=context)
            pool = self.pool.get(field.model_id.model)
            r = pool.fields_get(cr, uid, allfields=field.name, context=context)
            ret[_id] = _get_list(r)
        return ret

    _columns = {
        'field_to_dict': fields.function(_get_dict, store=False, type="text", string="Field parameters"),
    }

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: