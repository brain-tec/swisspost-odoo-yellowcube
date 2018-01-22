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

from openerp.osv import osv, fields
from openerp.tools.translate import _


class product_standard_price_history(osv.Model):
    """ Keeps track of the different updates of the field standard_price
        for each product.
    """
    _name = 'pc_connect_master.product_standard_price_history'

    def add(self, cr, uid, ids, product_ids, new_standard_price_value, context=None):
        """ Adds a new standard price value to the historial data.
        """
        if context is None:
            context = {}
        if type(product_ids) is not list:
            product_ids = [product_ids]

        for product_id in product_ids:
            self.create(cr, uid, {'product_id': product_id,
                                  'standard_price_value': new_standard_price_value,
                                  }, context=context)
        return True

    _columns = {
        'product_id': fields.many2one('product.product', 'Product', readonly=True, required=True, index=True),
        'create_date': fields.datetime('Create Date', readonly=True, required=True, index=True),
        'standard_price_value': fields.float('Cost Price', readonly=True, required=True),
    }

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
