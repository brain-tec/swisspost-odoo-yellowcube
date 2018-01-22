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
from openerp.addons.pc_connect_master.utilities.reports import \
    get_pdf_from_report, \
    associate_ir_attachment_with_object
from openerp.tools.translate import _
from openerp.tools.safe_eval import safe_eval
import logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)



class sale_order_ext(osv.Model):
    _inherit = 'sale.order'

    def print_deliveryorder_in_local_after(self, cr, uid, ids, picking_id=0, context=None):
        ''' Once the delivery order has been printed in local, here we
            print and attach the barcode report.

            We can skip the printing if the variable skip_barcode_printing is set to True in the
            system's parameter. 
        '''
        if context is None:
            context = {}
        sale_order_id = ids
        if type(sale_order_id) is list:
            sale_order_id = sale_order_id[0]

        result_success = True

        if safe_eval(self.pool.get('ir.config_parameter').get_param(cr, uid, 'skip_barcode_printing', 'False')):
            return result_success

        ir_attachment_obj = self.pool.get('ir.attachment')
        stock_picking_obj = self.pool.get('stock.picking')

        stock_picking_domain = [('sale_id', '=', sale_order_id),
                                ('state', '=', 'assigned')]
        if picking_id:
            stock_picking_domain.append(('id', '=', picking_id))
        stock_picking_ids = stock_picking_obj.search(cr, uid, stock_picking_domain, context=context)
        for stock_picking_id in stock_picking_ids:

            # We only generate the barcode report if the carrier of the picking has its type set.
            stock_picking = stock_picking_obj.browse(cr, uid, stock_picking_id, context=context)
            if stock_picking.carrier_id.type:
                barcode_report_name = stock_picking_obj.get_file_name_barcode(cr, uid, stock_picking_id, context=context)
                if not ir_attachment_obj.search(cr, uid, [('res_model', '=', 'stock.picking.out'),
                                                          ('res_id', '=', stock_picking_id),
                                                          ('name', '=', barcode_report_name),
                                                          ], limit=1, count=True, context=context):
                    pdf_data = get_pdf_from_report(cr, uid, 'report.barcode_label_report', {'ids': stock_picking_id, 'model': 'stock.picking.out'}, context=context)
                    attach_id = associate_ir_attachment_with_object(self, cr, uid, pdf_data,
                                                                    barcode_report_name, 'stock.picking.out', stock_picking_id)
                    pdf_data = None

                    if attach_id:
                        ir_attachment_obj.write(cr, uid, attach_id, {'document_type': 'barcode_out_report'}, context=context)
                    result_success = result_success and bool(attach_id)

            else:
                logger.warning(_('Carrier of picking with ID={0} does not have a type set, thus the barcode report can not be generated.').format(stock_picking_id))

        super_result_success = \
            super(sale_order_ext, self).print_deliveryorder_in_local_after(
                cr, uid, ids, picking_id=0, context=context)
        return result_success and super_result_success

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
