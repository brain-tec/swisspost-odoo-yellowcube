# b-*- encoding: utf-8 -*-
##############################################################################
#
#    Copyright (c) 2017 brain-tec AG (http://www.braintec-group.com)
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
from datetime import datetime


class account_invoice_ext(osv.Model):
    _inherit = 'account.invoice'

    def check_send_invoice_to_docout(self, cr, uid, ids, context=None):
        """ Indicates if the invoice will be sent to the doc-out or not.
        """
        if context is None:
            context = {}
        if type(ids) is not list:
            ids = [ids]

        order_obj = self.pool.get('sale.order')

        # In our code, we have always just ONE sale.order for any invoice,
        # (although a sale order may have several invoices)
        order_ids = order_obj.search(cr, uid, [('invoice_ids', 'in', ids)],
                                     limit=1, context=context)
        order = order_obj.browse(cr, uid, order_ids[0], context=context)

        is_epaid = order.payment_method_id.epayment
        addresses_are_different = \
            order.partner_invoice_id.id != order.partner_shipping_id.id
        invoice_policy = order.invoice_policy
        picking_policy = order.picking_policy

        # NOTE:
        # In the specs, the number of pickings matters also,
        # however it's not taken into account because it's actually not
        # important, since if invoice_policy == 'order' then just an invoice
        # is used, and if invoice_policy == 'delivery' then we have as
        # many invoices as pickings are created, thus the number of
        # pickings condition is implicit in the condition for
        # the invoice_policy.

        send_invoice_to_docout = \
            addresses_are_different and \
            (not is_epaid) and \
            ((invoice_policy == 'order') or
             (invoice_policy == 'delivery' and picking_policy == 'direct'))

        if send_invoice_to_docout:
            # New requirement in t7051: if the BVR is filled with XXXs, then
            # don't send it to the doc-out.
            if not self.show_bvr(cr, uid, ids, context=context):
                send_invoice_to_docout = False

        return send_invoice_to_docout

    def mark_invoice_to_be_sent_to_docout(self, cr, uid, ids, attach_tags=None, context=None):
        """ Marks the invoices to be sent to the doc-out.
        """
        if context is None:
            context = {}
        if type(ids) is not list:
            ids = [ids]

        attach_obj = self.pool.get('ir.attachment')
        attach_tags_obj = self.pool.get('ir.attachment.tag')

        # Searches for the attachments of the invoice to be sent.
        search_domain = [
            ('res_model', '=', 'account.invoice'),
            ('res_id', 'in', ids),
        ]
        if attach_tags:
            att_tags_ids = attach_tags_obj.search(cr, uid, [
                ('name', 'in', attach_tags),
            ], context=context)
            search_domain.append(('tags_ids', 'in', att_tags_ids))
        attach_ids = attach_obj.search(
            cr, uid, search_domain, context=context)

        for attach in attach_obj.browse(cr, uid, attach_ids, context=context):

            docout_exported_file_name = attach.get_docout_exported_file_name()

            write_values = {
                'docout_file_type': 'invoice',
                'docout_exported_file_name_email':
                    docout_exported_file_name,
                'docout_exported_file_name_remote_folder':
                    docout_exported_file_name,
            }

            # We are adding those conditions because we may call this
            # method several times, and we don't want to send an
            # invoice to the doc-out more than one time, or send it
            # if we marked it to be skipped.
            additional_write_values = {}
            if attach.docout_state_email not in ('sent', 'skipped'):
                additional_write_values.update(
                    {'docout_state_email': 'to_send'})
            if attach.docout_state_remote_folder not in ('sent', 'skipped'):
                additional_write_values.update(
                    {'docout_state_remote_folder': 'to_send'})

            if additional_write_values:
                write_values.update(additional_write_values)
                attach.write(write_values)

        return True

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
