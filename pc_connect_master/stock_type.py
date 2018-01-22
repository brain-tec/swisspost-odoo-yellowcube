# b-*- encoding: utf-8 -*-
##############################################################################
#
#    Copyright (c) 2016 brain-tec AG (http://www.braintec-group.com
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

STOCK_ROUTE_TYPES = [
    ('regular', 'Regular'),
    ('c+c', 'Click & Collect'),
    ('c+r', 'Click & Reserve'),
]

class stock_type(osv.Model):
    _name = 'stock.type'
    _rec_name = 'name'

    _columns = {
        'name': fields.char('Name'),
        'credit_check': fields.boolean('Do Credit Check?'),
        'availability_check': fields.boolean('Do Availability Check?'),
        'dropship': fields.boolean('Is it a drop-shippment?'),
        'forced_picking_policy': fields.selection(
            [('one', 'Force One Delivery'),
             ('direct', 'Force Partial Deliveries'),
             ('keep', 'According to Configuration'),
             ], string="Picking Policy to Force"),
        'consider_aging': fields.boolean('Consider a Sale Order Aging?'),
        'route': fields.selection(STOCK_ROUTE_TYPES, string="Route Type"),
        'warehouse_id': fields.many2one('stock.warehouse', 'Warehouse'),
        'supplier_payment_term_id': fields.many2one(
            'account.payment.term', 'Payment Term for the Supplier Invoice',
            help='If not set, the payment term from the customer invoice '
                 'will be used instead.'),
    }

    _defaults = {
        'credit_check': False,
        'availability_check': False,
        'dropship': False,
        'forced_picking_policy': 'keep',
        'consider_aging': False,
        'route': 'regular',
    }

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
