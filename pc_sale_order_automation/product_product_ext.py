# b-*- encoding: utf-8 -*-
##############################################################################
#
#    Copyright (c) 2016 brain-tec AG (http://www.braintec-group.com
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


class product_product_ext_lot(osv.Model):
    _inherit = 'product.product'

    def qty_on_picking(self, cr, uid, ids, picking_id, context=None):
        ''' Gets the quantity which is reserved for this product on this picking,
            i.e. that appears in stock.moves of this picking.
            The quantity is returned in the UOM of the product.
            It only considers those pickings which are NOT on states
            'draft', 'cancel' or 'done'.
        '''
        if context is None:
            context = {}
        if type(ids) is not list:
            ids = [ids]
        product_id = ids[0]

        product_uom_obj = self.pool.get('product.uom')
        stock_picking_obj = self.pool.get('stock.picking')

        picking = stock_picking_obj.browse(cr, uid, picking_id, context=context)

        qty_for_product = 0.0
        for stock_move in picking.move_lines:
            if (stock_move.product_id.id == product_id) and (stock_move.state not in ('draft', 'cancel', 'done')):
                qty_for_product_uom = product_uom_obj._compute_qty(cr, uid, stock_move.product_uom.id, stock_move.product_qty, stock_move.product_id.uom_id.id)
                qty_for_product += qty_for_product_uom

        return qty_for_product

    _columns = {
        'packaging_type_id': fields.many2one('packaging_type', 'Packaging Type',
                                             help='Packaging type to be used with this product.'),
        'packaging_qty_per_parcel': fields.integer('Packaging Quantity',
                                                   help='Integer specifying how many of this product will fit into '
                                                        'one parcel of the selected packaging type, in the UOM of the product.')
    }

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
