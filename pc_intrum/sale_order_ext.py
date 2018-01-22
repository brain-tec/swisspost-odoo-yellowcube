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
from report_webkit import report_helper
from pc_generics import generics
import netsvc


def _get_store_for(arg):
    def f(self, cr, uid, ids, context=None):
        result = []
        for values in self.read(cr, uid, ids, [arg], context):
            _arg = values[arg]
            if _arg:
                result.append(_arg[0])
        return result
    return (f, [arg], 10)


class sale_order_ext(osv.Model):
    _inherit = "sale.order"

    def _get_last_intrum_request(self, cr, uid, ids, field, arg, context=None):
        results = {}
        for _id in ids:
            cr.execute('SELECT id FROM intrum_request WHERE order_id={0} ORDER BY write_date DESC'.format(_id))
            res = cr.fetchone()
            if res:
                results[_id] = res[0]
            else:
                results[_id] = None
        return results

    def _get_last_intrum_request_code(self, cr, uid, ids, field, arg, context=None):
        results = {}
        if ids:
            cr.execute('SELECT id, last_intrum_check FROM sale_order WHERE id in ({0})'.format(','.join([str(x) for x in ids])))
            intrum_request_obj = self.pool.get('intrum.request')
            for _id, _ir in cr.fetchall():
                results[_id] = _ir and intrum_request_obj.read(cr, uid, int(_ir), ['response_text'], context)['response_text'] or 'Not checked'
        return results

    _columns = {
        'last_intrum_check': fields.function(_get_last_intrum_request,
                                             type='many2one',
                                             relation='intrum.request',
                                             store={'intrum.request': _get_store_for('order_id')}
                                             ),
        'last_intrum_response': fields.function(_get_last_intrum_request_code,
                                                type='text',
                                                store=False,
                                                string='Last credit check')
    }

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
