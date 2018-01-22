# b-*- encoding: utf-8 -*-
##############################################################################
#
#    Copyright (c) 2014 brain-tec AG (http://www.braintec-group.com)
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


class intrum_response_code(osv.Model):
    _name = 'intrum.response_code'
    _rec_name = 'intrum_response_text'

    _columns = {
        'intrum_response_code': fields.integer("Code of Intrum's Response", required=True),
        'intrum_response_text': fields.text("Text of Intrum's Response", required=True),
    }

    def get_response_text(self, cr, uid, ids, response_code, context=None):
        ''' Given an Intrum's code, returns its associated text,
            or the empty string if it does not exist.
        '''
        if context is None:
            context = {}
        if type(ids) is not list:
            ids = [ids]

        intrum_response_code_id = self.search(cr, uid, [('intrum_response_code', '=', response_code)], context=context, limit=1)[0]
        if intrum_response_code_id:
            response_text = self.browse(cr, uid, intrum_response_code_id, context=context).intrum_response_text
        else:
            response_text = ''
        return response_text

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
