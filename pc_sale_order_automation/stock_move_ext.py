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

from openerp.osv import osv, fields, orm
from openerp.tools.translate import _
from openerp.addons.stock import stock_picking
from openerp import netsvc
import math


class stock_move_ext(osv.Model):
    _inherit = 'stock.move'

    def compute_ratio_of_packages(self, cr, uid, ids, context=None):
        """ We compute the ratio of packages that are needed to pack
            this stock move, as a floating point number,
            e.g. 1.5 means 1 package and a half.

            This requires its product to define a packaging type and
            the amount which fits in each pack. If the product
            does not meet this condition, the method raises.

            Returns an integer indicating the number of packages required.

            MUST be called over just one ID, or a list of IDs of just one element
            (otherwise just the first ID of the list will be considered).
        """
        if context is None:
            context = {}
        if type(ids) is not list:
            ids = [ids]

        product_uom_obj = self.pool.get('product.uom')

        stock_move = self.browse(cr, uid, ids[0], context=context)

        # Checks that the stock move has a product with a packaging type well configured.
        product = stock_move.product_id
        packaging_type = product.packaging_type_id
        packaging_qty_per_parcel = product.packaging_qty_per_parcel
        if (not packaging_type) or (not packaging_qty_per_parcel):
            raise orm.except_orm(_('Missing Data on Product Regarding Packaging'),
                                 _('Method compute_num_packages was called over product with ID={0} '
                                   'but either field packaging_type or packaging_qty_per_parcel was not set.'). format(product.id))

        # Computes the quantity in the UOM of the product, because packaging_qty_per_parcel
        # is always set in the UOM of the product.
        qty_uom = product_uom_obj._compute_qty(cr, uid, stock_move.product_uom.id, stock_move.product_qty, product.uom_id.id)
        ratio_of_packages = (float(qty_uom) / product.packaging_qty_per_parcel)

        # We truncate the number of decimals to reduce the chance of having floating point issues.
        # For instance a picking with quantities 1, 1, 4, 1, 1, 1 gives a total amount
        # of packages of 3.0000000000000004, while it has to be 3 of course.
        # This should be enough to deal with this kind of errors.
        stock_packing_max_precision = 1.0 / 10 ** self.pool.get('decimal.precision').precision_get(cr, uid, 'Stock Packing')
        if abs(math.floor(ratio_of_packages) - ratio_of_packages) < stock_packing_max_precision:
            # If e.g. floor(3.0000000000000004) - 3.0000000000000004 < 0.001, then we don't need an extra package, otherwise yes.
            ratio_of_packages = float(int(ratio_of_packages))
        #else:
        #    ratio_of_packages = ratio_of_packages

        return ratio_of_packages

    def _fun_compute_ratio_of_packages(self, cr, uid, ids, field_name, args, context=None):
        """ Wrapper over _compute_ratio_of_packages for the functional field.
        """
        res = {}
        packaging_is_enabled = self.pool.get('configuration.data').get(cr, uid, None, context=context).packaging_enabled
        if packaging_is_enabled:
            for stock_move in self.browse(cr, uid, ids, context=context):
                res[stock_move.id] = stock_move.compute_ratio_of_packages()
        else:
            res = dict.fromkeys(ids, 0.0)
        return res

    def split_into(self, cr, uid, ids, quantity, context=None):
        ''' This was originally copied from method 'split()',
            of object wizard 'stock.split.into', but was simplified considerably
            to avoid assigning a stock.tracking object to the stock move, and now
            it simply splits a stock move into two.

            Splits a stock move into two, the first one having the indicated quantity,
            and the second one the remaining quantity.

            This method must receive just an ID; if a list of more than one ID is received,
            it picks just the first one.
        '''
        if context is None:
            context = {}
        if type(ids) is not list:
            ids = [ids]

        move = self.browse(cr, uid, ids[0], context=context)

        # If the split is full, we won't create a new stock.move, thus we'll return False.
        new_stock_move_id = False

        # Gets the quantity which will remain to allocate and that will go to the second move.
        quantity_rest = move.product_qty - quantity

        if quantity > move.product_qty:
            raise osv.except_osv(_('Error!'),
                                 _('Total quantity after split exceeds the quantity to split '
                                   'for this product: "{0}" (id: {1}).').format(move.product_id.name, move.product_id.id))

        if quantity > 0:
            move.write({
                'product_qty': quantity,
                'product_uos_qty': quantity,
                'product_uos': move.product_uom.id,
            })

        if quantity_rest > 0:
            default_val = {
                'product_qty': quantity_rest,
                'product_uos_qty': quantity_rest,
                'state': move.state,
                'product_uos': move.product_uom.id,
                'prodlot_id': move.prodlot_id.id,
            }
            new_stock_move_id = self.copy(cr, uid, move.id, default_val, context=context)

        return new_stock_move_id

    def action_cancel(self, cr, uid, ids, context=None):
        """ This is overridden so that when we cancel a stock move we
            see if there is a procurement in state confirmed, because after
            we have cancel the stock, the procurement should be run so that
            it's set as canceled also (otherwise it'll block the sale.order's
            workflow, thus requiring a manual intervention (something we
            try to minimise here).
        """
        if context is None:
            context = {}
        if not isinstance(ids, list):
            ids = [ids]

        wf_service = netsvc.LocalService('workflow')
        proc_obj = self.pool.get('procurement.order')

        ret = super(stock_move_ext, self).action_cancel(
            cr, uid, ids, context=context)

        # Runs the procurements.
        for move_id in ids:
            proc_ids = proc_obj.search(cr, uid, [
                ('move_id', '=', move_id),
                ('state', '=', 'confirmed')
            ], context=context)
            for proc_id in proc_ids:
                wf_service.trg_validate(uid, 'procurement.order', proc_id,
                                        'button_check', cr)

        return ret

    _columns = {
        'ratio_of_packages': fields.function(_fun_compute_ratio_of_packages, type="float", string="Ratio of Packages"),
    }


# HACK over Odoo:
# When a partial picking is done, Odoo doesn't copy the lot nor the package of the
# moves from the new picking to the backorder, and also removes the original package
# from the move which is actually sent. 
# We want this to be different: want to copy the lot always, and the package
# only on the move which is being actually delivered (not on the one for the
# backorder).
# Therefore, we OVERWRITE method do_partial from file addons/stock/stock.py
# Additions are enclosed between <Addition> and </Addition> tags.
def __do_partial(self, cr, uid, ids, partial_datas, context=None):
    """ Makes partial picking and moves done.
    @param partial_datas : Dictionary containing details of partial picking
                      like partner_id, partner_id, delivery_date,
                      delivery moves with product_id, product_qty, uom
    @return: Dictionary of values
    """
    if context is None:
        context = {}
    else:
        context = dict(context)
    res = {}
    move_obj = self.pool.get('stock.move')
    uom_obj = self.pool.get('product.uom')
    sequence_obj = self.pool.get('ir.sequence')
    wf_service = netsvc.LocalService("workflow")
    for pick in self.browse(cr, uid, ids, context=context):
        new_picking = None
        complete, too_many, too_few = [], [], []
        move_product_qty, prodlot_ids, product_avail, partial_qty, uos_qty, product_uoms = {}, {}, {}, {}, {}, {}
        for move in pick.move_lines:
            if move.state in ('done', 'cancel'):
                continue
            partial_data = partial_datas.get('move%s'%(move.id), {})
            product_qty = partial_data.get('product_qty',0.0)
            move_product_qty[move.id] = product_qty
            product_uom = partial_data.get('product_uom', move.product_uom.id)
            product_price = partial_data.get('product_price',0.0)
            product_currency = partial_data.get('product_currency',False)
            prodlot_id = partial_data.get('prodlot_id')
            prodlot_ids[move.id] = prodlot_id
            product_uoms[move.id] = product_uom
            partial_qty[move.id] = uom_obj._compute_qty(cr, uid, product_uoms[move.id], product_qty, move.product_uom.id)
            uos_qty[move.id] = move.product_id._compute_uos_qty(product_uom, product_qty, move.product_uos) if product_qty else 0.0
            if move.product_qty == partial_qty[move.id]:
                complete.append(move)
            elif move.product_qty > partial_qty[move.id]:
                too_few.append(move)
            else:
                too_many.append(move)

            if (pick.type == 'in') and (move.product_id.cost_method == 'average'):
                # Record the values that were chosen in the wizard, so they can be
                # used for average price computation and inventory valuation
                move_obj.write(cr, uid, [move.id],
                        {'price_unit': product_price,
                         'price_currency_id': product_currency})

        # every line of the picking is empty, do not generate anything
        empty_picking = not any(q for q in move_product_qty.values() if q > 0)

        for move in too_few:
            product_qty = move_product_qty[move.id]
            if not new_picking and not empty_picking:
                new_picking_name = pick.name
                self.write(cr, uid, [pick.id], 
                           {'name': sequence_obj.get(cr, uid,
                                        'stock.picking.%s'%(pick.type)),
                           })
                pick.refresh()
                new_picking = self.copy(cr, uid, pick.id,
                        {
                            'name': new_picking_name,
                            'move_lines' : [],
                            'state':'draft',
                        })
            if product_qty != 0:
                defaults = {
                        'product_qty' : product_qty,
                        'product_uos_qty': uos_qty[move.id],
                        'picking_id' : new_picking,
                        'state': 'assigned',
                        'move_dest_id': False,
                        'price_unit': move.price_unit,
                        'product_uom': product_uoms[move.id],
                        #<Addition>
                        # We want to keep the tracking if the move is split.
                        'tracking_id': move.tracking_id and move.tracking_id.id or False,
                        #</Addition>
                }
                prodlot_id = prodlot_ids[move.id]
                if prodlot_id:
                    defaults.update(prodlot_id=prodlot_id)
                move_obj.copy(cr, uid, move.id, defaults)
            move_obj.write(cr, uid, [move.id],
                    {
                        'product_qty': move.product_qty - partial_qty[move.id],
                        'product_uos_qty': move.product_uos_qty - uos_qty[move.id],
                        #<Addition>
                        # We want to maintain the lot (but not the tracking) on the new move.
                        'prodlot_id': move.prodlot_id.id,
                        'tracking_id': False,
                        #</Addition>
                    })

        if new_picking:
            move_obj.write(cr, uid, [c.id for c in complete], {'picking_id': new_picking})
        for move in complete:
            defaults = {'product_uom': product_uoms[move.id], 'product_qty': move_product_qty[move.id]}
            if prodlot_ids.get(move.id):
                defaults.update({'prodlot_id': prodlot_ids[move.id]})
            move_obj.write(cr, uid, [move.id], defaults)
        for move in too_many:
            product_qty = move_product_qty[move.id]
            defaults = {
                'product_qty' : product_qty,
                'product_uos_qty': uos_qty[move.id],
                'product_uom': product_uoms[move.id]
            }
            prodlot_id = prodlot_ids.get(move.id)
            if prodlot_ids.get(move.id):
                defaults.update(prodlot_id=prodlot_id)
            if new_picking:
                defaults.update(picking_id=new_picking)
            move_obj.write(cr, uid, [move.id], defaults)

        # At first we confirm the new picking (if necessary)
        if new_picking:
            wf_service.trg_validate(uid, 'stock.picking', new_picking, 'button_confirm', cr)
            # Then we finish the good picking
            self.write(cr, uid, [pick.id], {'backorder_id': new_picking})
            self.action_move(cr, uid, [new_picking], context=context)
            wf_service.trg_validate(uid, 'stock.picking', new_picking, 'button_done', cr)
            wf_service.trg_write(uid, 'stock.picking', pick.id, cr)
            delivered_pack_id = new_picking
            self.message_post(cr, uid, new_picking, body=_("Back order <em>%s</em> has been <b>created</b>.") % (pick.name), context=context)
        elif empty_picking:
            delivered_pack_id = pick.id
        else:
            self.action_move(cr, uid, [pick.id], context=context)
            wf_service.trg_validate(uid, 'stock.picking', pick.id, 'button_done', cr)
            delivered_pack_id = pick.id

        delivered_pack = self.browse(cr, uid, delivered_pack_id, context=context)
        res[pick.id] = {'delivered_picking': delivered_pack.id or False}

    return res

stock_picking.do_partial = __do_partial


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
