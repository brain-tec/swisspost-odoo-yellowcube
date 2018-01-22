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
from openerp.tools.translate import _
from PackagingAllocator import PackagingAllocator
from collections import deque
import math
from StockMoveInstruction import StockMoveInstruction


class stock_picking_ext(osv.Model):
    _inherit = 'stock.picking'

    def _prepare_invoice_line(self, cr, uid, group, picking, move_line,
                              invoice_id, invoice_vals, context=None):
        """ Overridden so that it keeps track of the originating
            move.line that generated the account.invoice.line.
        """
        ret = super(stock_picking_ext, self)._prepare_invoice_line(
            cr, uid, group, picking, move_line,
            invoice_id, invoice_vals, context=context)

        ret.update({'orig_stock_move_id': move_line.id})

        return ret

    def compute_assignation_for_non_lotted_moves(self, cr, uid, picking_id, context=None):
        """ Returns the lists of instructions (named tuples of type StockMoveInstructions)
            to know how to assign the lotted moves in a direct assignment schema.
        """
        if context is None:
            context = {}
        if type(picking_id) is list:
            picking_id = picking_id[0]

        # Caches the pools.
        stock_move_obj = self.pool.get('stock.move')
        product_uom_obj = self.pool.get('product.uom')

        # The list of instructions to create.
        instructions = []

        # Keeps track of the quantity assigned from the different lots.
        qty_on_sale_assigned_per_product = {}

        # We only consider those moves that are not lotted.
        stock_moves_ids = stock_move_obj.search(cr, uid, [('picking_id', '=', picking_id),
                                                          ('product_id.track_production', '=', False),
                                                          ('product_id.type', 'in', ('product', 'consu')),
                                                          ], context=context)
        for stock_move in stock_move_obj.browse(cr, uid, stock_moves_ids, context):

            # The product this stock.move is about.
            product = stock_move.product_id

            # Gets the quantity of the product in the UOM of the product, to ease the comparisons.
            qty_required = product_uom_obj._compute_qty_obj(cr, uid, stock_move.product_uom, stock_move.product_qty, product.uom_id, context=context)

            # Here we store the quantities that we are assigning per product.
            if product.id not in qty_on_sale_assigned_per_product:
                qty_on_sale_assigned_per_product[product.id] = 0

            total_amount_assigned = 0  # This measure is also in the UOM of the product.
            qty_available = product.qty_available - product.qty_on_assigned_moves - qty_on_sale_assigned_per_product[product.id]

            if qty_available <= 0:
                total_amount_assigned = 0
            elif qty_available >= qty_required:
                total_amount_assigned = qty_required
            elif qty_available < qty_required:
                total_amount_assigned = qty_available

            qty_on_sale_assigned_per_product[product.id] += total_amount_assigned

            if product.type == 'consu':
                # Consumables are delivered always.
                instructions.append(StockMoveInstruction('none', 'deliver',
                                                         stock_move.id, False))

            elif total_amount_assigned == 0:
                instructions.append(StockMoveInstruction('none', 'wait', stock_move.id, False))

            elif total_amount_assigned < qty_required:
                # stock.move has to be split into two: one with the goods that we can deliver,
                # and one with the goods we are still waiting for.
                #   The unit of measure is the same than in the original picking, thus we transform
                # from the product's UOM that we have been using to do the calculus to the unit of measure
                # which was indicated in the original stock.move.
                new_move_qty = product_uom_obj._compute_qty_obj(cr, uid, product.uom_id, total_amount_assigned, stock_move.product_uom, context=context)
                instructions.append(StockMoveInstruction('copy', 'deliver', stock_move.id, {'product_qty': new_move_qty}))

                original_move_qty = product_uom_obj._compute_qty_obj(cr, uid, product.uom_id, (qty_required - total_amount_assigned), stock_move.product_uom, context=context)
                instructions.append(StockMoveInstruction('update', 'wait', stock_move.id, {'product_qty': original_move_qty}))

            else:  # total_amount_assigned >= qty_required:  # Actually is == instead of >= because we adjust the quantity.
                # stock.move can be fulfilled entirely.
                instructions.append(StockMoveInstruction('none', 'deliver', stock_move.id, False))

        return instructions

    def compute_assignation_for_lotted_moves(self, cr, uid, picking_id, context=None):
        """ Returns the lists of instructions (named tuples of type StockMoveInstructions)
            to know how to assign the non-lotted moves in a direct assignment schema.
        """
        if context is None:
            context = {}
        if type(picking_id) is list:
            picking_id = picking_id[0]

        # Caches the pools.
        stock_move_obj = self.pool.get('stock.move')
        product_uom_obj = self.pool.get('product.uom')

        instructions = []

        # Consumable products are delivered always.
        consumable_stock_moves_ids = stock_move_obj.search(
            cr, uid, [('picking_id', '=', picking_id),
                      ('product_id.track_production', '=', True),
                      ('product_id.type', '=', 'consu'),
                      ], context=context)
        for stock_move in stock_move_obj.browse(cr, uid,
                                                consumable_stock_moves_ids,
                                                context):
            instructions.append(StockMoveInstruction('none', 'deliver',
                                                     stock_move.id, False))

        # From the regular products (not consumables nor services)
        # we only consider those moves that are lotted.
        stock_moves_ids = stock_move_obj.search(cr, uid, [('picking_id', '=', picking_id),
                                                          ('product_id.track_production', '=', True),
                                                          ('product_id.type', '=', 'product'),
                                                          ], context=context)
        for stock_move in stock_move_obj.browse(cr, uid, stock_moves_ids, context):

            # The product this stock.move is about.
            product = stock_move.product_id

            # Here we'll store the quantity already moved for the product of this move line,
            # in the unit of measure which is the base UOM which is marked as the reference.
            quantity_moved = 0

            # A stock move may be split into several ones. We use this variable to know that.
            # So the first time a stock.move is assigned, we store the ID of that stock.move
            # in this variable, thus we can keep track when we inspect more than once a stock.move,
            # which means that we need to split it up into another stock.move.
            first_move_id = None

            # We get the quantity in the UOM which is marked as 'reference', which may be different
            # than the quantity indicated in the stock.move.
            base_uom = product.get_base_uom()
            quantity_to_move = product_uom_obj._compute_qty_obj(cr, uid, stock_move.product_uom, stock_move.product_qty, base_uom, context=context)

            # Gets the lots available for this product.
            # The lots are returned as a list, sorted by eligibility criteria (take first those at the beginning).
            lots = product.get_lots_available()

            # Starts moving the quantity from the lots.
            lots_iterator = 0
            while (quantity_moved < quantity_to_move) and (lots_iterator < len(lots)):
                lot = lots[lots_iterator]

                # Since virtual_available can be negative, we add a 'max' comparison so that we do not have to subtract
                # a negative quantity from the lot (which could make we deliver abs(number) units if 'number' was negative).
                quantity_to_substract_from_lot = min(max(0.0, lot.virtual_available_for_sale),
                                                     quantity_to_move - quantity_moved)

                if quantity_to_substract_from_lot > 0:

                    # We transform the UOM from the base one that we have used to do the calculus to the same one
                    # which was on the original stock move.
                    new_move_qty = product_uom_obj._compute_qty_obj(cr, uid, base_uom, quantity_to_substract_from_lot, stock_move.product_uom, context=context)
                    stock_move_new_values = {
                        'prodlot_id': lot.id,
                        'product_qty': new_move_qty,
                    }

                    # If it's the first move, we reuse the line; if not, we create a new one.
                    if first_move_id is None:  # It's the first move.
                        instructions.append(StockMoveInstruction('update', 'deliver', stock_move.id, stock_move_new_values))
                        #stock_move.write(stock_move_new_values)
                        first_move_id = stock_move.id
                        #stock_moves_lotted_ready_ids.append(first_move_id)

                    else:  # It's not the first move, thus we create another one.
                        instructions.append(StockMoveInstruction('copy', 'deliver', stock_move.id, stock_move_new_values))
                        #new_move_id = stock_move_obj.copy(cr, uid, first_move_id, stock_move_new_values, context=context)
                        #stock_moves_lotted_ready_ids.append(new_move_id)

                # Prepares for the next iteration, just in case we did not fill all the amount using one lot.
                quantity_moved += quantity_to_substract_from_lot
                lots_iterator += 1

            if quantity_moved != quantity_to_move:
                # The quantity available on the lots was not enough to fulfill the quantity that was in the original move.
                if first_move_id is None:  # We couldn't find not even a portion of the original first move.
                    instructions.append(StockMoveInstruction('none', 'wait', stock_move.id, False))
                    #stock_moves_lotted_not_ready_ids.append(stock_move.id)
                else:
                    new_move_qty = product_uom_obj._compute_qty_obj(cr, uid, base_uom, quantity_to_move - quantity_moved, stock_move.product_uom, context=context)
                    instructions.append(StockMoveInstruction('copy', 'wait', first_move_id, {'product_qty': new_move_qty}))
                    #new_move_id = stock_move_obj.copy(cr, uid, first_move_id, {'product_qty': new_move_qty}, context=context)
                    #stock_moves_lotted_not_ready_ids.append(new_move_id)

        return instructions

    def apply_instructions(self, cr, uid, picking_id, instructions_list, context=None):
        """ Applies the instructions over a picking.
                The call of this method assumes that we are sure that we can actually delivery all the order.
        """
        if context is None:
            context = {}
        if type(picking_id) is list:
            picking_id = picking_id[0]

        stock_move_obj = self.pool.get('stock.move')

        # Now we apply each instruction over the picking.
        for instruction in instructions_list:

            if instruction.command == 'copy':
                move_id = stock_move_obj.copy(cr, uid, instruction.stock_move_id, instruction.values)
                stock_move_obj.write(cr, uid, move_id, {'picking_id': picking_id}, context=context)
            elif instruction.command == 'update':
                stock_move_obj.write(cr, uid, instruction.stock_move_id, instruction.values)
            else:  # if instruction.command == 'none':
                pass

        return True

    def create_backorder(self, cr, uid, picking_id, instructions_list, context=None):
        """ Creates a backorder from the picking.
            The moves which are ready to be delivered are moved to a new picking, while the ones which are
            not yet available are kept in the original picking, (which in v7 is the one called 'backorder').
                The creation of the backorder is done by following in order the instructions provided,
            of type StockMoveInstruction.
                The call of this method assumes that we are sure that we can actually create a back-order.
        """
        if context is None:
            context = {}
        if type(picking_id) is list:
            picking_id = picking_id[0]

        stock_move_obj = self.pool.get('stock.move')
        sequence_obj = self.pool.get('ir.sequence')

        # Caches the original picking (the one that in v7 is called back-order).
        original_picking = self.browse(cr, uid, picking_id, context=context)

        # Creates the new picking: The one that will be actually delivered.
        new_picking_name = sequence_obj.get(cr, uid, 'stock.picking.{0}'.format(original_picking.type))
        new_picking_id = self.copy(cr, uid, original_picking.id, {'name': new_picking_name,
                                                                  'move_lines': False,
                                                                  'state': 'draft',
                                                                  })

        # The back-order is (in v7) the picking which has the remaining stock moves that could not be assigned yet.
        original_picking.write({'backorder_id': new_picking_id})

        # Now we assign each stock move to its corresponding picking.
        for instruction in instructions_list:

            if instruction.command == 'copy':
                move_id = stock_move_obj.copy(cr, uid, instruction.stock_move_id, instruction.values)
                target_move_id = move_id
            elif instruction.command == 'update':
                stock_move_obj.write(cr, uid, instruction.stock_move_id, instruction.values)
                target_move_id = instruction.stock_move_id
            else:  # if instruction.command == 'none':
                target_move_id = instruction.stock_move_id

            if instruction.move_option == 'wait':
                stock_move_obj.write(cr, uid, target_move_id, {'picking_id': original_picking.id}, context=context)
            else:  # if instruction.move_option == 'deliver':
                stock_move_obj.write(cr, uid, target_move_id, {'picking_id': new_picking_id}, context=context)

        new_picking = self.browse(cr, uid, new_picking_id, context=context)
        return new_picking, original_picking

    def compute_instructions_for_assignation(self, cr, uid, picking_id, context=None):
        """ Implements the assignation direct of a picking, which assigns all the items that can
            be assigned, and the ones remaining are put apart in a different picking that will
            be tried to filled in later.
        """
        if context is None:
            context = {}
        if type(picking_id) is list:
            picking_id = picking_id[0]

        picking = self.browse(cr, uid, picking_id, context=context)

        instructions_for_lotted = picking.compute_assignation_for_lotted_moves()
        instructions_for_non_lotted = picking.compute_assignation_for_non_lotted_moves()
        return instructions_for_lotted + instructions_for_non_lotted

    def _prepare_shipping_invoice_line(self, cr, uid, picking, invoice, context=None):
        """ (What this method does in its original implementation is to take the shipping
            and create an invoice line with it).
                In our case, the shop adds a sale.order line which is the shipping product,
            thus we don't want a new invoice line to be added for this kind of product.
        """
        if context is None:
            context = {}

        if context.get('do_not_generate_shipping_invoice_line', False):
            res = False
        else:
            res = super(stock_picking_ext, self)._prepare_shipping_invoice_line(cr, uid, picking, invoice, context=context)
        return res

    def compute_num_packages(self, cr, uid, ids, context=None):
        ''' We compute the number of packages that are needed to pack the whole picking.

            This requires all products to define a packaging type and
            the amount which fits in each pack. If any of the products of the picking
            does not meet this condition, the method raises.

            Returns an integer indicated the number of packages required.

            MUST be called over just one ID, or a list of IDs of just one element
            (otherwise just the first ID of the list will be considered).
        '''
        if context is None:
            context = {}
        if type(ids) is not list:
            ids = [ids]

        product_uom_obj = self.pool.get('product.uom')

        picking = self.browse(cr, uid, ids[0], context=context)

        # Dictionary storing the number of packages needed per package type.
        # Key: The package type *object*, Value: The number of packages of that type.
        packages = {}

        for stock_move in picking.move_lines:
            product = stock_move.product_id
            packaging_type = product.packaging_type_id
            packaging_qty_per_parcel = product.packaging_qty_per_parcel

            if (not packaging_type) or (not packaging_qty_per_parcel):
                raise orm.except_orm(_('Missing Data on Product Regarding Packaging'),
                                     _('Method compute_num_packages was called over product with ID={0} '
                                       'but either field packaging_type or packaging_qty_per_parcel was not set.'). format(product.id))

            if packaging_type not in packages:
                packages[packaging_type] = 0

            # Computes the quantity in the UOM of the product, because packaging_qty_per_parcel
            # is always set in the UOM of the product.
            qty_uom = product_uom_obj._compute_qty(cr, uid, stock_move.product_uom.id, stock_move.product_qty, product.uom_id.id)
            packages[packaging_type] += (float(qty_uom) / product.packaging_qty_per_parcel)

        stock_packing_max_precision = 1.0 / 10 ** self.pool.get('decimal.precision').precision_get(cr, uid, 'Stock Packing')
        num_packages_needed = 0
        for package_type in packages:
            # We truncate the number of decimals to reduce the chance of having floating point issues.
            # For instance a picking with quantities 1, 1, 4, 1, 1, 1 gives a total amount
            # of packages of 3.0000000000000004, while it has to be 3 of course.
            # This should be enough to deal with this kind of errors.
            qty_for_current_package_type = packages[package_type]
            if abs(math.floor(qty_for_current_package_type) - qty_for_current_package_type) < stock_packing_max_precision:
                # If e.g. floor(3.0000000000000004) - 3.0000000000000004 < 0.001, then we don't need an extra package, otherwise yes.
                qty_for_current_package_type = int(qty_for_current_package_type)
            else:
                qty_for_current_package_type = int(math.ceil(qty_for_current_package_type))
            num_packages_needed += qty_for_current_package_type

        return num_packages_needed

    def _fun_compute_num_packages(self, cr, uid, ids, field_name, args, context=None):
        """ Wrapper over compute_num_packages for the functional field.
        """
        packaging_is_enabled = self.pool.get('configuration.data').get(cr, uid, None, context=context).packaging_enabled
        res = {}
        if packaging_is_enabled:
            for picking in self.browse(cr, uid, ids, context=context):
                res[picking.id] = picking.compute_num_packages()
        else:
            res = dict.fromkeys(ids, 0)
        return res

    def assign_packages(self, cr, uid, ids, context=None):
        """ Assigns packages to all the lines of stock move, and splits the lines into
            several ones if more than one package is required.

            MUST be called over just one ID, or a list of IDs of just one element
            (otherwise just the first ID of the list will be considered).
        """
        if context is None:
            context = {}
        if type(ids) is not list:
            ids = [ids]

        stock_move_obj = self.pool.get('stock.move')

        picking = self.browse(cr, uid, ids[0], context=context)

        # We use a Python object to encapsulate the logic behind the
        # assignment of the packages.
        packaging_allocator = PackagingAllocator(self, cr, uid, context)

        # While we are allocating the stock moves into packages it may happen that
        # one move splits into several ones because of a small size of the packages.
        # To avoid considering more than one time stock moves, we append new stock
        # moves to the end of the list, in a FIFO structure: a deque.
        move_line_ids = deque([move_line.id for move_line in picking.move_lines])

        while len(move_line_ids) > 0:
            current_stock_move_id = move_line_ids.popleft()
            current_stock_move = stock_move_obj.browse(cr, uid, current_stock_move_id, context=context)

            product = current_stock_move.product_id
            packaging_type = product.packaging_type_id
            packaging_qty_per_parcel = product.packaging_qty_per_parcel
            if (not packaging_type) or (not packaging_qty_per_parcel):
                raise orm.orm_exception(_('Missing Data on Product Regarding Packaging'),
                                        _('Method compute_num_packages was called over product with ID={0} '
                                          'but either field packaging_type or packaging_qty_per_parcel was not set.'). format(product.id))

            # Assigns a package to the current stock move. If the stock move has to be split into
            # two parts, then it returns a list with the new ID of the new stock move created.
            new_stock_move_ids = packaging_allocator.assign_package(current_stock_move)
            move_line_ids.extend(new_stock_move_ids)

        return True

    def store_backorder_products(self, cr, uid, ids, context=None):
        """ When executed, saves the products which are associated to any stock move which is in state
            waiting or confirmed, belonging to any picking different than the current one and which comes
            from any sale order associated to the current picking.
        """
        if context is None:
            context = {}
        if type(ids) is not list:
            ids = [ids]

        stock_move_obj = self.pool.get('stock.move')
        product_pending_obj = self.pool.get('pc_sale_order_automation.product_pending')

        for picking in self.browse(cr, uid, ids, context=context):
            product_pending_ids = []
            stock_move_ids = stock_move_obj.search(cr, uid, [('picking_id', 'in', [other_picking.id for other_picking in picking.sale_id.picking_ids if other_picking.id != picking.id]),
                                                             ('state', 'in', ('waiting', 'confirmed')),
                                                             ], context=context)
            for stock_move in stock_move_obj.browse(cr, uid, stock_move_ids, context=context):
                product_pending_new_id = product_pending_obj.create(cr, uid, {'product_id': stock_move.product_id.id,
                                                                              'product_uom_qty': stock_move.product_qty,
                                                                              'product_uom': stock_move.product_uom.id,
                                                                              }, context=context)
                product_pending_ids.append(product_pending_new_id)

                picking.write({'backorder_items_for_pickings_ids': [(6, False, product_pending_ids)]})

    _columns = {
        'num_packages': fields.function(_fun_compute_num_packages, type="integer", string="Number of Packages"),
    }

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
