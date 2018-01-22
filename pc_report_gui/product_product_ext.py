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


class product_product_ext(osv.Model):
    _inherit = 'product.product'

    def _fun_orderpoints(self, cr, uid, ids, orderpoints_qty_multiple, arg, context=None):
        stock_warehouse_orderpoint_obj = self.pool.get('stock.warehouse.orderpoint')
        res = {}
        for product_id in ids:
            orderpoint_ids = stock_warehouse_orderpoint_obj.search(cr, uid, [('product_id', '=', product_id)], context=context)
            if orderpoint_ids:
                stock_warehouse_orderpoint = stock_warehouse_orderpoint_obj.browse(cr, uid, orderpoint_ids[0], context=context)
                res[product_id] = {'orderpoints_qty_min': stock_warehouse_orderpoint.product_min_qty,
                                   'orderpoints_qty_max': stock_warehouse_orderpoint.product_max_qty,
                                   'orderpoints_qty_multiple': stock_warehouse_orderpoint.qty_multiple,
                                   }
            else:
                res[product_id] = {'orderpoints_qty_min': False,
                                   'orderpoints_qty_max': False,
                                   'orderpoints_qty_multiple': False,
                                   }
        return res

    def _sto_orderpoints(self, cr, uid, ids, context=None):
        ''' Returns the products' IDs associated to the orderpoints.
        '''
        if context is None:
            context = {}

        product_ids = []
        for orderpoint in self.pool.get('stock.warehouse.orderpoint').browse(cr, uid, ids, context=context):
            product_ids.append(orderpoint.product_id.id)
        return product_ids

    _columns = {
        'orderpoints_qty_min': fields.function(_fun_orderpoints, string='Orderpoint Minimum Quantity', type='float',
                                               help='It displays the minimum quantity of the first orderpoint of the product.',
                                               store={'stock.warehouse.orderpoint': (_sto_orderpoints, ['product_min_qty'], 10)},
                                               multi='orderpoints'),
        'orderpoints_qty_max': fields.function(_fun_orderpoints, string='Orderpoint Maximum Quantity', type='float',
                                               help='It displays the maximum quantity of the first orderpoint of the product.',
                                               store={'stock.warehouse.orderpoint': (_sto_orderpoints, ['product_max_qty'], 10)},
                                               multi='orderpoints'),
        'orderpoints_qty_multiple': fields.function(_fun_orderpoints, string='Orderpoint Quantity Multiple', type='integer',
                                                    help='It displays the quantity multiple of the first orderpoint of the product.',
                                                    store={'stock.warehouse.orderpoint': (_sto_orderpoints, ['qty_multiple'], 10)},
                                                    multi='orderpoints'),
    }

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
