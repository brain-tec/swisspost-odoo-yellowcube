# b-*- encoding: utf-8 -*-
##############################################################################
#
#    Copyright (c) 2017 brain-tec AG (http://www.braintec-group.com)
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


import time
from lxml import etree
from openerp.osv import fields, osv
from openerp.tools.misc import DEFAULT_SERVER_DATETIME_FORMAT
from openerp.tools.float_utils import float_compare
import openerp.addons.decimal_precision as dp
from openerp.tools.translate import _


class stock_partial_picking_ext(osv.osv_memory):
    _inherit = "stock.partial.picking"

    def _partial_move_for(self, cr, uid, move, context=None):
        res = super(stock_partial_picking_ext, self)._partial_move_for(
            cr, uid, move, context=context)
        res['yc_qty_done'] = move.yc_qty_done
        return res

    def do_partial(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        if type(ids) is not list:
            ids = [ids]

        # Copies into the quantity field of the wizard the quantity
        # indicated in the new field yc_qty_done. We do this
        # because the internals of the wizard works with this quantity,
        # but the user only sees (after our modification) the quantity done
        # ***BUT*** at the same time we have to be very careful when doing
        # this, since the wizard may be called programmatically, and simply
        # copying the quantity from the yc_qty_done will make all the existing
        # code relying on this wizard to fail (because they use the value
        # set on 'quantity' as is. Thus if we have the active_id or active_ids
        # on the context we assume we are using this code triggered from the
        # user interface, and otherwise we use the code as-is.
        from_ui = 'active_id' in context or 'active_ids' in context
        if from_ui:
            wizard = self.browse(cr, uid, ids[0], context=context)
            for wizard_line in wizard.move_ids:
                wizard_line.write({'quantity': wizard_line.yc_qty_done})

        ret = super(stock_partial_picking_ext, self).do_partial(
            cr, uid, ids, context=context)

        if from_ui:
            # Updates the quantity done after the call to the wizard.
            # do_partial has called action_confirm over the stock.move,
            # but it doesn't matter since yc_qty_done is just an informative
            # field, not used to compute the inventory directly (it still uses
            # the regular quantity field).
            for wizard_line in wizard.move_ids:
                wizard_line.move_id.write(
                    {'yc_qty_done': wizard_line.yc_qty_done})

        return ret

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
