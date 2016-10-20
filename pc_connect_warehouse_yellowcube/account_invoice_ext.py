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

from openerp.osv import osv, fields, orm
from openerp.tools.translate import _
from openerp.tools import DEFAULT_SERVER_DATETIME_FORMAT
from openerp import api
from openerp.addons.pc_connect_master.utilities.pdf import concatenate_pdfs
from tempfile import mkstemp
import os
import base64
import logging
logger = logging.getLogger(__name__)


class account_invoice_ext(osv.Model):
    _inherit = 'account.invoice'

    def get_filename_for_wab(self, cr, uid, ids, extension, context=None):
        ''' Gets the filename for the invoice file that is attached in the WAB,
            in the format the WAB expects.
        '''
        if context is None:
            raise Warning('context is missing when calling method get_filename_for_wab over account.invoice, and is required in this case.')
        if not isinstance(ids, list):
            ids = [ids]

        invoice = self.browse(cr, uid, ids[0], context=context)

        order_name = context['yc_customer_order_no']
        depositor_id = context['yc_sender']

        doc_type = 'IV'

        order_date = invoice.sale_ids[0].date_order
        order_date = order_date.split(' ')[0]  # Just in case date has attached the hh:mm:ss
        yyyy, mm, dd = order_date.split('-')
        yymmdd = '{yy}{mm}{dd}'.format(yy=yyyy[-2:], mm=mm, dd=dd)

        order_number = order_name

        file_name = '{depositor_id}_{doc_type}{order_number}_{yymmdd}.{ext}'.format(depositor_id=depositor_id,
                                                                                    doc_type=doc_type,
                                                                                    order_number=order_number,
                                                                                    yymmdd=yymmdd,
                                                                                    ext=extension)
        return file_name

    def get_attachment_wab(self, cr, uid, ids, extension='pdf', context=None):
        ''' Returns a dictionary of the type
            <KEY=output_filename, VALUE=original_path_of_attachment>
            with as many keys as invoice-related attachments need to
            be exported on the WAB.

            IDs must be an integer, or a list of just one ID (otherwise
            just the first element is taken into account).
        '''
        if context is None:
            context = {}
        if not isinstance(ids, list):
            ids = [ids]

        result = {}

        number_of_attachments_to_use = context.\
            get('yc_attachments_from_invoice', 1)
        if number_of_attachments_to_use == 0:
            return {}

        ir_attachment_obj = self.pool.get('ir.attachment')
        ir_config_parameter_obj = self.pool.get('ir.config_parameter')

        attachments_location = ir_config_parameter_obj.get_param(cr, uid, 'ir_attachment.location')

        account_invoice = self.browse(cr, uid, ids[0], context=context)

        att_picking_ids = ir_attachment_obj.search(cr, uid, [
            ('res_id', '=', account_invoice.id),
            ('res_model', '=', 'account.invoice'),
        ], order='create_data DESC', limit=number_of_attachments_to_use,
                                           context=context)
        if len(att_picking_ids) == 0:
            logger.warning(_('A bad number of picking reports was found '
                             '({0}) on invoice with ID={1}, '
                             'while at least one was expected')
                           .format(len(att_picking_ids), account_invoice.id))
            return result

        output_filename = account_invoice.get_filename_for_wab(extension)

        if len(att_picking_ids) == 1:
            attachment_to_send_id = att_picking_ids[0]
        else:
            attachment_to_send_id = account_invoice.\
                _get_attachment_id_for_invoices_concatenated\
                (att_picking_ids, extension)

        att = ir_attachment_obj.browse(cr, uid, attachment_to_send_id,
                                       context=context)
        result[output_filename] = ir_attachment_obj._full_path(cr, uid,
                                                               att.store_fname)

        return result


    def _get_attachment_id_for_invoices_concatenated(self, cr, uid, ids,
                                                     att_picking_ids, extension,
                                                     context=None):
        ''' Returns the ID of the attachment which consist of the concatenation of the picking and barcode attachments
            the ID of which is received as arguments. If the attachment doesn't exist, it creates it; otherwise just
            returns it.
        '''
        if context is None:
            context = {}
        if type(ids) is not list:
            ids = [ids]

        ir_attachment_obj = self.pool.get('ir.attachment')
        ir_config_parameter_obj = self.pool.get('ir.config_parameter')

        invoice = self.browse(cr, uid, ids[0], context=context)

        if 'output_filename' not in context:
            output_filename = invoice.get_filename_for_wab(extension)
        else:
            output_filename = context['output_filename']
        attachments_location = ir_config_parameter_obj.get_param(cr, uid, 'ir_attachment.location')

        # First we check if we already have the attachment. If we don't have it, we create it.
        att_ids = ir_attachment_obj.search(cr, uid, [('res_id', '=', invoice.id),
                                                     ('res_model', '=', 'account.invoice'),
                                                     ('name', '=', output_filename),
                                                     ], limit=1, context=context)
        if att_ids:
            attachment_id = att_ids[0]
        else:
            try:
                # First, we create a temporary PDF file having the content of the concatenation.
                fd, tmp_path = mkstemp(prefix='concatenated_invoices_', dir="/tmp")
                paths_of_files_to_concatenate = []
                for att_to_concatenate in ir_attachment_obj.browse(cr, uid, att_picking_ids, context=context):
                    att_to_concatenate_full_path = ir_attachment_obj._full_path(cr, uid, attachments_location, att_to_concatenate.store_fname)
                    paths_of_files_to_concatenate.append(att_to_concatenate_full_path)
                concatenate_pdfs(tmp_path, paths_of_files_to_concatenate)

                # Then we create an attachment with the content of that file.
                with open(tmp_path, "rb") as f:
                    attachment_content_base64 = base64.b64encode(f.read())
                values_create_att = {
                    'name': output_filename,
                    'datas': attachment_content_base64,
                    'datas_fname': output_filename,
                    'res_model': 'account.invoice',
                    'res_id': invoice.id,
                    'type': 'binary',
                    'description':
                        _('Attachment for invoice with ID={0}. '
                          'Autogenerated from attachments: {1}'.format(
                            invoice.id,
                            ', '.join(map(str, att_picking_ids))
                        )),
                }
                attachment_id = ir_attachment_obj.create(cr, uid, values_create_att, context=context)

            finally:
                if fd:
                    os.close(fd)
                if tmp_path:
                    os.remove(tmp_path)

        return attachment_id

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
