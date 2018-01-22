# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
# b-*- encoding: utf-8 -*-
##############################################################################
#
#    Copyright (c) 2016 brain-tec AG (http://www.braintec-group.com)
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
###############################################################################

from osv import osv, fields
from openerp.addons.pc_generics import generics
from tools.translate import _


@generics.has_mako_header()
class stock_picking_ext(osv.osv):
    _inherit = 'stock.picking'

    def get_partials(self, cr, uid, ids, context=None):
        ''' Returns a dictionary of partial moves for a single stock.picking
        '''
        if context is None:
            context = {}
        if type(ids) is not list:
            ids = [ids]

        partials = {}

        stock_picking = self.browse(cr, uid, ids[0], context)
        for move_line in stock_picking.move_lines:
            partials['move{0}'.format(move_line.id)] = {
                'prodlot_id': move_line.prodlot_id.id,
                'product_id': move_line.product_id.id,
                'product_uom': move_line.product_uom.id,
                'product_qty': move_line.product_qty,
            }

        return partials

    def __get_products(self, cr, uid, ids, context=None):
        ''' Gets a dictionary of the *different* products that are
            in the stock pickings which are received in the 'objects'
            argument. The key is the product's ID, and the content is
            a dictionary containing:
              - default_code: the default code of the product.
              - name: the name of the product.
              - uoms: a dictionary, with key the UOM's ID, and
                      the content being:
                          * product_qty: The quantity of this product
                                         for this UOM.
        '''
        if context is None:
            context = {}
        if type(ids) is not list:
            ids = [ids]

        products = {}
        for stock_picking_out in self.browse(cr, uid, ids, context=context):
            for move_line in stock_picking_out.move_lines:
                product = move_line.product_id
                if product.id not in products:
                    products[product.id] = {'default_code': product.default_code,
                                            'name': product.name,
                                            'uoms': {},
                                            }
                product_uom_id = move_line.product_uom.id
                if product_uom_id not in products[product.id]['uoms']:
                    products[product.id]['uoms'][product_uom_id] = {'product_qty': 0.0}
                products[product.id]['uoms'][product_uom_id]['product_qty'] += move_line.product_qty

        return products

    def get_product_lines(self, cr, uid, ids, context=None):
        ''' Returns a list of 3-tuples, each tuple being of type
            (product's ID, UOM's ID, quantity),
            summarising the information present in all the stock pickings
            the ID of which are received as arguments.
        '''
        if context is None:
            context = {}

        products_lines = []

        products = self.__get_products(cr, uid, ids, context)
        for product_id in products:
            product = products[product_id]
            for uom in product['uoms']:
                quantity = product['uoms'][uom]['product_qty']
                products_lines.append((product_id, uom, quantity))

        return products_lines

    _columns = {
        'connect_file_id': fields.many2one('stock.connect.file', 'Related stock connect file'),
    }

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
