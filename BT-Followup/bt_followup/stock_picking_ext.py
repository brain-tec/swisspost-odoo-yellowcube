# b-*- encoding: utf-8 -*-
#
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
#

from datetime import datetime

from openerp.osv import fields, osv, orm
from openerp.tools.translate import _
from openerp import netsvc
from openerp import tools
from openerp.tools import float_compare, DEFAULT_SERVER_DATETIME_FORMAT
import openerp.addons.decimal_precision as dp
from bt_helper.log_rotate import get_log
logger = get_log()


#===============================================================================
# stock_picking_ext
#=========================================================================
class stock_picking_ext(osv.osv):

    """
    Extends stock picking
    """
    _inherit = 'stock.picking'

    def _prepare_invoice(
            self, cr, uid, picking, partner, inv_type, journal_id, context=None):
        """
        When creating an invoice from a Delivery Order the Followup Responsible Id comes from the partner in the delivery order
        """

        invoice_vals = super(
            stock_picking_ext,
            self)._prepare_invoice(
                cr,
                uid,
         picking,
         partner,
         inv_type,
         journal_id,
         context=context)

        # As done in stock/stock.py, since it may be that we receive the ID.
        if isinstance(partner, int):
            partner = self.pool.get('res.partner').browse(cr, uid, partner, context=context)

        invoice_vals.update({
            'followup_responsible_id': partner.followup_responsible_id.id,
        })
        return invoice_vals
