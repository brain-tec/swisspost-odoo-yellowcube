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

from openerp.osv import fields, osv


class sale_shop_ext(osv.osv):
    _inherit = 'sale.shop'

    def get_stock_location_ids(self, cr, uid, ids, context=None):
        """ Gets the location's ID for the shop. In the case
            that several shop's IDs are received, returns the locations
            from all the shops.
        """
        if context is None:
            context = {}
        if type(ids) is not list:
            ids = [ids]

        shop_obj = self.pool.get('sale.shop')

        location_ids = set()
        for shop in shop_obj.browse(cr, uid, ids, context=context):
            location_ids.add(shop.warehouse_id.lot_stock_id.id)

        return list(location_ids)

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
