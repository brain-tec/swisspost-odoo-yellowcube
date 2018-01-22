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


class product_pending(osv.Model):
    """ Encodes a product which is still pending to be sent when creating an invoice
        or a picking. So this is an auxiliary model which just encodes a tuple of
        (product, quantity pending, unit of measure).
    """
    _name = 'pc_sale_order_automation.product_pending'

    _columns = {
        'product_id': fields.many2one('product.product', 'Product'),
        'product_uom_qty': fields.integer('Quantity'),
        'product_uom': fields.many2one('product.uom', 'Product Unit of Measure'),
    }

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
