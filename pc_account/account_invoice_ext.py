# b-*- encoding: utf-8 -*-
##############################################################################
#
#    Copyright (c) 2014 brain-tec AG (http://www.braintec-group.com)
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
from openerp.addons.report_webkit import report_helper
from openerp.addons.pc_generics import generics


@generics.has_mako_header()
class account_invoice_ext(osv.Model):
    _inherit = "account.invoice"

    def get_sale_order_ids(self, cr, uid, ids, context=None):
        """ Gets the ID of the sale order associated to this invoice, or False if it has no
            sale order associated.
        """
        if context is None:
            context = {}
        if type(ids) is not list:
            ids = [ids]

        invoice = self.browse(cr, uid, ids[0], context=context)
        if invoice.type == 'out_refund':
            sale_order_ids = invoice.refunded_invoice_id and invoice.refunded_invoice_id.sale_ids or False
        else:
            sale_order_ids = invoice.sale_ids
        return sale_order_ids

    def is_partial_invoice(self, cr, uid, ids, context=None):
        ''' Returns True if an invoice is not unique for the given sale order.
        '''
        if context is None:
            context = {}

        # Gets the sale order this invoice comes from, if any
        is_partial_invoice = False
        invoice = self.pool.get('account.invoice').browse(cr, uid, ids, context=context)[0]
        if invoice.sale_ids and len(invoice.sale_ids) > 0:
            sale_order = invoice.sale_ids[0]
            if len(sale_order.invoice_ids) > 1:
                is_partial_invoice = True
        return is_partial_invoice

    def invoice_print(self, cr, uid, ids, context=None):
        if context is None:
            context = {}

        datas = {'ids': ids,
                 'model': 'account.invoice',
                 'form': self.read(cr, uid, ids[0], context=context)
                 }
        return {'type': 'ir.actions.report.xml',
                'report_name': 'invoice.report',
                'datas': datas,
                'nodestroy': True,
                'context': context,
                }

    def ending_text(self, cr, uid, ids, type_, context=None):
        ''' Return the ending text
        '''
        ending_text = ""
        conf_data = self.pool.get('configuration.data').get(cr, uid, [], context=context)
        if type_ == 'out_refund' or type_ == 'in_refund':
            ending_text = conf_data.invoice_ending_text_for_refunds or ''
        elif self.is_epaid(cr, uid, ids, context):
            ending_text = conf_data.invoice_ending_text_with_epayment or ''
        else:
            ending_text = conf_data.invoice_ending_text_without_epayment or ''

        return ending_text

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
