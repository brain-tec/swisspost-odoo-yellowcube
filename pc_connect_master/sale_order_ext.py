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

import openerp
from openerp.osv import osv, fields, orm
from utilities import filters
from openerp.addons.connector.session import ConnectorSession
from openerp.addons.connector.queue.job import job, related_action
from openerp.tools.translate import _
from utilities.pdf import associate_ir_attachment_with_object, get_pdf_from_report
import base64
import netsvc
import logging
logger = logging.getLogger(__name__)


class sale_order_ext(osv.Model):
    _inherit = 'sale.order'

    def _get_configuration_data(self, cr, uid, ids, context=None):
        return self.pool.get('configuration.data').get(cr, uid, [], context=context)

    # BEGIN OF THE CODE WHICH DEFINES THE NEW FILTERS TO ADD TO THE OBJECT.
    def _replace_week_placeholders(self, cr, uid, args, context=None):
        return filters._replace_week_placeholders(self, cr, uid, args, context=context)

    def _replace_quarter_placeholders(self, cr, uid, args, context=None):
        return filters._replace_quarter_placeholders(self, cr, uid, args, context=context)

    def search(self, cr, uid, args, offset=0, limit=None, order=None, context=None, count=False):
        return filters.search(self, cr, uid, args, sale_order_ext, offset=offset, limit=limit, order=order, context=context, count=count)

    def read_group(self, cr, uid, domain, fields, groupby, offset=0, limit=None, context=None, orderby=False):
        return filters.read_group(self, cr, uid, domain, fields, groupby, sale_order_ext, offset=offset, limit=limit, context=context, orderby=orderby)
    # END OF THE CODE WHICH DEFINES THE NEW FILTERS TO ADD TO THE OBJECT.

    def _prepare_invoice(self, cr, uid, order, lines, context=None):
        ''' Makes the journal of the invoice be the journal set up in the payment method which uses the sale order.
        '''
        invoice_vals = super(sale_order_ext, self)._prepare_invoice(cr, uid, order, lines, context=context)

        sale_order = self.browse(cr, uid, order.id, context)
        if sale_order.payment_method_id and sale_order.payment_method_id.journal_id:
            invoice_vals.update({'journal_id': sale_order.payment_method_id.journal_id.id})

        return invoice_vals

    def copy(self, cr, uid, ids, defaults={}, context=None):
        _defaults = {'invoices_printed': False,
                     'delivery_orders_printed': False,
                     'state': 'draft',
                     }
        _defaults.update(defaults)
        return super(sale_order_ext, self).copy(cr, uid, ids, _defaults, context=context)

    def create(self, cr, uid, values, context=None):
        """
        In case a sale order is created with a name, the standard sale order sequence name will be used,
        and the name that was established will be attached behind the sequence number, keeping both numeration
        (and been able of sorting by openerp sequence number)

        Sets the picking policy to be the one indicated in the configuration data.
        This is done in the default_get BUT it doesn't work when created through RPC,
        thus we add it to the create().
        """
        sequence = self.pool['ir.sequence'].next_by_code(cr, uid, "sale.order")
        if 'name' not in values:
            values['name'] = sequence
        else:
            values['name'] = "{0}-{1}".format(sequence, values["name"])

        values['picking_policy'] = self._defaults_picking_policy(cr, uid, None, values.get('picking_policy', None), context)

        logger.debug("{0}: {1}".format(uid, values))
        _id = super(sale_order_ext, self).create(cr, uid, values, context=context)
        return _id

    def check_credit(self, cr, uid, ids, context=None):
        ''' Checks whether the credit of the sale order is allowed by the payment.method and,
            perhaps, another considerations (to be defined).
        '''
        if context is None:
            context = {}
        ctx = context.copy()
        ctx['order_id'] = ids

        sale_order = self.browse(cr, uid, ids[0], context=context)
        return self.pool.get('res.partner').check_credit(cr, uid, sale_order.partner_id.id, sale_order.amount_total, context=ctx)

    def _check_payment_term(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        config = self.pool.get('configuration.data').get(cr, uid, [], context=context)
        for sale in self.browse(cr, uid, ids, context):
            if sale.state == 'draft':
                if (not sale.payment_term) or config.force_payment_term:
                    if sale.payment_method_id.payment_term_id:
                        write_payment_term = False
                        if (not sale.payment_term):
                            write_payment_term = True
                            message_to_post = _("Payment term was filled based on payment method  : '{0}'").format(sale.payment_method_id.payment_term_id.name)
                        elif (sale.payment_term.id != sale.payment_method_id.payment_term_id.id):
                            write_payment_term = True
                            message_to_post = _("Payment term was changed because Force payment term based on Payment method is checked: '{0}' -> '{1}'").format(sale.payment_term.name, sale.payment_method_id.payment_term_id.name)

                        if write_payment_term:
                            self.message_post(cr, uid, sale.id, body=message_to_post, context=context)
                            sale.write({'payment_term': sale.payment_method_id.payment_term_id.id})
        return True

    def print_and_attach_invoice_report(self, cr, uid, ids, context=None):
        ''' Prints and attaches the invoice reports for the invoices associated
            to this sale.order.
        '''

        if context is None:
            context = {}
        if not isinstance(ids, list):
            ids = [ids]

        result_success = True

        ir_attachment_obj = self.pool.get('ir.attachment')

        report_name = self._get_configuration_data(cr, uid, ids, context=context).report_account_invoice.report_name
        if not report_name:
            raise Exception(_("No report for account.invoice was found in SwissPost Connector > Reports"))

        sale_order = self.browse(cr, uid, ids[0], context=context)

        for invoice in sale_order.invoice_ids:
            file_name = invoice.get_file_name(context=context)
            if not ir_attachment_obj.search(cr, uid, [('res_model', '=', 'account.invoice'),
                                                      ('res_id', '=', invoice.id),
                                                      ('name', '=', file_name)]):

                pdf_data = get_pdf_from_report(cr, uid, 'report.' + report_name, {'ids': invoice.id, 'model': 'account.invoice'}, context=context)
                attach_id = associate_ir_attachment_with_object(self, cr, uid, pdf_data,
                                                                file_name, 'account.invoice', invoice.id)
                if attach_id:
                    ir_attachment_obj.write(cr, uid, attach_id, {'document_type': 'invoice_report'}, context=context)
                result_success = result_success and bool(attach_id)

        return result_success

    def print_and_attach_deliveryorder_report(self, cr, uid, ids, picking_to_print_id=0, context=None):
        ''' Prints and attaches the stock picking reports for the stock pickings associated
            to this sale.order provided that they are in the state 'assigned' or 'done'.

            If picking_to_print == 0, then we print all the delivery orders associated
            to the current sale.order. Otherwise we just print the picking with the provided ID
            (provided that it also belongs to the current sale.order).
        '''
        if context is None:
            context = {}
        if not isinstance(ids, list):
            ids = [ids]

        result_success = True

        ir_attachment_obj = self.pool.get('ir.attachment')
        stock_picking_obj = self.pool.get('stock.picking.out')

        stock_picking_domain = [('sale_id', 'in', ids),
                                ('state', 'in', ['assigned', 'done'])]
        if picking_to_print_id:
            stock_picking_domain.append((('id', '=', picking_to_print_id)))
        stock_picking_ids = stock_picking_obj.search(cr, uid, stock_picking_domain, context=context)

        if not stock_picking_ids:
            raise Exception(_("There are no associated delivery orders in state assigned or done for sale order with IDs={0}").format(','.join(map(str, ids))))

        report_name = self._get_configuration_data(cr, uid, ids, context=context).report_stock_picking.report_name
        if not report_name:
            raise Exception(_("No report for stock.picking was found in SwissPost Connector > Reports"))

        for stock_picking in stock_picking_obj.browse(cr, uid, stock_picking_ids, context=context):
            file_name = stock_picking.get_file_name()
            if not ir_attachment_obj.search(cr, uid, [('res_model', '=', 'stock.picking.out'),
                                                      ('res_id', '=', stock_picking.id),
                                                      ('name', '=', file_name)], context=context):

                pdf_data = get_pdf_from_report(cr, uid, 'report.' + report_name, {'ids': stock_picking.id, 'model': 'stock.picking.out'}, context=context)
                attach_id = associate_ir_attachment_with_object(self, cr, uid, pdf_data,
                                                                file_name, 'stock.picking.out', stock_picking.id)
                if attach_id:
                    ir_attachment_obj.write(cr, uid, attach_id, {'document_type': 'picking_out_report'}, context=context)
                result_success = result_success and bool(attach_id)
        return result_success

    def generate_reports(self, cr, uid, ids, context=None):
        '''
        This function returns a dictionary of attachments
        where the key is the model and the value is another dictionary
        where the key is the name of the attachment and the value is its id.
        '''
        if context is None:
            context = {}
        if not isinstance(ids, list):
            ids = [ids]

        self.print_and_attach_invoice_report(cr, uid, ids, context=context)
        self.print_and_attach_deliveryorder_report(cr, uid, ids, context=context)

        ir_attachment_obj = self.pool.get('ir.attachment')
        account_invoice_obj = self.pool.get('account.invoice')

        dict_invoices = {}
        dict_stk_picking = {}
        dict_attachments = {'account.invoice': dict_invoices, 'stock.picking': dict_stk_picking}

        # Collecting attachments for the invoices
        invoice_ids = []
        for sale_order in self.browse(cr, uid, ids, context=context):
            for invoice in sale_order.invoice_ids:
                invoice_ids.append(invoice.id)
        for invoice in account_invoice_obj.browse(cr, uid, invoice_ids, context=context):
            filename = invoice.get_file_name()
            for attachment_id in ir_attachment_obj.search(cr, uid, [('res_model', '=', 'account.invoice'),
                                                                    ('res_id', '=', invoice.id),
                                                                    ('name', '=', filename),
                                                                    ], context=context):
                dict_invoices[filename] = attachment_id

        # Collecting attachments for the delivery orders
        stock_picking_obj = self.pool.get('stock.picking')
        stock_picking_ids = stock_picking_obj.search(cr, uid, [('sale_id', 'in', ids)], context=context)
        for stock_picking in stock_picking_obj.browse(cr, uid, stock_picking_ids, context=context):
            filename = stock_picking.get_file_name()
            for attachment_id in ir_attachment_obj.search(cr, uid, [('res_model', '=', 'stock.picking'),
                                                                    ('res_id', '=', stock_picking.id),
                                                                    ('name', '=', filename),
                                                                    ], context=context):
                dict_stk_picking[filename] = attachment_id

        return dict_attachments

    def default_get(self, cr, uid, fields, context=None):
        ''' Sets the 'Shipping Policy' based on the configuration parameter.
            This doesn't work when creating the record through RPC.
        '''
        ret = super(sale_order_ext, self).default_get(cr, uid, fields, context)

        default_picking_policy = ret.get('picking_policy', 'one')
        ret['picking_policy'] = self._defaults_picking_policy(cr, uid, None, default_picking_policy, context)

        return ret

    def _defaults_picking_policy(self, cr, uid, ids, default_picking_policy=None, context=None):
        ''' Sets the 'Shipping Policy' based on the configuration parameter.
            Call it from create() also, otherwise just from default_get doesn't work through RPC.
        '''
        configuration = self.pool.get('configuration.data').get(cr, uid, [], context=context)

        if configuration.default_picking_policy in ('keep', False, None):
            picking_policy = default_picking_policy or 'one'
        elif configuration.default_picking_policy in ('one', 'direct'):
            picking_policy = configuration.default_picking_policy

        return picking_policy

    def has_backorder(self, cr, uid, ids, context=None):
        ''' Returns whether the current sale.order has any stock.picking
            which is a backorder.

            MUST be called just over ONE id. If ids is a list, it takes just the
            first element.
        '''
        if context is None:
            context = {}
        if not isinstance(ids, list):
            ids = [ids]

        sale_order = self.browse(cr, uid, ids[0], context=context)
        return any([picking.backorder_id for picking in sale_order.picking_ids])

    _columns = {
        'invoices_printed': fields.boolean('The invoices have been printed', help='Have the invoices been printed?'),
        'delivery_orders_printed': fields.boolean('The delivery order have been printed', help='Have the delivery orders been printed?'),
        'automation_finished': fields.boolean('Has Automation Finished?', help='Indicates if the sale.order automation has reached its last state and finished.'),

        # Overrides this existing field to make it required=True.
        'payment_method_id': fields.many2one('payment.method', 'Payment Method', ondelete='restrict', required=True),

        # Gift-text fields.
        'additional_message_type': fields.many2one('gift.text.type', 'Gift Text Type'),
        'additional_message_content': fields.text('Message Content', size=2000, translate=True, required=False, help='Content of the gift-text.'),

        # Fields required by the shops.
        'delivery_date': fields.date(string="delivery_date"),
        'delivery_time_jit': fields.char(string="delivery_time_jit", size=5),
        'delivery_location': fields.char(string="delivery_location", size=35),
        'delivery_notification_type': fields.selection([('TEL', 'TEL'),
                                                        ('FAX', 'FAX'),
                                                        ('SMS', 'SMS'),
                                                        ('EMAIL', 'EMAIL'),
                                                        ], string="delivery_notification_type"),
    }

    _defaults = {
        'invoices_printed': False,
        'delivery_orders_printed': False,
        'automation_finished': False,
    }

    _constraints = [
        (_check_payment_term, _('Error: Payment term must be set.'), ['payment_method_id']),
    ]

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
