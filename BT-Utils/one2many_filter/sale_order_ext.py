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
from generic import one2many_line_ext
from bt_helper.log_rotate import get_log
logger = get_log('DEBUG')


class sale_order_ext(osv.osv):
    _inherit = 'sale.order'

    def __init__(self, pool, cr):
        init_super = super(sale_order_ext, self).__init__(pool, cr)
        for name in ['action_orders', 'action_quotations']:
            cr.execute("""select context,id from ir_act_window where id in (select res_id from ir_model_data where model = 'ir.actions.act_window'  and module='sale' and name='{0}');""".format(name))
            result = cr.fetchall()
            for elem in result:
                context = None
                try:
                    context = eval(elem[0])
                except:
                    pass
                if context is None or not context:
                    context = {}
                context['custom_search_line_discount'] = True
                context['custom_search_line_editor'] = True
                context['custom_search_category_editor'] = True
                value = "{0}".format(context)
                pool.get('ir.actions.act_window').write(cr, 1, elem[1], {'context': value})
        return init_super

    _columns = {
        'order_line': one2many_line_ext('sale.order.line', 'order_id', 'Order Lines',
                                        readonly=True,
                                        states={'draft': [('readonly', False)],
                                                'sent': [('readonly', False)]}),
    }
    def action_invoice_create(self, cr, uid, ids, grouped=False, states=None, date_invoice = False, context=None):
        if context is None:
            context = {}
        context['custom_search_line_discount'] = True
        context['custom_search_line_editor'] = False
        context['custom_search_category_editor'] = False
        result = super(sale_order_ext, self).action_invoice_create(cr, uid, ids, grouped, states, date_invoice, context)
        return result
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
