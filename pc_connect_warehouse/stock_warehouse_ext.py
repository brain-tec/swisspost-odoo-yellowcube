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
from openerp.osv import osv, fields
from openerp.tools.translate import _
import logging
logger = logging.getLogger(__name__)
from stock_event import check_all_events, EVENT_STATE_CANCEL
from openerp import SUPERUSER_ID, api


class stock_warehouse_ext(osv.Model):
    _inherit = 'stock.warehouse'

    @api.multi
    def _validate_fields(self, field_names):
        """
        With this, validation is also made on the connection (e.g. avoid multiple warehouse in YC, etc.)
        """
        super(stock_warehouse_ext, self)._validate_fields(field_names)
        self.env['stock.warehouse.location'].update_table()
        for warehouse in self:
            if warehouse.stock_connect_id:
                warehouse.stock_connect_id._validate_fields([])

    def event_change_connection(self, cr, uid, res_id, context=None, warehouse_id=None):
        """
        This event method checks a change in the connection of the warehouse,
        and registers the event.

        This event only registers the first assignation to a connection.
        """
        if warehouse_id is None:
            # We know how to relate a warehouse to a warehouse. Itself.
            self.event_change_connection(cr, uid, res_id, context, res_id)
        if res_id != warehouse_id:
            return

        event_obj = self.pool['stock.event']
        warehouse = self.browse(cr, uid, warehouse_id, context)
        domain = [
            ('state', '!=', EVENT_STATE_CANCEL),
            ('warehouse_id', '=', warehouse_id),
            ('model', '=', 'stock.connect'),
        ]
        if warehouse.stock_connect_id:
            domain.append(('res_id', '=', warehouse.stock_connect_id.id))
        else:
            domain.append(('res_id', 'in', (False, None, 0)))
        if not event_obj.search(cr, uid, domain, context=context):
            # Then, we create the event
            if warehouse.stock_connect_id:
                domain.append(('res_id', '=', warehouse.stock_connect_id.id))
                vals = {
                    'event_code': 'warehouse_connection_set',
                    'res_id': warehouse.stock_connect_id.id,
                    'model': 'stock.connect',
                }
                event_obj.create(cr, uid, vals, context=context)
            else:
                vals = {
                    'event_code': 'warehouse_connection_unset',
                    'res_id': 0,
                    'model': 'stock.connect',
                }
                event_obj.create(cr, uid, vals, context=context)

    def check_events_on_warehouse(self, cr, uid, ids):
        """
        When checking for events, the model itself must provide the warehouse_id
        (In this case it is the object itself, but in other models it maybe more complex)

        Thanks to that function, it is not required to define a loop for checks again,
        only define a method which name begins with 'event_'
        """
        # First, we make sure the warehouse-location table is up-to-date
        # For this check, we must be superuser
        uid = SUPERUSER_ID

        self.pool.get('stock.warehouse.location').update_table(cr, uid)
        for _id in ids:
            check_all_events(self, cr, uid, ids, context={}, warehouse_id=_id)
        return True

    _columns = {
        'stock_connect_id': fields.many2one('stock.connect', 'Warehouse Connection', required=False),
        'stock_connect_type': fields.related('stock_connect_id', 'type', type="char", string='Connection type', readonly=True),
        'stock_event_ids': fields.one2many('stock.event', 'warehouse_id', 'Events'),
        'stock_connect_file_ids': fields.one2many('stock.connect.file', 'warehouse_id', 'Files'),
        'lot_input_id': fields.related('wh_input_stock_loc_id', type="many2one", relation="stock.location", string="Input location", required=True),
        'lot_output_id': fields.related('wh_output_stock_loc_id', type="many2one", relation="stock.location", string="Output location", required=True),
    }

    _constraints = [
        (check_events_on_warehouse, 'check of events on this item', []),
    ]
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
