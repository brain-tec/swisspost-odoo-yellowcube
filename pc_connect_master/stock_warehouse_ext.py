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


class stock_warehouse_ext(osv.Model):
    _inherit = 'stock.warehouse'

    def get_stock_location_ids(self, cr, uid, ids, context=None):
        """ Returns all the stock location's IDs of the warehouses
            the ID of which is received. If no IDs are sent, then returns
            all the stock locations of all the warehouses of the system.
        """
        if context is None:
            context = {}
        if not ids:
            ids = self.search(cr, uid, [], context=context)
        elif type(ids) is not list:
            ids = [ids]

        ret = set()
        for warehouse in self.browse(cr, uid, ids, context=context):
            ret.add(warehouse.lot_stock_id.id)
        return list(ret)

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
