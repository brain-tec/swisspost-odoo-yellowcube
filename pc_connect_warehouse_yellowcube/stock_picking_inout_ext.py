# b-*- encoding: utf-8 -*-
##############################################################################
#
#    Copyright (c) 2015 brain-tec AG (http://www.braintec-group.com)
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
from openerp.release import version_info
assert version_info[0] <= 7, "This file can only be loaded on version 7 or lower."

from openerp.osv import osv, fields
from openerp.tools.translate import _
from stock_picking_ext import RETURN_REASON_CODES


class stock_picking_in_ext(osv.Model):
    _inherit = 'stock.picking.in'

    def create(self, cr, uid, vals, context=None):
        picking_id = super(stock_picking_in_ext, self).create(
            cr, uid, vals, context=context)

        if 'carrier_id' in vals:
            self.set_mandatory_additional_shipping_codes(cr, uid, picking_id,
                                                         context=context)

        return picking_id

    def write(self, cr, uid, ids, vals, context=None):
        ret = super(stock_picking_in_ext, self).write(
            cr, uid, ids, vals, context=None)

        if 'carrier_id' in vals:
            self.set_mandatory_additional_shipping_codes(cr, uid, ids,
                                                         context=context)

        return ret

    def split_lot(self, cr, uid, ids, partial, yc_pos_no, context=None):
        """ Given the partials computed (the same structure that expects
            the method do_partial) and a YC PosNo for a stock.move,
            it splits it.
        """
        if context is None:
            context = {}
        if type(ids) is not list:
            ids = [ids]

        # Returns a dictionary with the key being the picking's ID, and
        # the value a list of IDs for the new stock.moves created.
        res = {}

        move_obj = self.pool.get('stock.move')
        lot_obj = self.pool.get('stock.production.lot')

        lot = lot_obj.browse(cr, uid, partial['prodlot_id'], context=context)

        for picking in self.browse(cr, uid, ids, context=context):

            res[picking.id] = []

            move_lot_ids = move_obj.search(cr, uid, [
                ('product_id', '=', partial['product_id']),
                ('yc_posno', '=', yc_pos_no),
                ('picking_id', '=', picking.id),
                ('prodlot_id', '=', lot.id),
            ], context=context, limit=1)

            if not move_lot_ids:
                # If the lot doesn't exist, the splitting has to be made.
                # Chooses the move to split, Ms, choosing it to be the one
                # with the largest pending quantity to fulfill.
                M = []
                for move in picking.move_lines:
                    if move.product_id.id == partial['product_id'] and \
                       move.yc_posno == yc_pos_no:
                        M.append((move.product_qty - move.yc_qty_done,
                                  move.product_qty,
                                  move.prodlot_id.id,
                                  move))
                # Take the move ms that has the biggest difference
                # product_qty - yc_qty_done. If all are equal then the one
                # with the biggest product_qty. If all are equal, then any.
                M.sort(reverse=True)
                target_move = M[0][-1]

                # Determines the amount to split and does the splitting.
                amount = max(1, min(
                    partial['product_qty'],
                    target_move.product_qty - target_move.yc_qty_done))
                new_move_ids = target_move.split_move_by_lot(lot, amount)

                # We now have a stock.move with the new lot created.
                move_lot_ids = new_move_ids[target_move.id]
                if move_lot_ids:
                    res[picking.id].append(move_lot_ids[0])
                else:
                    # If we didn't got a splitted move, it's because
                    # the original move is all that we need.
                    move_lot_ids = [target_move.id]

            # Increment the qty done in the splitted move.
            previous_yc_qty_done = move_obj.read(
                cr, uid, move_lot_ids, ['yc_qty_done'],
                context=context)[0]['yc_qty_done']
            move_obj.write(cr, uid, move_lot_ids[0], {
                'yc_qty_done': previous_yc_qty_done + partial['product_qty'],
            }, context=context)

            # Re-browse is needed because of the (possibly)
            # new stock.move created.
            picking = self.browse(cr, uid, picking.id, context=context)

            # Now we have to balance the quantities in the other move.
            # We sort M ascending by product's lot.
            M = []
            for move in picking.move_lines:
                if move.yc_posno == yc_pos_no:
                    M.append((move.prodlot_id and move.prodlot_id.id or False,
                              move.product_qty - move.yc_qty_done,
                              move.product_qty,
                              move))
            M.sort()

            # First, collects all the positive quantities on the first line.
            move_0 = M[0][-1]
            for move_idx in xrange(1, len(M)):
                move_m = M[move_idx][-1]
                delta = \
                    move_m.product_qty - move_m.yc_qty_done
                if delta > 0:
                    move_obj.write(cr, uid, move_0.id, {
                        'product_qty': move_0.product_qty + delta,
                        'product_uos_qty': move_0.product_qty + delta,
                    }, context=context)
                    move_obj.write(cr, uid, move_m.id, {
                        'product_qty': move_m.product_qty - delta,
                        'product_uos_qty': move_m.product_qty - delta,
                    }, context=context)

            # Then, 'gives donations, but not more than we have', from the
            # first line.
            for move_idx in xrange(1, len(M)):
                move_m = M[move_idx][-1]
                delta = min(
                    move_m.yc_qty_done - move_m.product_qty,
                    move_0.product_qty - move_0.yc_qty_done)
                if delta > 0:
                    move_obj.write(cr, uid, move_0.id, {
                        'product_qty': move_0.product_qty - delta,
                        'product_uos_qty': move_0.product_qty - delta,
                    }, context=context)
                    move_obj.write(cr, uid, move_m.id, {
                        'product_qty': move_m.product_qty + delta,
                        'product_uos_qty': move_m.product_qty + delta,
                    }, context=context)

        return res

    def store_tracking_link(self, cr, uid, ids, context=None):
        raise Warning("store_tracking_link can not be called "
                      "over stock.picking.in.")

    def send_tracking_email_to_client(self, cr, uid, ids, context=None):
        raise Warning("send_tracking_email_to_client can not be called "
                      "over stock.picking.in.")

    def get_filename_for_wab(self, cr, uid, ids, context=None):
        raise Warning("get_filename_for_wab can not be called over stock.picking.in.")

    def get_attachment_wab(self, cr, uid, ids, context=None):
        raise Warning("get_attachment_wab can not be called over stock.picking.in.")

    def get_customer_order_no(self, cr, uid, ids, field=None, arg=None, context=None):
        return self.pool['stock.picking'].get_customer_order_no(cr, uid, ids, field=field, arg=arg, context=context)

    def wrapper_do_partial(self, cr, uid, ids, partial_datas, context=None):
        return self.pool['stock.picking'].wrapper_do_partial(
            cr, uid, ids, partial_datas, context=context)

    def _create_invoice_on_wba(self, cr, uid, ids, context=None):
        """ Instead of creating an invoice every time a WBA is received,
            it just creates one invoice in draft and keeps updating it.
            If no invoice in state draft is associated to the purchase, then
            a new one is created so that it's updated in the future.
        """
        if context is None:
            context = {}
        if type(ids) is not list:
            ids = [ids]

        account_journal_obj = self.pool.get('account.journal')
        account_invoice_obj = self.pool.get('account.invoice')
        picking_obj = self.pool.get('stock.picking')

        # We browse the picking as a generic stock.picking, instead of its
        # real stock.picking.IN, because deep into the chain of calls that
        # follow, it arrives to a point were the code hits the methods
        # _get_comment_invoice and _get_currency_id, and maybe others, which
        # are inplemented in such a way that the code requiring the fields
        # for a picking.IN (e.g. needing access to purchase_id) or requiring
        # the fields for a picking.OUT (e.g. needing access to sale_id) are
        # not separated into the implementations of stock.picking.in or
        # stock.picking.out, but are both within the stock.picking. Thus, any
        # code which attempts to call the picking.IN as a picking.IN (instead
        # of a generic stock.picking) MAY end up (depending on the layers
        # in which the modules are arranged) calling a code which expects
        # a field that doesn't exist. IMHO this is a bug of the core, but to
        # avoid changing it (which would only imply moving the implementations
        # into the current class, and making the 'parent' class stock.picking
        # call one or the other depending on the type of the picking) I simply
        # force the stock.picking.IN to be a generic stock.picking.NOTHING.
        picking_in = self.pool.get('stock.picking').browse(cr, uid, ids[0], context=context)
        draft_invoice_ids = picking_in.purchase_id.get_draft_invoices()

        if not draft_invoice_ids:
            # Have a look at addons/stock/wizard/stock_invoice_onshipping,
            # method _get_journal_id() for the next line.
            purchase_journal_ids = account_journal_obj.search(cr, uid, [
                ('type', '=', 'purchase'),
            ], limit=1, context=context)
            journal_id = \
                False if not purchase_journal_ids else purchase_journal_ids[0]

            picking_obj.action_invoice_create(cr, uid, [picking_in.id],
                                              journal_id=journal_id,
                                              type='in_invoice', group=False,
                                              context=context)

        elif len(draft_invoice_ids) == 1:
            invoice = account_invoice_obj.browse(cr, uid, draft_invoice_ids[0],
                                                 context)
            invoice.update_invoice_lines_from_picking(picking_in)

        else:
            raise Warning(
                _('More than one invoice in state draft was found for '
                  'the purchase order associated to '
                  'picking with ID={0}').format(picking_in.id))

        picking_in.write({'invoice_state': 'invoiced'})

        return True

    def set_event(self, cr, uid, ids, picking_state, event_state,
                  event_info, context=None):
        """ Sets the event in the state given to have the indicated state
            and information.
        """
        if context is None:
            context = {}

        event_obj = self.pool.get('stock.event')

        for picking in self.browse(cr, uid, ids, context=context):
            warehouse = picking.purchase_id.warehouse_id
            event_code = 'new_picking_state_{0}'.format(picking_state)
            event_ids = event_obj.search(cr, uid, [
                ('warehouse_id', '=', warehouse.id),
                ('state', '!=', event_state),
                ('res_id', '=', picking.id),
                ('model', '=', 'stock.picking.in'),
                ('event_code', '=', event_code),
            ], context=context)
            event_obj.write(cr, uid, event_ids, {
                'state': event_state,
                'info': event_info,
            }, context=context)

        return True

    _columns = {
        'yellowcube_customer_order_no': fields.function(get_customer_order_no,
                                                        string="YC CustomerOrderNo",
                                                        type='text',
                                                        store={'stock.picking': (lambda self, cr, uid, ids, context=None: ids, ['sale_id', 'purchase_id'], 10)},
                                                        readonly=True),
        'yellowcube_delivery_no': fields.char('YCDeliveryNo', size=10, help='Tag <YCDeliveryNo> of the WAR file.'),
        'yellowcube_delivery_date': fields.date('YCDeliveryDate', help='Tag <YCDeliveryDate> of the WAR file.'),
        'yellowcube_return_origin_order': fields.many2one('sale.order', 'Original order'),
        'yellowcube_return_automate': fields.boolean('Automate return-claim on confirm'),
        'yellowcube_return_reason': fields.selection(RETURN_REASON_CODES, 'Return reason (if and only if return)', help='Return reason in accordance with the Return-Reason Code List'),

        'carrier_tracking_url': fields.char(
            'Carrier Tracking URL',
            help='URL for the tracking webpage provided '
                 'by the delivery carrier.'),

        'yellowcube_last_confirmation_timestamp': fields.datetime(
            string='Last confirmation file from YC',
            help='Last time a confirmation file (WBA/WAR) was processed for '
                 'this picking.'),
    }


class stock_picking_out_ext(osv.Model):
    _inherit = 'stock.picking.out'

    def create(self, cr, uid, vals, context=None):
        picking_id = super(stock_picking_out_ext, self).create(
            cr, uid, vals, context=context)

        if 'sale_id' in vals or 'carrier_id' in vals:
            self.set_mandatory_additional_shipping_codes(cr, uid, picking_id,
                                                         context=context)

        return picking_id

    def write(self, cr, uid, ids, vals, context=None):
        ret = super(stock_picking_out_ext, self).write(
            cr, uid, ids, vals, context=None)

        if 'sale_id' in vals or 'carrier_id' in vals:
            self.set_mandatory_additional_shipping_codes(cr, uid, ids,
                                                         context=context)

        return ret

    def store_tracking_link(self, cr, uid, ids, context=None):
        return self.pool.get('stock.picking').\
            store_tracking_link(cr, uid, ids, context=context)

    def send_tracking_email_to_client(self, cr, uid, ids, context=None):
        return self.pool.get('stock.picking').\
            send_tracking_email_to_client(cr, uid, ids, context=context)

    def get_filename_for_wab(self, cr, uid, ids, context=None):
        return self.pool['stock.picking'].get_filename_for_wab(cr, uid, ids, context=context)

    def get_attachment_wab(self, cr, uid, ids, context=None):
        return self.pool['stock.picking'].get_attachment_wab(cr, uid, ids, context=context)

    def equal_addresses_ship_invoice(self, cr, uid, ids, context=None):
        return self.pool['stock.picking'].equal_addresses_ship_invoice(cr, uid, ids, context)

    def get_customer_order_no(self, cr, uid, ids, field=None, arg=None, context=None):
        return self.pool['stock.picking'].get_customer_order_no(cr, uid, ids, field=field, arg=arg, context=context)

    def wrapper_do_partial(self, cr, uid, ids, partial_datas, context=None):
        return self.pool['stock.picking'].wrapper_do_partial(
            cr, uid, ids, partial_datas, context=context)

    def payment_method_has_epayment(self, cr, uid, ids, context=None):
        return self.pool['stock.picking'].payment_method_has_epayment(cr, uid, ids, context)

    _columns = {
        'yellowcube_customer_order_no': fields.function(get_customer_order_no,
                                                        string="YC CustomerOrderNo",
                                                        type='text',
                                                        store={'stock.picking': (lambda self, cr, uid, ids, context=None: ids, ['sale_id', 'purchase_id'], 10)},
                                                        readonly=True),
        'yellowcube_delivery_no': fields.char('YCDeliveryNo', size=10, help='Tag <YCDeliveryNo> of the WAR file.'),
        'yellowcube_return_origin_order': fields.many2one('sale.order', 'Original order'),
        'yellowcube_delivery_date': fields.date('YCDeliveryDate', help='Tag <YCDeliveryDate> of the WAR file.'),
        'yellowcube_return_automate': fields.boolean('Automate return-claim on confirm'),
        'yellowcube_return_reason': fields.selection(RETURN_REASON_CODES, 'Return reason (if and only if return)', help='Return reason in accordance with the Return-Reason Code List'),

        'carrier_tracking_url': fields.char(
            'Carrier Tracking URL',
            help='URL for the tracking webpage provided '
                 'by the delivery carrier.'),

        'yellowcube_last_confirmation_timestamp': fields.datetime(
            string='Last confirmation file from YC',
            help='Last time a confirmation file (WBA/WAR) was processed for '
                 'this picking.'),
    }

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
