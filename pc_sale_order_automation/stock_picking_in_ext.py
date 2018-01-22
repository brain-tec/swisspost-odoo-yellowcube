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
##############################################################################

from openerp.osv import osv, fields
from openerp.tools.translate import _


class stock_picking_in_ext(osv.Model):
    _inherit = 'stock.picking.in'

    def store_backorder_products(self, cr, uid, ids, context=None):
        raise NotImplementedError(_("Method 'store_backorder_products' is not implemented in 'stock.picking.in'."))

    def compute_assignation_for_non_lotted_moves(self, cr, uid, picking_id, context=None):
        raise NotImplementedError(_("Method 'compute_assignation_for_non_lotted_moves' is not implemented in 'stock.picking.in'."))

    def compute_assignation_for_lotted_moves(self, cr, uid, picking_id, context=None):
        raise NotImplementedError(_("Method 'compute_assignation_for_lotted_moves' is not implemented in 'stock.picking.in'."))

    def create_backorder(self, cr, uid, picking_id, instructions_list, context=None):
        raise NotImplementedError(_("Method 'create_backorder' is not implemented in 'stock.picking.in'."))

    def compute_instructions_for_assignation(self, cr, uid, picking_id, context=None):
        raise NotImplementedError(_("Method 'compute_instructions_for_assignation' is not implemented in 'stock.picking.in'."))

    def apply_instructions(self, cr, uid, picking_id, instructions_list, context=None):
        raise NotImplementedError(_("Method 'apply_instructions' is not implemented in 'stock.picking.in'."))

    def compute_num_packages(self, cr, uid, ids, context=None):
        return self.pool.get('stock.picking').compute_num_packages(cr, uid, ids, context=context)

    def assign_packages(self, cr, uid, ids, context=None):
        raise NotImplementedError(_("Method 'assign_packages' is not implemented in 'stock.picking.in'."))

    def _fun_compute_num_packages(self, cr, uid, ids, field_name, args, context=None):
        """ Wrapper over compute_num_packages for the functional field.
        """
        res = {}
        for picking in self.browse(cr, uid, ids, context=context):
            res[picking.id] = picking.compute_num_packages()
        return res

    _columns = {
        'num_packages': fields.function(_fun_compute_num_packages, type="integer", string="Number of Packages"),
    }

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
