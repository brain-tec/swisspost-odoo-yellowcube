# b-*- encoding: utf-8 -*-
##############################################################################
#
#    Copyright (c) 2014 brain-tec AG (http://www.braintec-group.com)
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

    def set_mandatory_additional_shipping_codes(self, cr, uid, ids,
                                                context=None):
        return self.pool.get('stock.picking').\
            set_mandatory_additional_shipping_codes(
            cr, uid, ids, context=context)

    def get_route(self, cr, uid, ids, context=None):
        return self.pool.get('stock.picking').get_route(cr, uid, ids, context)

    def is_last_picking(self, cr, uid, ids, context=None):
        return self.pool.get('stock.picking').is_last_picking(cr, uid, ids, context)

    def is_first_delivery(self, cr, uid, ids, context=None):
        return self.pool.get('stock.picking').is_first_delivery(cr, uid, ids, context)

    def payment_method_has_epayment(self, cr, uid, ids, context=None):
        ''' Returns whether the payment method has epayment.
        '''
        has_epayment = False

        if type(ids) is list:
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

        if type(ids) is list:
            ids = ids[0]
        stock_picking_out = self.browse(cr, uid, ids, context)

        sale_order = stock_picking_out.sale_id
        if sale_order:
            equal_addresses = (sale_order.partner_invoice_id.id == sale_order.partner_shipping_id.id)

        return bool(equal_addresses)

    def set_stock_moves_done(self, cr, uid, ids, context=None):
        ''' Marks all the stock.moves as done.
        '''
        return self.pool.get('stock.picking').set_stock_moves_done(cr, uid, ids, context=context)

    def get_file_name(self, cr, uid, ids, context=None):
        ''' Returns the file name for this stock.picking.out.
        '''
        return self.pool.get('stock.picking').get_file_name(cr, uid, ids, context=context)

    def get_ready_for_export(self, cr, uid, ids, name, args, context=None):
        return self.pool.get('stock.picking').get_ready_for_export(cr, uid, ids, name, args, context)

    def map_partials_to_picking_in(self, cr, uid, ids, picking_in_id, partials,
                                      context=None):
        """ Given a partials structure (the data that the method do_partial()
            expects to receive) from a picking.out, it does the mapping
            between those partials and the ones for the given picking.in.
        """
        if context is None:
            context = {}

        move_obj = self.pool.get('stock.move')

        mapped_partials = {}
        for partial_key, partial_values in partials.iteritems():
            picking_out_move_id = int(partial_key.split('move')[-1])

            # We search a stock.move that has as the move_dest_id the one
            # for the picking.out. This way we know the move from the
            # picking.in was originated by the move by the picking.out
            picking_in_move_ids = move_obj.search(
                cr, uid, [('move_dest_id', '=', picking_out_move_id)],
                limit=1, context=context)

            if picking_in_move_ids:
                # We found at least one move that matches, so we pick one and
                # do the mapping, just copying the original values but with a
                # new key to point to the new stock move from the picking.in.
                mapped_partials['move{0}'.format(picking_in_move_ids[0])] = \
                    partial_values.copy()

            else:
                # If we didn't find a match, that means that the move
                # has not a match yet.
                pass

        return mapped_partials

    _columns = {
        'do_not_send_to_warehouse': fields.boolean('Do Not Send to Warehouse',
                                                   help='If checked, this picking will not be sent to the warehouse.'),

        #<MOVE> to pc_connect_warehouse? I think it's used only there.
        'carrier_tracking_ref': fields.char('Carrier Tracking Ref', size=256),  # Redefines the field.

        # TODO: Bulk-freight related logic (and this includes packaging) may be moved to pc_connect_master
        # even if it's going to be used only on the automation, since bulk freight in particular is used
        # outside the automation, so in the future packages may be needed outside it also.
        'uses_bulkfreight': fields.boolean('Picking Uses Bulk Freight?'),

        'ready_for_export': fields.function(get_ready_for_export,
                                            type='boolean',
                                            string='Ready for Export?',
                                            help='Indicates whether the stock.picking is ready for export to the warehouse.'),
        'ready_for_export_manual': fields.boolean('Manual Ready for Export?',
                                                  help="If checked, it overrides the field 'Ready for Export?' and marks the picking as being ready for export."),

        'create_date': fields.datetime('Create Date', help="Redefined just to be able to use it from the model."),

        'backorder_items_for_pickings_ids': fields.many2many('pc_sale_order_automation.product_pending',
                                                             rel='backorder_items_for_pickings',
                                                             id1='picking_id', id2='product_pending_id'),

        'yc_mandatory_additional_shipping': fields.char(
            'Mandatory additional services',
            help='These mandatory additional service codes must '
                 'be added to the WAB when submitting it to YellowCube.'),
    }

    _defaults = {
        'uses_bulkfreight': False,
        'ready_for_export': False,
        'ready_for_export_manual': False,
    }

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
