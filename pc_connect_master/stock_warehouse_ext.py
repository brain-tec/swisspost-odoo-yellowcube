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


class stock_warehouse_ext(osv.Model):
    _inherit = 'stock.warehouse'

    def get_stock_location_ids(self, cr, uid, ids, context=None):
        if not ids:
            ids = self.search(cr, uid, [], context=context)
        ret = []
        for data in self.read(cr, uid, ids, ['lot_stock_id'], context=context):
            loc_id = data['lot_stock_id']
            if loc_id and loc_id[0] not in ret:
                ret.append(loc_id[0])
        return ret

    def get_stock_location(self, cr, uid, ids, context=None):
        ''' Gets the stock location for our warehouse (there must be just one warehouse).
        '''
        if context is None:
            context = {}

        warehouse_obj = self.pool.get('stock.warehouse')
        warehouse_ids = warehouse_obj.search(cr, uid, [], context=context)

        if not warehouse_ids:
            raise orm.except_orm(_('No Warehouses Found'),
                                 _('There were no warehouses found in the system.'))
        if len(warehouse_ids) > 1:
            raise orm.except_orm(_('Bad Number of Warehouses'),
                                 _('{0} warehouses were found on the system, while just one is allowed.').format(len(warehouse_ids)))

        # Gets the stock location for our warehouse.
        stock_location = False
        for warehouse in warehouse_obj.browse(cr, uid, warehouse_ids, context=context):
            stock_location = warehouse.lot_stock_id
        if not stock_location:
            raise orm.except_orm(_('No Location Stock Defined'),
                                 _('No location was defined for stock (Location Stock) on the warehouse.'))

        return stock_location

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
