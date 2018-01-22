# b-*- encoding: utf-8 -*-
##############################################################################
#
#    Copyright (c) 2014 brain-tec AG (http://www.braintec-group.com)
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
from utilities.db import create_db_index


class sale_order_line_ext(osv.Model):
    _inherit = 'sale.order.line'

    def init(self, cr):
        """ Creates some indices that can not be created directly using the ORM
        """
        create_db_index(cr, 'sale_order_line_company_id_state_product_id_index', 'sale_order_line', 'company_id, state, product_id')

    def _get_line_from_so(self, cr, uid, ids, context=None):
        return self.pool['sale.order.line'].search(cr, uid, [('order_id', 'in', ids)], context=context)

    _columns = {
        'sale_date': fields.related('order_id',
                                    'date_order',
                                    string='Sale date',
                                    type="date",
                                    readonly=True,
                                    store={'sale.order': (_get_line_from_so, ['date_order'], 10),
                                           }
                                    ),
        'xx_price_subtotal': fields.related('price_subtotal',
                                            string='Subtotal',
                                            type="float",
                                            readonly=True,
                                            store={'sale.order': (_get_line_from_so, ['total'], 10),
                                                   'sale.order.line': (lambda s, cr, u, i, ct=None: i, ['price_subtotal', 'price_unit', 'discount', 'tax_id'], 10),
                                                   }
                                            ),
        'alt_carrier_id': fields.many2one(
            'delivery.carrier', 'Alternative Carrier',
            help='The alternative delivery carrier needed to dispatch this '
                 'item, that may be different than the one defined '
                 'on the sale.order this line belongs to.'),
    }

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
