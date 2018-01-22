# b-*- encoding: utf-8 -*-
##############################################################################
#
#    Copyright (c) 2015 brain-tec AG (http://www.braintec-group.com)
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
from openerp.tools import DEFAULT_SERVER_DATETIME_FORMAT
from openerp.tools.translate import _
from ..sale_order_ext import automate_sale_order_process
import time
from datetime import datetime
from openerp.addons.connector.session import ConnectorSession


class sale_order_automation_joiner(osv.TransientModel):
    _name = 'sale.order.automation_wiz'

    _columns = {
        'when': fields.datetime(string="When to execute", required=True),
        'order_id': fields.many2one('sale.order', string='Sale order to automatise', required=True, readonly=True),
        'state': fields.selection([('saleorder_check_inventory_for_quotation', '1) saleorder_check_inventory_for_quotation'),
                                   ('saleorder_checkcredit', '2) saleorder_checkcredit'),
                                   ('saleorder_draft', '3) saleorder_draft'),
                                   ('saleorder_sent', '4) saleorder_sent'),
                                   ('deliveryorder_assignation_one', '5) deliveryorder_assignation_one'),
                                   ('deliveryorder_assignation_direct', '5) deliveryorder_assignation_direct'),
                                   ('deliveryorder_assignation_dropship', '5) deliveryorder_assignation_dropship'),
                                   ('do_multi_parcel_deliveries', '6) do_multi_parcel_deliveries'),
                                   ('print_deliveryorder_in_local', '7) print_deliveryorder_in_local'),
                                   ('invoice_open', '8) invoice_open'),
                                   ('print_invoice_in_local', '9) print_invoice_in_local'),
                                   ],
                                  required=True, string='State to force')
    }

    def do_join(self, cr, uid, ids, context=None):
        for wiz in self.browse(cr, uid, ids, context=context):
            session = ConnectorSession(cr, uid, context)
            print wiz.when
            automate_sale_order_process.delay(session,
                                              'sale.order',
                                              wiz.order_id.id,
                                              wiz.state,
                                              priority=wiz.order_id.get_soa_priority(),
                                              eta=datetime.strptime(wiz.when, DEFAULT_SERVER_DATETIME_FORMAT))
        return

    _defaults = {
        'order_id': lambda s, cr, ui, ct: ct.get('active_id', False) or ct.get('active_ids', [False])[0],
        'when': lambda *a: time.strftime(DEFAULT_SERVER_DATETIME_FORMAT),
    }

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
