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
from openerp.tools import DEFAULT_SERVER_DATETIME_FORMAT
from openerp.tools.translate import _
import logging
logger = logging.getLogger(__name__)
from openerp import netsvc
import time
from stock_picking_ext import RETURN_REASON_CODES
from openerp.release import version_info


class stock_return_picking_ext(osv.osv_memory):
    _inherit = 'stock.return.picking'

    def _create_returns(self, cr, uid, ids, context=None):
        data = self.read(cr, uid, ids[0], context=context)
        if not data['yellowcube_return']:
            return super(stock_return_picking_ext, self)._create_returns(cr, uid, ids, context=context)
        if 'location_id' in data:
            default_location_dest_id = data['location_id'][0]
        else:
            default_location_dest_id = None
        logger.debug("Executing YC return code")
        if context is None:
            context = {}
        else:
            context = context.copy()
        record_id = context.get('active_id', False) or False
        move_obj = self.pool.get('stock.move')
        pick_obj = self.pool.get('stock.picking')
        uom_obj = self.pool.get('product.uom')
        if version_info[0] > 7:
            data_obj = self.pool['stock.return.picking.line']
            wf_service = None
        else:
            data_obj = self.pool['stock.return.picking.memory']
            wf_service = netsvc.LocalService("workflow")
        pick = pick_obj.browse(cr, uid, record_id, context=context)
        date_cur = time.strftime(DEFAULT_SERVER_DATETIME_FORMAT)
        set_invoice_state_to_none = True
        returned_lines = 0
        context['yellowcube_return_reason'] = data['yellowcube_return_reason']
        context['yellowcube_return_origin_order'] = data['yellowcube_return_origin_order'][0]
        context['yellowcube_return_automate'] = True
        if not data['yellowcube_return_reason']:
            raise osv.except_osv(_('Missing field'), _('Return reason'))

        # Cancel assignment of existing chained assigned moves
        moves_to_unreserve = []
        for move in pick.move_lines:
            to_check_moves = [move.move_dest_id] if move.move_dest_id.id else []
            while to_check_moves:
                current_move = to_check_moves.pop()
                if current_move.state not in ('done', 'cancel') and current_move.reserved_quant_ids:
                    moves_to_unreserve.append(current_move.id)
                split_move_ids = move_obj.search(cr, uid, [('split_from', '=', current_move.id)], context=context)
                if split_move_ids:
                    to_check_moves += move_obj.browse(cr, uid, split_move_ids, context=context)

        if moves_to_unreserve:
            move_obj.do_unreserve(cr, uid, moves_to_unreserve, context=context)
            # break the link between moves in order to be able to fix them later if needed
            move_obj.write(cr, uid, moves_to_unreserve, {'move_orig_ids': False}, context=context)

#       Create new picking for returned products
        vals = {
            'move_lines': [],
            'state': 'draft',
        }
        if version_info[0] > 7:
            pick_type_id = pick.picking_type_id.return_picking_type_id and pick.picking_type_id.return_picking_type_id.id or pick.picking_type_id.id
            version_vals = {
                'picking_type_id': pick_type_id,
                'origin': pick.name,
            }
        else:
            seq_obj_name = 'stock.picking'
            new_type = 'internal'
            if pick.type == 'out':
                new_type = 'in'
                seq_obj_name = 'stock.picking.in'
            elif pick.type == 'in':
                new_type = 'out'
                seq_obj_name = 'stock.picking.out'
            new_pick_name = self.pool.get('ir.sequence').get(cr, uid, seq_obj_name)
            version_vals = {
                'name': _('%s-%s-return') % (new_pick_name, pick.name),
                'type': new_type,
                'date': date_cur,
                'invoice_state': data['invoice_state'],
            }

        vals.update(version_vals)
        new_picking = pick_obj.copy(cr, uid, pick.id, vals, context=context)

        for data_get in data_obj.browse(cr, uid, data['product_return_moves'], context=context):
            move = data_get.move_id
            if not move:
                raise osv.except_osv(_('Warning !'), _("You have manually created product lines, please delete them to proceed"))
            new_qty = data_get.quantity
            if version_info[0] < 8:
                new_location = move.location_dest_id.id
                returned_qty = move.product_qty
                for rec in move.move_history_ids2:
                    returned_qty -= rec.product_qty

                if returned_qty != new_qty:
                    set_invoice_state_to_none = False
            if new_qty:
                # The return of a return should be linked with the original's destination move if it was not cancelled
                if move.origin_returned_move_id.move_dest_id.id and move.origin_returned_move_id.move_dest_id.state != 'cancel':
                    move_dest_id = move.origin_returned_move_id.move_dest_id.id
                else:
                    move_dest_id = False

                returned_lines += 1
                vals = {
                    'picking_id': new_picking,
                    'state': 'draft',
                }
                if version_info[0] > 7:
                    vals.update({
                        'product_id': data_get.product_id.id,
                        'product_uom_qty': new_qty,
                        'product_uos_qty': new_qty * move.product_uos_qty / move.product_uom_qty,
                        'location_id': move.location_dest_id.id,
                        'location_dest_id': default_location_dest_id or move.location_id.id,
                        'picking_type_id': pick_type_id,
                        'warehouse_id': pick.picking_type_id.warehouse_id.id,
                        'origin_returned_move_id': move.id,
                        'procure_method': 'make_to_stock',
                        'restrict_lot_id': data_get.lot_id.id,
                        'move_dest_id': move_dest_id,
                    })
                else:
                    vals.update({
                        'product_qty': new_qty,
                        'product_uos_qty': uom_obj._compute_qty(cr, uid, move.product_uom.id, new_qty, move.product_uos.id),
                        'location_id': new_location,
                        'location_dest_id': (data_get.wizard_id.location_id or move.location_id).id,
                        'date': date_cur,
                        'prodlot_id': data_get.prodlot_id.id,
                    })
                new_move = move_obj.copy(cr, uid, move.id, vals, context=context)
                move_obj.write(cr, uid, [move.id], {'move_history_ids2': [(4, new_move)]}, context=context)
        if not returned_lines:
            raise osv.except_osv(_('Warning!'), _("Please specify at least one non-zero quantity."))

        if set_invoice_state_to_none:
            pick_obj.write(cr, uid, [pick.id], {'invoice_state': 'none'}, context=context)

        if data['sale_id']:
            # if the return is from a picking related to a sale.order we define the original order, but don't process the return
            pick_obj.write(cr, uid, new_picking, {'sale_id': data['sale_id'][0]}, context)

        if wf_service is not None:
            wf_service.trg_validate(uid, 'stock.picking', new_picking, 'button_confirm', cr)
            pick_obj.force_assign(cr, uid, [new_picking], context)
        else:
            pick_obj.action_confirm(cr, uid, [new_picking], context=context)
            pick_obj.action_assign(cr, uid, [new_picking], context)

        if version_info[0] > 7:
            return new_picking, pick_type_id

        # Update view id in context, lp:702939
        model_list = {
            'out': 'stock.picking.out',
            'in': 'stock.picking.in',
            'internal': 'stock.picking',
        }
        return {
            'domain': "[('id', 'in', [" + str(new_picking) + "])]",
            'name': _('Returned Picking'),
            'view_type': 'form',
            'view_mode': 'tree,form',
            'res_model': model_list.get(new_type, 'stock.picking'),
            'type': 'ir.actions.act_window',
            'context': context,
        }

    def _get_return_loc(self, location, res):
        if 'location_id' in res and res['location_id'] is not None:
            return res['location_id']
        if not location:
            return False
        for w in location.warehouse_ids:
            if w.field_id.name == 'lot_stock_id':
                if w.warehouse_id.stock_connect_id and w.warehouse_id.stock_connect_id.type:
                    if w.warehouse_id.stock_connect_id.type[:10] == 'yellowcube':
                        res['location_id'] = w.warehouse_id.lot_input_id.id
                        res['yellowcube_return'] = True
                        return w.warehouse_id.lot_input_id.id
        return False

    def create_returns(self, cr, uid, ids, context=None):
        """
         Creates return picking.
         @param self: The object pointer.
         @param cr: A database cursor
         @param uid: ID of the user currently logged in
         @param ids: List of ids selected
         @param context: A standard dictionary
         @return: A dictionary which of fields with values.
        """
        if context is None:
            context = {}
        else:
            context = context.copy()
        data = self.read(cr, uid, ids[0], context=context)
        if data['yellowcube_return']:
            context['yellowcube_return_reason'] = data['yellowcube_return_reason']
            context['yellowcube_return_origin_order'] = data['yellowcube_return_origin_order'][0]
            context['yellowcube_return_automate'] = True
            if not data['yellowcube_return_reason']:
                raise osv.except_osv(_('Missing field'), _('Return reason'))
        return super(stock_return_picking_ext, self).create_returns(cr, uid, ids, context=context)

    def default_get(self, cr, uid, fields, context=None):
        """
         To get default values for the object.
         @param self: The object pointer.
         @param cr: A database cursor
         @param uid: ID of the user currently logged in
         @param fields: List of fields for which we want default values
         @param context: A standard dictionary
         @return: A dictionary with default values for all field in ``fields``
        """
        if context is None:
            context = {}
        res = super(stock_return_picking_ext, self).default_get(cr, uid, fields, context=context)
        record_id = False
        if context:
            if 'active_id' in context:
                record_id = context['active_id']
            elif 'active_ids' in context:
                record_id = context['active_ids'][0]
        pick_obj = self.pool.get('stock.picking')
        pick = pick_obj.browse(cr, uid, record_id, context=context)
        if pick.sale_id:
            res['sale_id'] = pick.sale_id.id
            res['yellowcube_return'] = True
            res['yellowcube_return_origin_order'] = pick.sale_id.id
        res['location_id'] = pick.picking_type_id.warehouse_id.lot_input_id.id
        if not self._get_return_loc(pick.location_id, res):
            for move in pick.move_lines:
                if self._get_return_loc(move.location_id, res):
                    break
        if not res.get('location_id', None):
            logger.warning('It was not possible to assign a return location: {0}'.format(pick.name))
        res['yellowcube_return_origin_order'] = res.get('sale_id', None)
        return res

    _columns = {
        'yellowcube_return_origin_order': fields.many2one('sale.order', 'Original order'),
        'yellowcube_return_reason': fields.selection(RETURN_REASON_CODES, 'Return reason (if and only if return)', help='Return reason in accordance with the Return-Reason Code List'),
        'sale_id': fields.many2one('sale.order'),
        'location_id': fields.many2one('stock.location', string="Return location"),
        'yellowcube_return': fields.boolean('Under YC return'),
    }

    _defaults = {
        'location_id': None,
        'yellowcube_return': False,
        'yellowcube_return_origin_order': None,
    }
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
