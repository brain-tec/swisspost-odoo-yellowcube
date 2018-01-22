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

import openerp
from openerp.osv import osv, fields, orm
from openerp.tools.translate import _


class barcode_storage(osv.Model):
    ''' Stores pre-computed barcode labels for a given combination
        of picking and tracking number. This way we can avoid calling
        again the service to provide a label if we already have one.
    '''

    _name = 'barcode.storage'

    _columns = {
        'picking_id': fields.many2one('stock.picking', 'Picking', required=True, index=True),
        'tracking_id': fields.many2one('stock.tracking', 'Package', index=True),
        'barcode_base64': fields.binary('Barcode Label', required=True),
    }

    _sql_constraints = [
        ('picking_tracking_unique', 'unique (picking_id, tracking_id)',
         'Only one barcode label can exist for a given combination of picking_id and tracking_id'),
    ]

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
