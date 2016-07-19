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


_yc_basic_shipping_codes = [(x[1], '{1}: {0}'.format(*x)) for x in [
    ('PostPac Economy', 'ECO'),
    ('PostPac Priority', 'PRI'),
    ('Bulky goods PostPac Economy', 'SP ECO'),
    ('Bulky goods PostPac Priority', 'SP PRI'),
    ('PostPac Promo', 'PPR'),
    ('Swiss-Express Mond', 'SEM'),
    ('Bulky goods Swiss-Express Mond', 'SP SEM'),
    ('Swiss-Kurier Blitz', 'SKB'),
    ('Bulky goods Swiss-Kurier Blitz', 'SP SKB'),
    ('Vinolog', 'VL'),
    ('Collection customer/receiver - pick-up', 'PICKUP'),
    ('Return shipment', 'RETOURE'),
    ('Fright/bulky goods Economy', 'LKW ECO'),
    ('Fright/small consignments Priority', 'LKW PRIO'),
    ('Fright/small consignments Express', 'LKW EXPRESS'),
]]


class delivery_carrier_ext(osv.Model):
    _inherit = 'delivery.carrier'

    _columns = {
        'yc_basic_shipping': fields.selection(_yc_basic_shipping_codes,
                                              'Basic products for YellowCube shipping',
                                              help='Mandatory for YellowCube'),
        'yc_additional_shipping': fields.char("Additional service in accordance with post parcels Postlogistics",
                                              help="SI; AS; BLN; SA; AZS, etc. Delimiter « ; » if more than one  element is available."),

        'pc_delivery_instructions': fields.char('Delivery Instructions', size=15),
        'pc_freight_shipping': fields.boolean('Is it used for bulk freight?'),
        'pc_shipping_interface': fields.selection([('WSBC', 'WSBC'),
                                                   ('WEBSTAMP', 'WEBSTAMP'),
                                                   ('FRIGHT', 'FRIGHT'),
                                                   ('GLSWEB', 'GLSWEB'),
                                                   ('PICKUP', 'PICKUP'),
                                                   ('MANUALLY', 'MANUALLY'),
                                                   ], string='Shipping Interface'),
    }

    def validate_yc_shipping_method(self, cr, uid, ids, context=None):
        for method in self.browse(cr, uid, ids, context):
            if not method.yc_basic_shipping:
                return False
            # Here we validate the values of additional shipping
            #  but, for now, any value is ok
        return True

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
