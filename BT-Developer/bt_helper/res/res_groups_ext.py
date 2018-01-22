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
from openerp import netsvc
from openerp.tools import ustr

class res_groups_ext(osv.osv):
    _inherit = 'res.groups'

    def _get_xml_id(self, cr, uid, ids, field, arg, context=None):
        result = {}
        for g in self.browse(cr, uid, ids, context):
            cr.execute("select module || '.' || name as xml_id from ir_model_data where res_id = %s and model = 'res.groups'" %(ustr(g.id)))
            res = cr.dictfetchall()
            ref = res and res[0]['xml_id'] or ''
            result[g.id] = ref
        return result

    _columns = {
        'xml_id': fields.function(_get_xml_id, type="char", string='XML ID'),
    }

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
