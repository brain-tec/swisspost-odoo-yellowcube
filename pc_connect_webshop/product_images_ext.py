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
from osv import osv, fields
from openerp.tools.translate import _


class product_image_ext(osv.Model):
    _inherit = 'product.images'

    def create(self, cr, uid, values, context=None):
        free_order = values.get('sort_order', 0)
        ids = self.search(cr, uid, [('product_id', '=', values['product_id'])], context=context)
        if ids:
            sort_orders = [x['sort_order'] for x in self.read(cr, uid, ids, ['sort_order'], context=context)]
            while free_order in sort_orders:
                free_order += 1
        values['sort_order'] = free_order
        result = super(product_image_ext, self).create(cr, uid, values, context=context)
        return result

    _columns = {
        'sort_order': fields.integer('Webshop sort order', required=True)
    }

    _defaults = {
        'sort_order': 0
    }

    _sql_constraints = [
        ('Unique sort order per product', 'UNIQUE(product_id,sort_order)', _('It is required to have a unique picture with a sort order for a product'))
    ]
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: