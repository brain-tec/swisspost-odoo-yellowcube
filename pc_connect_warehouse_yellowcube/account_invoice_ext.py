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

from openerp.osv import osv, fields, orm
from openerp.tools.translate import _
from openerp.tools import DEFAULT_SERVER_DATETIME_FORMAT


class account_invoice_ext(osv.Model):
    _inherit = 'account.invoice'

    def get_filename_for_wab(self, cr, uid, ids, context=None):
        ''' Gets the filename for the invoice file that is attached in the WAB,
            in the format the WAB expects.
        '''
        if context is None:
            raise Warning('context is missing when calling method get_filename_for_wab over account.invoice, and is required in this case.')
        if type(ids) is not list:
            ids = [ids]

        invoice = self.browse(cr, uid, ids[0], context=context)

        order_name = context['yc_customer_order_no']
        depositor_id = context['yc_sender']

        doc_type = 'ZS'

        order_date = invoice.sale_ids[0].date_order
        order_date = order_date.split(' ')[0]  # Just in case date has attached the hh:mm:ss
        yyyy, mm, dd = order_date.split('-')
        yymmdd = '{yy}{mm}{dd}'.format(yy=yyyy[-2:], mm=mm, dd=dd)

        order_number = order_name

        file_name = '{depositor_id}_{doc_type}{order_number}_{yymmdd}.pdf'.format(depositor_id=depositor_id,
                                                                                  doc_type=doc_type,
                                                                                  order_number=order_number,
                                                                                  yymmdd=yymmdd)
        return file_name

    def get_attachment_wab(self, cr, uid, ids, context=None):
        ''' Returns a dictionary of the type
            <KEY=output_filename, VALUE=original_path_of_attachment>
            with as many keys as invoice-related attachments need to
            be exported on the WAB.

            IDs must be an integer, or a list of just one ID (otherwise
            just the first element is taken into account).
        '''
        if context is None:
            context = {}
        if type(ids) is not list:
            ids = [ids]

        result = {}

        ir_attachment_obj = self.pool.get('ir.attachment')
        ir_config_parameter_obj = self.pool.get('ir.config_parameter')

        attachments_location = ir_config_parameter_obj.get_param(cr, uid, 'ir_attachment.location')

        account_invoice = self.browse(cr, uid, ids[0], context=context)

        att_ids = ir_attachment_obj.search(cr, uid, [('res_id', '=', account_invoice.id),
                                                     ('res_model', '=', 'account.invoice'),
                                                     ('document_type', '=', 'invoice_report'),
                                                     ], context=context)
        if len(att_ids) != 1:
            if context.get('yc_min_number_attachments') != 0:
                raise Warning(_('A bad number of invoice reports was found ({0}) '
                                'for invoice with ID={1}, while just one was expected').format(len(att_ids),
                                                                                               account_invoice.id))
            else:
                return result

        output_filename = account_invoice.get_filename_for_wab()
        att = ir_attachment_obj.browse(cr, uid, att_ids[0], context=context)
        result[output_filename] = ir_attachment_obj._full_path(cr, uid, attachments_location, att.store_fname)

        return result

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
