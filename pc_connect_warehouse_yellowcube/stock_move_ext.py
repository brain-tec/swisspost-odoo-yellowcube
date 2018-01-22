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
from openerp.osv import osv, fields
from openerp.tools.translate import _


class stock_move_ext(osv.Model):
    _inherit = 'stock.move'

    def split_move_by_lot(self, cr, uid, ids, lot, lot_qty, context=None):
        """ Splits a stock.move according to a given quantity for a lot.
        """
        if context is None:
            context = {}

        lot_split_obj = self.pool.get('stock.move.split')
        lot_split_lines_obj = self.pool.get('stock.move.split.lines')

        res = {}

        for move in self.browse(cr, uid, ids, context=context):
            res[move.id] = []

            lot_split_id = lot_split_obj.create(cr, uid, {
                'product_id': move.product_id.id,
                'qty': move.product_qty,
                'product_uom': move.product_uom.id,
                'use_exist': True,
            }, context=context)
            lot_split_lines_obj.create(
                cr, uid, {
                    'name': lot.name,
                    'prodlot_id': lot.id,
                    'quantity': lot_qty,
                    'wizard_exist_id': lot_split_id,
                }, context=context)

            new_ctx = context.copy()
            new_ctx['active_model'] = 'stock.move'
            new_move_ids = lot_split_obj.split(
                cr, uid, [lot_split_id], [move.id],
                context=new_ctx)

            # We have to clear the yc_qty_done because its value
            # is copied when doing the split.
            self.write(cr, uid, new_move_ids, {
                'yc_qty_done': 0.0,
            }, context=context)

            res[move.id] = new_move_ids

        return res

    _columns = {
        'yc_posno': fields.integer('PosNo value on YC files', required=False),
        'yc_booking_voucher_id': fields.char("YellowCube's BookingVoucherID"),
        'yc_booking_voucher_year': fields.char("YellowCube's BookingVoucherYear"),
        'yc_qty_done': fields.float(
            string='YC Qty Done',
            help='This is the increment of the qty received in the YC '
                 'confirmation files (WBA/WAR)'),
        'yc_eod_received': fields.boolean(
            string='YC EoD',
            help='True if the EndOfDelivery flag has been received in any of '
                 'the processed WBA/WAR files for this picking line.'),
    }

    _defaults = {
        'yc_posno': False,
        'yc_eod_received': False,
        'yc_qty_done': 0.0,
    }

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: