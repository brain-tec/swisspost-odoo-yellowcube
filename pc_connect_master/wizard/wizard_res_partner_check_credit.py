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

from openerp.osv import osv, fields
from openerp.tools.translate import _
import logging
logger = logging.getLogger(__name__)


class res_partner_check_credit(osv.TransientModel):
    _name = 'res.partner.check_credit'

    _columns = {
        'order_amount': fields.float("Amount to check", required=True),
        'order_currency': fields.many2one('res.currency', string="Currency of payment", required=True),
        'result': fields.text('Result', readonly=True),
    }

    def do_credit_check(self, cr, uid, ids, context=None):
        if context is None:
            context = {}

        wizard = self.browse(cr, uid, ids[0], context=context)

        ctx = context.copy()
        ctx['currency_name'] = wizard.order_currency.name

        result = ''
        for res_partner in self.pool.get(ctx['active_model']).browse(cr, uid, ctx.get('active_ids', []), context=ctx):
            check_credit_result = res_partner.check_credit(wizard.order_amount, context=ctx)
            if check_credit_result['decision'] is False:
                result_description = 'REJECT\n({0})'.format(check_credit_result['description'])
            else:
                result_description = 'ACCEPT\n({0})'.format(check_credit_result['description'])
            result = '{original}Partner {partner_name} with ID={id}: {result}\n\n'.format(original=result,
                                                                                          partner_name=res_partner.name,
                                                                                          id=res_partner.id,
                                                                                          result=result_description)

        self.write(cr, uid, ids, {'result': result}, context=ctx)
        ctx['credit_check_done'] = True
        return {'type': 'ir.actions.act_window',
                'res_model': self._name,
                'res_id': ids[0],
                'view_mode': 'form',
                'target': 'new',
                'context': ctx,
                }

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
