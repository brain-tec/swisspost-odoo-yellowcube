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

from openerp.osv import osv, fields
from utilities import filters


class stock_picking_out_ext(osv.Model):
    _inherit = 'stock.picking.out'

    # BEGIN OF THE CODE WHICH DEFINES THE NEW FILTERS TO ADD TO THE OBJECT.
    def _replace_week_placeholders(self, cr, uid, args, context=None):
        ''' Generates the placeholders for the XML which defines the filter for the current week.
            The code of this filter had to be done partially in Python, thus the reason of this function.
        '''
        return filters._replace_week_placeholders(self, cr, uid, args, context=context)

    def _replace_quarter_placeholders(self, cr, uid, args, context=None):
        ''' Generates the placeholders for the XML which defines the filter for the current quarter.
            The code of this filter had to be done partially in Python, thus the reason of this function.
        '''
        return filters._replace_quarter_placeholders(self, cr, uid, args, context=context)

    def search(self, cr, uid, args, offset=0, limit=None, order=None, context=None, count=False):
        ''' Adds the new filters, added in addition to the ones defined in the XML.
        '''
        return filters.search(self, cr, uid, args, stock_picking_out_ext, offset=offset, limit=limit, order=order, context=context, count=count)

    def read_group(self, cr, uid, domain, fields, groupby, offset=0, limit=None, context=None, orderby=False):
        ''' Adds the posibility to group when using the two new filters, added in addition to the ones defined in the XML.
        '''
        return filters.read_group(self, cr, uid, domain, fields, groupby, stock_picking_out_ext, offset=offset, limit=limit, context=context, orderby=orderby)
    # END OF THE CODE WHICH DEFINES THE NEW FILTERS TO ADD TO THE OBJECT.

    def is_last_picking(self, cr, uid, ids, context=None):
        return self.pool.get('stock.picking').is_last_picking(cr, uid, ids, context)

    def is_first_delivery(self, cr, uid, ids, context=None):
        ''' Returns whether this stock.picking.out is the first or only delivery for a given sale order.
        '''
        if isinstance(ids, list):
            ids = ids[0]
        stock_picking_out = self.browse(cr, uid, ids, context)
        res = (stock_picking_out.move_type == 'one') or ((stock_picking_out.move_type == 'direct') and (not stock_picking_out.backorder_id))
        return bool(res)

    def payment_method_has_epayment(self, cr, uid, ids, context=None):
        ''' Returns whether the payment method has epayment.
        '''
        has_epayment = False

        if isinstance(ids, list):
            ids = ids[0]
        stock_picking_out = self.browse(cr, uid, ids, context)

        sale_order = stock_picking_out.sale_id
        if sale_order:
            has_epayment = sale_order.payment_method_id.epayment

        return bool(has_epayment)

    def equal_addresses_ship_invoice(self, cr, uid, ids, context=None):
        ''' Returns whether the shipping and invoicing addresses are the same for a given sale order.
        '''
        equal_addresses = True

        if isinstance(ids, list):
            ids = ids[0]
        stock_picking_out = self.browse(cr, uid, ids, context)

        sale_order = stock_picking_out.sale_id
        if sale_order:
            equal_addresses = (sale_order.partner_invoice_id.id == sale_order.partner_shipping_id.id)

        return bool(equal_addresses)

    def assign_lots(self, cr, uid, ids, context=None):
        ''' Assigns lots to stock.moves.
        '''
        return self.pool.get('stock.picking').assign_lots(cr, uid, ids, context=context)

    def set_stock_moves_done(self, cr, uid, ids, context=None):
        ''' Marks all the stock.moves as done.
        '''
        return self.pool.get('stock.picking').set_stock_moves_done(cr, uid, ids, context=context)

    def get_file_name(self, cr, uid, ids, context=None):
        ''' Returns the file name for this stock.picking.out.
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
