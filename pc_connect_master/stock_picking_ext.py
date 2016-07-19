# b-*- encoding: utf-8 -*-
##############################################################################
#
#    Copyright (c) 2014 brain-tec AG (http://www.brain-tec.ch)
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
from utilities.misc import format_exception
from openerp.tools.translate import _
from openerp.tools import DEFAULT_SERVER_DATETIME_FORMAT
import logging
logger = logging.getLogger(__name__)


class stock_picking_ext(osv.Model):
    _inherit = 'stock.picking'

    def is_the_only_picking(self, cr, uid, ids, context=None):
        ''' It returns whether this picking is the only one associated to
            its sale order. It doesn't consider those pickings which are
            cancelled.

            If the picking has no sale.order associated, we consider that
            it is the only picking.

            This method MUST receive just an ID, or a list of just
            one ID, since otherwise just the first element will be used.
        '''
        if context is None:
            context = {}
        if not isinstance(ids, list):
            ids = [ids]

        picking = self.browse(cr, uid, ids[0], context=context)

        is_the_only_picking = True
        if picking.sale_id:
            num_pickings = self.search(cr, uid, [('origin', '=', picking.sale_id.name),
                                                 ('state', '!=', 'cancel'),
                                                 ], context=context, count=True)
            is_the_only_picking = (num_pickings == 1)
        return is_the_only_picking

    def is_last_picking(self, cr, uid, ids, context=None):
        ''' Indicates whether a stock picking is the last one.
            This is the case if the picking is the states
            'assigned', 'done', 'cancel' and there is no other
            stock.picking which is its back-order.

            In the case we don't know for SURE that it's the last
            one, it returns False. Thus, it only returns True when
            we are 100% sure that it's the last one.

            This method MUST receive just an ID, or a list of just
            one ID, since otherwise just the first element will be used.
        '''
        if context is None:
            context = {}
        if not isinstance(ids, list):
            ids = [ids]

        picking = self.browse(cr, uid, ids[0], context=context)
        picking_in_target_state = picking.state in ('assigned', 'done', 'cancel')
        picking_has_backorder = bool(self.search(cr, uid, [('backorder_id', '=', picking.id),
                                                           ], context=context, count=True))
        return picking_in_target_state and (not picking_has_backorder)

    def assign_lots(self, cr, uid, ids, context=None):
        ''' Assigns lots to stock.moves.

            It MUST receive either an ID, or a list of just one ID,
            because it only takes the first one in this case.
        '''
        if context is None:
            context = {}
        if not isinstance(ids, list):
            ids = [ids]

        # Caches the pools.
        stock_move_obj = self.pool.get('stock.move')
        product_uom_obj = self.pool.get('product.uom')

        # Gets the picking we are going to assign the lots to.
        picking = self.browse(cr, uid, ids[0], context=context)

        # Stores the IDs of the stock.moves that are modified/created.
        stock_moves_ids = []

        # Stores any errors found.
        errors = []

        for stock_move in picking.move_lines:

            # The product this stock.move is about.
            product = stock_move.product_id

            # Here we'll store the quantity already moved for the product of this move line,
            # in the unit of measure which is the base unit of measure. E.g. if the product
            # measures its quantity in dozens, this variable will count units.
            quantity_moved = 0

            # A stock move may be split into several ones. We use this variable to know that.
            # So the first time a stock.move is assigned, we store the ID of that stock.move
            # in this variable, thus we can keep track when we inspect more than once a stock.move,
            # which means that we need to split it up into another stock.move.
            first_move_id = None

            # We get the quantity in the base unit of the product, which may be different
            # than the quantity indicated in the stock.move (e.g. it may be 1 dozen which means
            # 12 units of a product). The quantity on the lots is retrieved also on the base UOM of
            # the product. That is why we do it this way: in order to ease the comparison.
            base_uom = product.get_base_uom()
            quantity_to_move = product_uom_obj._compute_qty(cr, uid, stock_move.product_uom.id, stock_move.product_qty, base_uom.id)

            # If we must make use of lots, we use them.
            if product.track_production:
                # Gets the lots available for this product, sorted by its use date.
                # The product may not make use of lots, but if it does then we use them.
                lots = product.get_lots_available()

                if not lots:
                    # Error: we need lots BUT we didn't find any.
                    error_message = _('There were no lots found to fill the stock.picking {0} (ID={1}) '
                                      'associated to the sale.order {2} (ID={3}) for product {4} (ID={5}) '
                                      'that MUST make use of lots').format(picking.name, picking.id,
                                                                           picking.sale_id.name, picking.sale_id.id,
                                                                           product.name, product.id)
                    errors.append(error_message)

                # Starts moving the quantity from the lots.
                lots_iterator = 0
                while (quantity_moved < quantity_to_move) and (lots_iterator < len(lots)):
                    lot = lots[lots_iterator]

                    # Since virtual_available can be negative, we add a 'max' comparison so that we do not have to subtract
                    # a negative quantity from the lot (which could make we deliver abs(number) units if 'number' was negative).
                    quantity_to_substract_from_lot = min(max(0.0, lot.virtual_available_for_sale), quantity_to_move - quantity_moved)

                    if quantity_to_substract_from_lot > 0:

                        # We transform the UOM from the base one that we have used to do the calculus to the same one
                        # which was on the original stock move.
                        new_move_qty = product_uom_obj._compute_qty(cr, uid, base_uom.id, quantity_to_substract_from_lot, stock_move.product_uom.id)

                        # If it's the first move, we reuse the line; if not, we create a new one.
                        if first_move_id is None:  # It's the first move.
                            stock_move.write({'prodlot_id': lot.id,
                                              'product_qty': new_move_qty,
                                              })
                            first_move_id = stock_move.id
                            stock_moves_ids.append(first_move_id)

                        else:  # It's not the first move, thus we create another one.
                            next_move_id = stock_move_obj.copy(cr, uid, first_move_id, {'prodlot_id': lot.id,
                                                                                        'product_qty': new_move_qty,
                                                                                        }, context=context)
                            stock_moves_ids.append(next_move_id)

                    # Prepares for the next iteration, just in case we did not fill all the amount using one lot.
                    quantity_moved += quantity_to_substract_from_lot
                    lots_iterator += 1

                if quantity_moved != quantity_to_move:
                    # Error: quantity on the lots was not enough to fulfill the stock.move.
                    error_message = _('There were not enough quantity on lots to fill the stock.picking {0} (ID={1}) '
                                      'associated to the sale.order {2} (ID={3}) for product {4} (ID={5}) '
                                      'that MUST make use of lots').format(picking.name, picking.id,
                                                                           picking.sale_id.name, picking.sale_id.id,
                                                                           product.name, product.id)
                    errors.append(error_message)

            else:  # if not product.track_production, then we just make use the quantity on hand without paying attention to lots.
                move_qty = product_uom_obj._compute_qty(cr, uid, base_uom.id, quantity_to_move, stock_move.product_uom.id)
                stock_move.write({'product_qty': move_qty,
                                  })
                stock_moves_ids.append(stock_move.id)

        if errors:
            raise orm.except_orm(_('Some errors were found'), '\n'.join(errors))
        else:
            # If no errors happened, i.e. if we didn't raise an exception, then we confirm the moves.
            stock_move_obj.action_confirm(cr, uid, stock_moves_ids, context=context)

        return True

    def set_stock_moves_done(self, cr, uid, ids, context=None):
        ''' Marks all the stock.moves as done.
        '''
        if context is None:
            context = {}
        picking_objs = self.pool.get('stock.picking').browse(cr, uid, ids, context=context)
        for picking_obj in picking_objs:
            stock_move_objs = picking_obj.move_lines
            for stock_move_obj in stock_move_objs:
                stock_move_obj.action_done()
        return True

    def get_file_name(self, cr, uid, ids, context=None):
        ''' Returns the file name for this stock.picking.
        '''
        if context is None:
            context = {}
        if not isinstance(ids, list):
            ids = [ids]
        stock_picking = self.browse(cr, uid, ids[0], context=context)
        file_name = 'delivery_order_{0}_spo{1}.pdf'.format(stock_picking.origin, stock_picking.id)
        return file_name

    def is_printed(self, cr, uid, ids, context=None):
        ''' Returns if we have printed the attachment for this picking.
        '''
        if context is None:
            context = {}
        if not isinstance(ids, list):
            ids = [ids]

        ir_attachment_obj = self.pool.get('ir.attachment')

        picking_id = ids[0]
        file_name = self.get_file_name(cr, uid, ids[0], context=context)

        attachment_count = ir_attachment_obj.search(cr, uid, [('res_model', 'in', ['stock.picking', 'stock.picking.in', 'stock.picking.out']),
                                                              ('res_id', '=', picking_id),
                                                              ('name', '=', file_name),
                                                              ], context=context, count=True)
        return (attachment_count > 0)

    _columns = {
        'do_not_send_to_warehouse': fields.boolean('Do Not Send to Warehouse',
                                                   help='If checked, this picking will not be sent to the warehouse.'),

        #<MOVE> to pc_connect_warehouse? I think it's used only there.
        'carrier_tracking_ref': fields.char('Carrier Tracking Ref', size=256),  # Redefines the field.

        # TODO: Bulk-freight related logic (and this includes packaging) may be moved to pc_connect_master
        # even if it's going to be used only on the automation, since bulk freight in particular is used
        # outside the automation, so in the future packages may be needed outside it also.
        'uses_bulkfreight': fields.boolean('Picking Uses Bulk Freight?'),
    }

    _defaults = {
        'uses_bulkfreight': False,
    }

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
