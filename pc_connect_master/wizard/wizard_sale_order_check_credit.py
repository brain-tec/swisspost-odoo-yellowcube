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
import logging
logger = logging.getLogger(__name__)


class sale_order_check_credit(osv.TransientModel):
    _name = 'sale.order.check_credit'

    _columns = {'result': fields.text('Result', readonly=True)}

    def do_credit_check(self, cr, uid, ids, context=None):
        if context is None:
            context = {}

        result = ''
        for sale_order in self.pool.get(context['active_model']).browse(cr, uid, context.get('active_ids', []), context=context):
            check_credit_result = sale_order.check_credit()
            if check_credit_result['decision'] is False:
                result_description = 'REJECT\n({0})'.format(check_credit_result['description'])
            else:
                result_description = 'ACCEPT\n({0})'.format(check_credit_result['description'])
            result = '{original}Sale Order {sale_order} with ID={id}: {result}\n\n'.format(original=result,
                                                                                           sale_order=sale_order.name,
                                                                                           id=sale_order.id,
                                                                                           result=result_description)

        self.write(cr, uid, ids, {'result': result}, context=context)
        ctx = context.copy()
        ctx['credit_check_done'] = True
        return {'type': 'ir.actions.act_window',
                'res_model': self._name,
                'res_id': ids[0],
                'view_mode': 'form',
                'target': 'new',
                'context': ctx,
                }

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
