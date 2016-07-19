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
from openerp.osv import osv, fields
from openerp.tools.translate import _


class stock_picking_in_ext(osv.Model):
    _inherit = 'stock.picking.in'

    def is_last_picking(self, cr, uid, ids, context=None):
        raise NotImplementedError(_("Method 'is_last_picking' is not implemented in 'stock.picking.in'."))

    def assign_lots(self, cr, uid, ids, context=None):
        ''' Assigns lots to stock.moves.
        '''
        raise NotImplementedError(_("Method 'assign_lots' is not implemented in 'stock.picking.in'."))

    def set_stock_moves_done(self, cr, uid, ids, context=None):
        ''' Marks all the stock.moves as done.
        '''
        return self.pool.get('stock.picking').set_stock_moves_done(cr, uid, ids, context=context)

    def get_file_name(self, cr, uid, ids, context=None):
        ''' Returns the file name for this stock.picking.in.
        '''
        return self.pool.get('stock.picking').get_file_name(cr, uid, ids, context=context)

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
