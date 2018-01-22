# -*- coding: utf-8 -*-
# Copyright 2017 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl)

from openerp.osv import osv, fields


class gift_card(osv.Model):
    _name = 'gift.card'

    _columns = {
        'name': fields.char('Number', required=True, help='Unique identifier of the gift card'),
        'amount': fields.float('Amount', required=True),
        'date': fields.date('Date', required=True),
        'sale_order_id': fields.many2one('sale.order', "Used on"),
    }

    _sql_constraints = [
        ('name_uniq', 'unique(name)', 'The gift card name must be unique.')
    ]

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
