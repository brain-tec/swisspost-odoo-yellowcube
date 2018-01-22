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

import math
from openerp import tools


class Packaging():

    def __init__(self, delegate_odoo, cr, uid, context, package):
        self.delegate_odoo = delegate_odoo
        self.cr = cr
        self.uid = uid
        self.context = context

        self.package = package  # Object of type stock.tracking.
        self.filling = 0  # 1 means completely filled.

        # Because of floating point operations, we allow
        # for a tolerance when checking for the filling.
        self.filling_tolerance = 1.0 / 10 ** self.delegate_odoo.pool.get('decimal.precision').precision_get(cr, uid, 'Stock Packing')

    def has_same_type(self, stock_move):
        ''' Returns whether a package is compatible with the package needed
            by the stock move by checking if it has the same type.
        '''
        return (self.package.packaging_type_id.id == stock_move.product_id.packaging_type_id.id)

    def is_full(self):
        ''' Returns whether the current package is full or not.
            We allow for a 1% of tolerance because of floating point errors.
        '''
        return (abs(self.filling - 1.0) <= self.filling_tolerance)

    def is_empty(self):
        """ Returns whether a package is empty.
        """
        return self.filling == 0.0

    def has_room(self, stock_move):
        ''' Indicates if there is room for the stock move.
            It computes the relative room which is needed by the stock move to allocate the products.
        '''
        product_uom_obj = self.delegate_odoo.pool.get('product.uom')

        # It converts the quantity to the UOM of the product, since that UOM is the one used
        # to indicate the room on each package.
        qty_uom = product_uom_obj._compute_qty_obj(self.cr, self.uid, stock_move.product_uom, stock_move.product_qty, stock_move.product_id.uom_id)
        ratio_to_occupy = (float(qty_uom) / stock_move.product_id.packaging_qty_per_parcel)

        return (self.filling + ratio_to_occupy) <= 1.0

    def assign_to_stock_move(self, stock_move):
        ''' Assigns a stock.move the current package, and
            increments the ration of occupancy for the package.
        '''
        product_uom_obj = self.delegate_odoo.pool.get('product.uom')

        # Assigns the packaging to this stock move.
        stock_move.write({'tracking_id': self.package.id})

        # Updates the filling for the current package.
        # It converts the quantity to the UOM of the product, since that UOM is the one used
        # to indicate the room on each package.
        qty_uom = product_uom_obj._compute_qty_obj(self.cr, self.uid, stock_move.product_uom, stock_move.product_qty, stock_move.product_id.uom_id)
        ratio_to_occupy = (float(qty_uom) / stock_move.product_id.packaging_qty_per_parcel)
        self.filling += ratio_to_occupy

        return True


class PackagingAllocator():

    def __init__(self, delegate_odoo, cr, uid, context):
        self.delegate_odoo = delegate_odoo
        self.cr = cr
        self.uid = uid
        self.context = context

        # Keeps track of the packages that are already allocated.
        # self.packages stores objects of type Package, which inside
        # reference object of type stock.tracking.
        self.packages = []

    def _find_package_to_use_for_allocation(self, stock_move):
        """ Checks if any package has room for the quantities on this stock.move,
            either completely or partially. Favours packages which are almost empty, so that
            we fill them before we start to use a new package.
        """
        package_to_use = False
        package_to_use_fill_ratio = float('inf')

        for package in self.packages:
            if package.has_same_type(stock_move) and not package.is_full():
                if package.filling < package_to_use_fill_ratio:
                    package_to_use_fill_ratio = package.filling
                    package_to_use = package

        return package_to_use

    def _create_new_package(self, product):
        new_odoo_package = self._create_new_odoo_package(product)
        package = Packaging(self.delegate_odoo, self.cr, self.uid, self.context, new_odoo_package)
        self.packages.append(package)
        return package

    def _create_new_odoo_package(self, product):
        ''' Creates an Odoo package (an object of type stock.tracking) associated
            to a picking and a product, and returns it,
        '''
        package_obj = self.delegate_odoo.pool.get('stock.tracking')

        new_odoo_package_id = package_obj.create(self.cr, self.uid,
                                                 {'packaging_type_id': product.packaging_type_id.id,
                                                  }, self.context)
        new_odoo_package = package_obj.browse(self.cr, self.uid, new_odoo_package_id, self.context)

        return new_odoo_package

    def assign_package(self, stock_move):
        """ Assigns a package to the current stock move. If the stock move has to be split into
            two parts, then it returns a list with the new ID of the new stock move created.

            It first tries to re-use a package that is already existing, but if none of the
            already existing packages has room for the quantity, then it creates as many
            new packages as needed to assign them to the stock.moves. This latter option
            may imply creating new stock moves for the picking (since a stock move may
            have a quantity which is greater than the quantity which fits on a single package).
        """
        product_uom_obj = self.delegate_odoo.pool.get('product.uom')
        stock_move_obj = self.delegate_odoo.pool.get('stock.move')

        # Computes how many packages this stock move needs, as a ratio (floating point) number.
        ratio_of_packages_needed = stock_move.compute_ratio_of_packages()

        # Finds a package to assign to this stock move. The package assigned may not be enough
        # to fulfill the whole stock move. If we don't find a package to at least assign a part
        # the stock move to it, then we create a new package.
        package = self._find_package_to_use_for_allocation(stock_move)
        if not package:
            package = self._create_new_package(stock_move.product_id)

        # Now, variable 'package' points to a package which either: is partially filled so that we can put
        # at least a portion of the stock move, or is completely empty (because it's new).
        # Thus, four cases are possible:
        #   1) The package is partially filled and the stock move fits completely.
        #   2) The package is partially filled and only a portion of the stock moves fits.
        #   3) The package is empty and the stock move fits completely.
        #   4) The package is empty and only a portion of the stock move fits.
        if not package.is_empty():

            # This is Case 1, so no new stock move is needed: all the goods in the move are assigned to the package.
            if ratio_of_packages_needed <= (1.0 - package.filling):
                new_stock_move_id = False

            # This is Case 2, so we need to split the stock move.
            else:
                # We compute the quantity in the UOM of the product, since the limit per package is defined in that UOM.
                qty_to_assign = product_uom_obj._compute_qty_obj(self.cr, self.uid, stock_move.product_uom, stock_move.product_qty, stock_move.product_id.uom_id)
                # We compute the amount which corresponds to the available free space in the package.
                qty_to_assign_to_this_stock_move = stock_move.product_id.packaging_qty_per_parcel * (1.0 - package.filling)
                qty_to_assign_to_this_stock_move = tools.float_round(qty_to_assign_to_this_stock_move, precision_rounding=stock_move.product_id.uom_id.rounding)
                # We fill the empty package completely, and the remaining quantity is left in a new stock.move.
                new_stock_move_id = stock_move.split_into(qty_to_assign_to_this_stock_move)
        else:

            # This is Case 3, so no new stock move is needed: all the goods in the move are assigned to the package.
            if ratio_of_packages_needed <= 1.0:
                new_stock_move_id = False

            # This is Case 4, so a new stock move is needed.
            else:
                # We fill the empty package completely, and the remaining quantity is left in a new stock.move.
                new_stock_move_id = stock_move.split_into(stock_move.product_id.packaging_qty_per_parcel)

        if new_stock_move_id:
            new_stock_move_ids = [new_stock_move_id]
        else:
            new_stock_move_ids = []

        # We assign the current package to the stock move.
        stock_move = stock_move_obj.browse(self.cr, self.uid, stock_move.id, self.context)  # We do a re-browse because of the cache.
        package.assign_to_stock_move(stock_move)

        return new_stock_move_ids

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
