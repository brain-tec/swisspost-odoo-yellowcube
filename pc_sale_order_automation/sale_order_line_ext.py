# b-*- encoding: utf-8 -*-
##############################################################################
#
#    Copyright (c) 2017 brain-tec AG (http://www.braintec-group.com)
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

from openerp.osv import osv, fields, orm
from openerp.addons.decimal_precision import decimal_precision as dp
from openerp.addons.pc_connect_master.utilities.db import create_db_index


class SaleOrderLineExt(osv.Model):
    _inherit = 'sale.order.line'

    def init(self, cr):
        create_db_index(cr, 'sale_order_line_order_id_alt_carrier_id_index',
                        'sale_order_line',
                        'order_id, alt_carrier_id')

    def _prepare_order_line_invoice_line(self, cr, uid, line, account_id=False,
                                         context=None):
        """ Overridden so that it keeps track of the originating
            sale.order.line that generated the account.invoice.line.
        """
        ret = super(SaleOrderLineExt, self)._prepare_order_line_invoice_line(
            cr, uid, line, account_id=account_id, context=context)

        ret.update({'orig_sale_order_line_id': line.id})

        return ret

    def compute_purchase_uom(self, cr, uid, ids, context=None):
        """ For each sale.order.line it fills its fields
            product_uop and product_uop_qty with the unit of
            purchase order, and its converted quantity.
        """
        if context is None:
            context = {}
        if type(ids) is not list:
            ids = [ids]

        uom_obj = self.pool.get('product.uom')

        for line in self.browse(cr, uid, ids, context=context):
            if hasattr(line, 'is_discount') and line.is_discount:
                continue

            product = line.product_id
            product_uop_qty = uom_obj._compute_qty_obj(cr, uid,
                                                       line.product_uom,
                                                       line.product_uom_qty,
                                                       product.uom_po_id)
            line.write({
                'product_uop': product.uom_po_id.id,
                'product_uop_qty': product_uop_qty,
            })

        return True

    _columns = {
        'product_uop_qty': fields.float(
            'Quantity for the UOM for Purchases',
            digits_compute=dp.get_precision('Product Unit of Measure'),
            readonly=True),
        'product_uop': fields.many2one(
            'product.uom', 'Product Unit of Measure for Purchases',
            readonly=True),
    }

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
