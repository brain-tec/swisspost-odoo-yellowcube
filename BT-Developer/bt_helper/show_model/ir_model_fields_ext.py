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


class ir_model_fields_ext(osv.osv):
    _inherit = 'ir.model.fields'

    def name_get(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        if isinstance(ids, (int, long)):
            ids = [ids]
        res = []
        for record in self.browse(cr, uid, ids, context=context):
            name = record.field_description
            if context.get('show_field'):
                name = record.name
            res.append((record.id, name))
        return res
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
