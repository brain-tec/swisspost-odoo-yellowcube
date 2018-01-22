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

from osv import osv, fields
from openerp import netsvc
from tools import ustr
from tools.translate import _

from bt_helper.log_rotate import get_log
logger = get_log()


class sale_order_ext(osv.osv):

    """
    Extends sale order adding free texts
    """
    _inherit = 'sale.order'

    def _prepare_invoice(self, cr, uid, order, lines, context=None):
        """
        Add the followup partner id from the partner of the sale order
        """
        invoice_vals = super(
            sale_order_ext,
            self)._prepare_invoice(
                cr,
                uid,
         order,
         lines,
         context=context)

        invoice_vals.update({
            'followup_responsible_id':
                order.partner_id.followup_responsible_id.id,
        })
        return invoice_vals

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
