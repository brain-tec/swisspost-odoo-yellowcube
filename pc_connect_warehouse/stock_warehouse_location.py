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
from openerp import api
from openerp.osv import osv, fields
from openerp.tools.translate import _
import logging
logger = logging.getLogger(__name__)
from openerp import SUPERUSER_ID


class stock_warehouse_location(osv.Model):
    _name = 'stock.warehouse.location'

    _columns = {
        'warehouse_id': fields.many2one('stock.warehouse', 'Warehouse', required=True),
        'location_id': fields.many2one('stock.location', 'Location', required=True),
        'field_id': fields.many2one('ir.model.fields', 'Field', required=True),
    }

    @api.cr_uid
    def update_table(self, cr, uid):
        # For this update, we must be superuser
        uid = SUPERUSER_ID
        logger.debug("Updating stock.location inverse table")
        field_model = self.pool.get('ir.model.fields')
        warehouse_model = self.pool.get('stock.warehouse')
        warehouse_ids = warehouse_model.search(cr, uid, [])
        field_ids = field_model.search(cr, uid, [('model', '=', 'stock.warehouse'), ('relation', '=', 'stock.location')])
        field_names = field_model.read(cr, uid, field_ids, ['name'])
        for warehouse in warehouse_model.read(cr, uid, warehouse_ids, [x['name'] for x in field_names]):
            for field in field_names:
                wid = warehouse['id']
                fid = field['id']
                lid = warehouse.get(field['name'], None)
                id_r = self.search(cr, uid, [('warehouse_id', '=', wid),
                                             ('field_id', '=', fid)])
                if not lid:
                    if id_r:
                        self.unlink(cr, uid, id_r)
                else:
                    if id_r:
                        if lid != self.read(cr, uid, id_r, ['location_id'])[0]['location_id']:
                            self.write(cr, uid, id_r, {'location_id': lid[0]})
                    else:
                        self.create(cr, uid, {'location_id': lid[0],
                                              'warehouse_id': wid,
                                              'field_id': fid})

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
