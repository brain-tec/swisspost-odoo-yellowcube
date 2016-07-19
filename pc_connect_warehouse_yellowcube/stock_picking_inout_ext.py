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
from openerp.release import version_info
assert version_info[0] <= 7, "This file can only be loaded on version 7 or lower."

from openerp.osv import osv, fields
from openerp.tools.translate import _
from stock_picking_ext import RETURN_REASON_CODES
import logging
logger = logging.getLogger(__name__)


class stock_picking_in_ext(osv.Model):
    _inherit = 'stock.picking.in'

    def get_filename_for_wab(self, cr, uid, ids, extension, context=None):
        raise Warning("get_filename_for_wab can not be called over stock.picking.in.")

    def get_attachment_wab(self, cr, uid, ids, extension='pdf', context=None):
        raise Warning("get_attachment_wab can not be called over stock.picking.in.")

    def get_customer_order_no(self, cr, uid, ids, field, arg, context=None):
        return self.pool['stock.picking'].get_customer_order_no(cr, uid, ids, field, arg, context=context)

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
    }


class stock_picking_out_ext(osv.Model):
    _inherit = 'stock.picking.out'

    def get_filename_for_wab(self, cr, uid, ids, extension, context=None):
        return self.pool['stock.picking'].get_filename_for_wab(cr, uid, ids, extension, context=context)

    def get_attachment_wab(self, cr, uid, ids, extension='pdf', context=None):
        return self.pool['stock.picking'].get_attachment_wab(cr, uid, ids, extension, context=context)

    def equal_addresses_ship_invoice(self, cr, uid, ids, context=None):
        return self.pool['stock.picking'].equal_addresses_ship_invoice(cr, uid, ids, context)

    def get_customer_order_no(self, cr, uid, ids, field, arg, context=None):
        return self.pool['stock.picking'].get_customer_order_no(cr, uid, ids, field, arg, context=context)

    def is_first_delivery(self, cr, uid, ids, context=None):
        return self.pool['stock.picking'].is_first_delivery(cr, uid, ids, context)

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
    }

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
