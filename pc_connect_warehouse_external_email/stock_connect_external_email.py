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

from openerp.osv import osv, fields, orm
from openerp.tools.translate import _
from openerp.addons.pc_connect_master.utilities.others import format_exception
from openerp.addons.pc_connect_warehouse.stock_event import EVENT_STATE_DONE, EVENT_STATE_DRAFT, EVENT_STATE_IGNORED
from openerp.addons.pc_connect_master.utilities.pdf import concatenate_pdfs
from openerp import SUPERUSER_ID
from openerp.addons.pc_connect_master.utilities.reports import \
    get_pdf_from_report, \
    associate_ir_attachment_with_object

from tempfile import mkstemp

import os
from datetime import datetime

import logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


class stock_connect_external_email(osv.Model):
    _name = "stock.connect.external_email"
    _inherit = 'stock.connect'

    def connection_get_files(self, cr, uid, ids, context=None):
        ''' In this connector, we receive files from nowhere.
        '''
        logger.debug(_('connection_get_files does nothing if stock.connect.type is external_email.'))
        return True

    def connection_process_files(self, cr, uid, ids, context=None):
        ''' In this connector, we don't process any files,
            since we do not receive any.
        '''
        logger.debug(_('connection_process_files does nothing if stock.connect.type is external_email.'))
        return True

    def connection_process_events(self, cr, uid, ids, context=None):
        ''' Process the events. In our case, for each stock.picking
            which is assigned, we must create a stock.connect.file
            with the information to be send in the email, and its
            attachments.
        '''
        if context is None:
            context = {}
        if type(ids) is not list:
            ids = [ids]

        stock_event_obj = self.pool.get('stock.event')
        stock_connect_obj = self.pool.get('stock.connect')

        this = stock_connect_obj.browse(cr, uid, ids[0], context)

        func_dir = self.get_function_mapping()

        # Sets to be ignored all those events which have an event code
        # which must be ignored and which are not yet ignored.
        event_codes_to_ignore = this.get_event_codes_to_ignore()
        event_to_ignore_ids = stock_event_obj.search(cr, uid, [
            ('event_code', 'in', event_codes_to_ignore),
            ('warehouse_id', 'in', [x.id for x in this.warehouse_ids]),
            ('state', '!=', EVENT_STATE_IGNORED),
            ('error', '=', False),
        ], context=context)

        if event_to_ignore_ids:
            stock_event_obj.write(cr, uid, event_to_ignore_ids, {'state': EVENT_STATE_IGNORED}, context)

        logger.debug("Started checking events on connections.")

        for connect in stock_connect_obj.browse(cr, uid, ids, context):
            for warehouse in connect.warehouse_ids:
                for event_code in func_dir:

                    # It is the function passed in the parameter 'func' which must
                    # deal with the exception, not this code.
                    try:
                        self._process_event(cr,
                                            uid,
                                            [connect.id],
                                            func=func_dir[event_code],
                                            event_code=event_code,
                                            warehouse_id=warehouse.id,
                                            context=context)
                    except Exception as e:
                        # _process_event must raise, but just in case...
                        raise

        logger.debug("Finished checking events on connections.")
        return True

    def get_function_mapping(self):
        return {
            'new_picking_state_assigned': self._process_stock_picking_assigned,
        }

    def connection_send_files(self, cr, uid, ids, context=None):
        ''' Takes each stock.connect.file which is not yet processed and
            generates an email, adding the templates generated to it,
            and then calls the schedulers which will try to send the emails.
        '''
        if context is None:
            context = {}

        logger.debug("Start sending files.")

        file_obj = self.pool.get('stock.connect.file')
        project_issue_obj = self.pool.get('project.issue')

        configuration_data = self.pool.get('configuration.data').get(cr, uid, None, context)

        invoice_to_external_warehouse_email_template_id = configuration_data.email_connector_email_template_id.id

        if invoice_to_external_warehouse_email_template_id:
            file_ids = file_obj.search(cr, uid, [('state', '=', 'draft'),
                                                 ], context=context)

            if file_ids:
                mail_template_obj = self.pool.get("email.template")
                mail_mail_obj = self.pool.get('mail.mail')

                for connect_file in file_obj.browse(cr, uid, file_ids, context):
                    new_cr = self.pool.db.cursor()
                    try:
                        values = mail_template_obj.generate_email(cr, uid, invoice_to_external_warehouse_email_template_id, connect_file.id, context=context)
                        values.update({'stock_connect_id': connect_file.stock_connect_id.id})
                        msg_id = mail_mail_obj.create(cr, uid, values, context=context)

                        list_attachments = []
                        for att in connect_file.attachments:
                            list_attachments.append(att._id)

                        mail_mail_obj.write(cr, uid, msg_id, {'attachment_ids': [(6, 0, list_attachments)]}, context=context)

                        connect_file.write({'state': 'done'})

                    except Exception as e:
                        error_message = format_exception(e)
                        logger.error(error_message)
                        project_issue_obj.create_issue(cr, uid, 'stock.connect.file', connect_file.id, error_message, tags=['warehouse'], context=context)
                        file_obj.write(new_cr, uid, connect_file.id, {'error': True,
                                                                      'info': error_message,
                                                                      }, context=context)
                        raise

                    finally:
                        new_cr.commit()
                        new_cr.close()

        logger.debug("Finished sending files.")

        return True

    def attach_of_invoice_to_email_is_required(self, cr, uid, ids, picking, context=None):
        """ Indicates if the invoice has to be attached to the email which is created and which is
            linked to the stock.connect.file which is created.
        """
        invoice_policy = picking.sale_id.invoice_policy
        has_epayment = picking.sale_id.payment_method_id.epayment
        equal_invoice_and_shipping_address = (picking.sale_id.partner_shipping_id == picking.sale_id.partner_invoice_id)

        attach_invoice_to_email = (not has_epayment) and \
            equal_invoice_and_shipping_address and \
            (picking.is_full_delivery() or invoice_policy == 'delivery')

        return attach_invoice_to_email

    def _process_stock_picking_assigned(self, cr, uid, ids, event_ids, context=None):
        ''' This function processes the events received.
                In this case, it generates a stock.connect.file containing the
            body of the email to be sent, and its attachments.
        '''
        if context is None:
            context = {}
        context['check_date_ready_for_export'] = True

        logger.debug("Start processing assigned stock pickings")

        location = self.pool.get('ir.config_parameter').get_param(cr, uid, 'ir_attachment.location')

        picking_obj = self.pool.get('stock.picking')
        stock_event_obj = self.pool.get('stock.event')
        ir_attachment_obj = self.pool.get('ir.attachment')
        account_invoice_obj = self.pool.get('account.invoice')
        file_obj = self.pool.get('stock.connect.file')
        project_issue_obj = self.pool.get('project.issue')

        ret = []

        # Used to display the information in a way that makes the user able to find quickly a
        # file within the list of files.
        # The key is the 'sale_order_name': The name of the sale order.
        # Each dictionary will store the following variables:
        #   'invoice_attachm_full_path': The list of the full paths to the attachments of the invoices associated to the sale.order.
        #   'picking_attachm_full_path': The list of the full paths to the attachments of the delivery slips associated to the sale.order.
        #   'barcode_attachm_full_path': The list of the full paths to the attachments of the barcode reports associated to the picking of the sale.order.
        #   'picking_id': The list of IDs of the pickings associated to this sale.order, for convenience.
        # This way, we can sort afterwards for the name of the sale.order.
        sale_orders_to_include = {}

        # This set is to ensure that we don't send an invoice's attachment more than once, and that we can do
        # the check in a fast way. For instance, if two pickings share the same sale order, it can
        # be that they share the same invoice.
        invoices_full_paths = set()

        # Stores events to be ignored & errored, which are those ones belonging
        # to a picking which was manually removed.
        events_picking_removed_ids = []

        events_ignored_ids = []  # Stores the events to be ignored.
        events_to_process_ids = []  # Stores the events to process.

        # Filters the events to process and to ignore.
        for event_id in event_ids:
            event = stock_event_obj.browse(cr, uid, event_id, context=context)

            # It can happen that the picking related to the event has been
            # manually removed (should never happen, but has happened
            # in the past, so we prepare for it.)
            if not picking_obj.search(cr, SUPERUSER_ID,
                                      [('id', '=', event.res_id),
                                       ], context=context, limit=1):
                events_picking_removed_ids.append(event_id)
            else:
                picking = picking_obj.browse(cr, uid, event.res_id, context)

                if picking.do_not_send_to_warehouse:
                    events_ignored_ids.append(event_id)
                elif picking.state == 'assigned':
                    events_to_process_ids.append(event_id)
                else:
                    # If the picking.state is not assigned, it must not
                    # be processed, but checked next time the pickings
                    # are processed
                    pass

        # Sets to ignored and errored all those events belonging to a
        # picking which was not found.
        if events_picking_removed_ids:
            stock_event_obj.write(
                cr, uid, events_picking_removed_ids,
                {'state': EVENT_STATE_IGNORED,
                 'error': True,
                 'info': _('Event was marked as being ignored and errored '
                           'because the picking was not found.'),
                 }, context=context)
        # Sets to ignored all the events which were marked as ignored.
        if events_ignored_ids:
            stock_event_obj.write(cr, uid, events_ignored_ids, {'state': EVENT_STATE_IGNORED, 'info': _('Event was marked as being ignored.')}, context)

        if events_to_process_ids:
            first_event_id = events_to_process_ids[0]

        # Process the events which do not have to be ignored.
        # Collect all attachments (invoice and delivery_order) in lists
        for event in stock_event_obj.browse(cr, uid, events_to_process_ids, context=context):
            try:
                new_cr = self.pool.db.cursor()

                send_invoice = False
                send_picking = False

                invoice_attachment_full_path = False
                delivery_order_attachment_full_path = False
                barcode_attachment_full_path = False

                picking = picking_obj.browse(cr, uid, event.res_id, context)

                # If the picking is associated to a sale order which was automated, but its automation did
                # not finished yet, or it was not ready for export yet, we don't process it yet.
                if (not picking.sale_id.automation_finished) or \
                   (not picking.ready_for_export):
                    warning_message = 'Event with ID {event_id} for picking {picking} (ID={picking_id}) ' \
                                      'was not be processed yet'.format(event_id=event.id,
                                                                        picking=picking.name,
                                                                        picking_id=picking.id)
                    logger.warning(warning_message)
                    event.write({'info': warning_message})
                    continue

                if self.attach_of_invoice_to_email_is_required(cr, uid, ids, picking, context=context):
                    # There should be just one invoice if invoice_policy is 'order', otherwise we complain.
                    num_invoices = 0 if (not picking.sale_id.invoice_ids) else len(picking.sale_id.invoice_ids)
                    if picking.sale_id.invoice_policy == 'order' and num_invoices != 1:
                        raise orm.except_orm(_('Bad Number of Invoices'),
                                             _('Stock picking with ID={0} comes from sale order with ID={1} which has {2} invoices, while just one is allowed.').format(picking.id,
                                                                                                                                                                        picking.sale_id.id,
                                                                                                                                                                        num_invoices))
                    elif picking.sale_id.invoice_policy == 'delivery' and num_invoices < 1:
                        raise orm.except_orm(_('Bad Number of Invoices'),
                                             _('Stock picking with ID={0} comes from sale order with ID={1} which has {2} invoices, while at least one is required.').format(picking.id,
                                                                                                                                                                             picking.sale_id.id,
                                                                                                                                                                             num_invoices))

                    if picking.sale_id.invoice_policy == 'delivery':
                        # If we have a partial invoice for each partial delivery, then we get the invoice associated to the picking.
                        invoice_to_use_id = picking.invoice_id.id
                    else:  # if picking.sale_id.invoice_policy == 'order':
                        # If we just have an invoice for all the order, then we get the invoice through the sale order instead.
                        invoice_to_use_id = picking.sale_id.first_invoice_id.id

                    invoice_file_name = account_invoice_obj.get_file_name(cr, uid, invoice_to_use_id, context=context)
                    invoice_attachment_ids = ir_attachment_obj.search(cr, uid, [('name', '=', invoice_file_name)], limit=1, context=context)
                    if invoice_attachment_ids:
                        invoice_attachment = ir_attachment_obj.browse(cr, uid, invoice_attachment_ids[0], context=context)
                        invoice_attachment_full_path = ir_attachment_obj._full_path(cr, uid, location, invoice_attachment.store_fname)
                        send_invoice = True

                # We only send the picking if the invoice is not going to be attached.
                else:
                    delivery_order_file_name = picking.get_file_name()
                    delivery_order_attachment_ids = ir_attachment_obj.search(cr, uid, [('name', '=', delivery_order_file_name)], limit=1, context=context)
                    if delivery_order_attachment_ids:
                        delivery_order_attachment = ir_attachment_obj.browse(cr, uid, delivery_order_attachment_ids[0], context=context)
                        delivery_order_attachment_full_path = ir_attachment_obj._full_path(cr, uid, location, delivery_order_attachment.store_fname)
                        send_picking = True

                # We attach the barcode report for all the pickings.
                barcode_file_name = picking.get_file_name_barcode()
                barcode_attachment_ids = ir_attachment_obj.search(cr, uid, [('name', '=', barcode_file_name)], limit=1, context=context)
                if barcode_attachment_ids:
                    barcode_attachment = ir_attachment_obj.browse(cr, uid, barcode_attachment_ids[0], context=context)
                    barcode_attachment_full_path = ir_attachment_obj._full_path(cr, uid, location, barcode_attachment.store_fname)

                # Only if we send the delivery_order OR the invoice, we add the sale order to the list of processed sale orders.
                if send_picking or send_invoice:
                    if picking.sale_id.name not in sale_orders_to_include:
                        sale_order_name = picking.sale_id.name
                        sale_orders_to_include[sale_order_name] = {
                            'invoice_attachm_full_path_list': [invoice_attachment_full_path],
                            'picking_attachm_full_path_list': [delivery_order_attachment_full_path],
                            'barcode_attachm_full_path_list': [barcode_attachment_full_path],
                            'picking_id_list': [picking.id],
                        }
                        invoices_full_paths.add(invoice_attachment_full_path)
                    else:  # If the picking is a back-order then we'll have the sale order already there.
                        if invoice_attachment_full_path not in invoices_full_paths:
                            sale_orders_to_include[sale_order_name]['invoice_attachm_full_path_list'].append(invoice_attachment_full_path)
                            invoices_full_paths.add(invoice_attachment_full_path)
                        sale_orders_to_include[sale_order_name]['picking_attachm_full_path_list'].append(delivery_order_attachment_full_path)
                        sale_orders_to_include[sale_order_name]['barcode_attachm_full_path_list'].append(barcode_attachment_full_path)
                        sale_orders_to_include[sale_order_name]['picking_id_list'].append(picking.id)

                    ret.append(event.id)  # We processed this event.

                    sale_order = picking.sale_id
                    for invoice in sale_order.invoice_ids:
                        if invoice.check_send_invoice_to_docout():
                            invoice.mark_invoice_to_be_sent_to_docout()

            except Exception as e:
                error_message = _('Exception while processing event with ID={0}: {1}').format(event.id, format_exception(e))
                logger.error(error_message)
                project_issue_obj.create_issue(cr, uid, 'stock.event', event.id, error_message, tags=['warehouse'], context=context)

                stock_event_obj.write(new_cr, uid, event.id, {'error': True, 'info': error_message}, context=context)
                raise

            finally:
                new_cr.commit()
                new_cr.close()

        # If we have pickings to send...
        if sale_orders_to_include:
            fd_invoice_summary, tmp_path_invoice_summary = mkstemp(prefix='invoice_summary_{0}_'.format(ids[0]), dir="/tmp", text=False)
            fd_barcode_summary, tmp_path_barcode_summary = mkstemp(prefix='barcode_summary_{0}_'.format(ids[0]), dir="/tmp", text=False)
            fd_delivery_order_summary, tmp_path_delivery_order_summary = mkstemp(prefix='delivery_order_{0}_'.format(ids[0]), dir="/tmp", text=False)

            # The list of names for the sale.orders to send, sorted.
            sorted_sale_order_names = sorted(sale_orders_to_include.keys())

            # The list of IDs for the pickings, sorted according to its associated sale order.
            picking_list_ids = []
            for order in sorted_sale_order_names:
                picking_list_ids.extend(sale_orders_to_include[order]['picking_id_list'])

            try:
                new_cr = self.pool.db.cursor()

                now = fields.datetime.context_timestamp(cr, uid, datetime.now())
                date_format = datetime.strftime(now, '%Y%m%d')
                time_format = datetime.strftime(now, '%H%M%S')
                millisec_format = datetime.strftime(now, '%f')
                name = 'Email_event{event_id}_{date}_{time}_{milliseconds}'.format(event_id=first_event_id,
                                                                                   date=date_format,
                                                                                   time=time_format,
                                                                                   milliseconds=millisec_format)

                values = {'name': name,
                          'state': 'draft',
                          'content': '\n'.join(sorted_sale_order_names),
                          'picking_ids': [(6, 0, picking_list_ids)],
                          }

                new_stock_connect_file_instance = file_obj.create(cr, uid, values, context=context)

                # If we have any delivery orders to attach, we join them into a single PDF file and attach it.
                delivery_order_attachments_full_paths = []
                invoice_attachments_full_paths = []
                barcode_attachments_full_paths = []
                for order in sorted_sale_order_names:
                    delivery_order_attachments_full_paths.extend([attach for attach in sale_orders_to_include[order]['picking_attachm_full_path_list'] if attach is not False])
                    invoice_attachments_full_paths.extend([attach for attach in sale_orders_to_include[order]['invoice_attachm_full_path_list'] if attach is not False])
                    barcode_attachments_full_paths.extend([attach for attach in sale_orders_to_include[order]['barcode_attachm_full_path_list'] if attach is not False])

                if delivery_order_attachments_full_paths:
                    concatenate_pdfs(tmp_path_delivery_order_summary, delivery_order_attachments_full_paths)
                    self.attach_file(cr, uid, 'delivery_orders_summary_{date}_{time}_{milliseconds}.pdf'.format(date=date_format, time=time_format, milliseconds=millisec_format), tmp_path_delivery_order_summary, new_stock_connect_file_instance, context)

                # If we have any invoices to attach, we join them into a single PDF file and attach it.
                if invoice_attachments_full_paths:
                    concatenate_pdfs(tmp_path_invoice_summary, invoice_attachments_full_paths)
                    self.attach_file(cr, uid, 'invoices_summary_{date}_{time}_{milliseconds}.pdf'.format(date=date_format, time=time_format, milliseconds=millisec_format), tmp_path_invoice_summary, new_stock_connect_file_instance, context)

                # We join all the barcodes into a single PDF and attach it.
                concatenate_pdfs(tmp_path_barcode_summary, barcode_attachments_full_paths)
                self.attach_file(cr, uid, 'barcodes_summary_{date}_{time}_{milliseconds}.pdf'.format(date=date_format, time=time_format, milliseconds=millisec_format), tmp_path_barcode_summary, new_stock_connect_file_instance, context)

                # We generate and attach the picking list.
                pdf_data = get_pdf_from_report(cr, uid, 'report.picking_list_report', {'ids': picking_list_ids, 'model': 'ir.actions.report.xml'}, context=context)
                associate_ir_attachment_with_object(self, cr, uid, pdf_data, 'picking_list_{date}_{time}_{milliseconds}.pdf'.format(date=date_format, time=time_format, milliseconds=millisec_format), 'stock.connect.file', new_stock_connect_file_instance)
                pdf_data = None

            except Exception as e:
                error_message = _('Exception while processing event on stock.picking with IDs {0}: {1}').format(','.join(map(str, picking_list_ids)), format_exception(e))
                logger.error(error_message)
                project_issue_obj.create_issue(cr, uid, 'stock.event', first_event_id, error_message, tags=['warehouse'], context=context)

                stock_event_obj.write(new_cr, uid, first_event_id, {'error': True, 'info': error_message}, context=context)

                raise

            finally:
                new_cr.commit()
                new_cr.close()

                os.close(fd_invoice_summary)
                if os.path.exists(tmp_path_invoice_summary):
                    os.unlink(tmp_path_invoice_summary)

                os.close(fd_delivery_order_summary)
                if os.path.exists(tmp_path_delivery_order_summary):
                    os.unlink(tmp_path_delivery_order_summary)

                os.close(fd_barcode_summary)
                if os.path.exists(tmp_path_barcode_summary):
                    os.unlink(tmp_path_barcode_summary)

            # Sets as done all those events which were correctly processed.
            stock_event_obj.write(cr, uid, ret, {'state': EVENT_STATE_DONE}, context)

            # Sets to done the pickings processed.
            for picking_out in picking_obj.browse(cr, uid, picking_list_ids, context=context):
                partials = picking_out.get_partials()
                picking_out.do_partial(partials)
                picking_out.action_done()
                picking_out.set_stock_moves_done()

        logger.debug("Finished processing assigned stock pickings")

        del context['check_date_ready_for_export']

        return ret

    def attach_file(self, cr, uid, summary_file_name, summary_file_location, stock_connect_file_instance, context=None):
        if context is None:
            context = {}
        with open(summary_file_location, 'rb') as f:
            data = f.read()
            self.pool.get('ir.attachment').create(cr, uid, {'res_model': 'stock.connect.file',
                                                            'res_id': stock_connect_file_instance,
                                                            'name': summary_file_name,
                                                            'datas_fname': summary_file_name,
                                                            'datas': data.encode('base64'),
                                                            }, context)
        return True

    def _process_event(self, cr, uid, ids, func, event_code, warehouse_id, context):
        ''' It receives a function (func) to be executed over all the pending events
            associated to the warehouse. That function is the one which is going to do
            the work (in this case, create a stock.connect.file that will be used in a
            next step to generate the email)
                If something goes wrong, an issue will be logged associated to the
            current warehouse.
                It is the function passed as the argument 'func' which must log an
            issue per each event which yielded an error.
        '''
        if context is None:
            context = {}

        project_issue_obj = self.pool.get('project.issue')
        stock_event_obj = self.pool.get('stock.event')

        event_ids = stock_event_obj.search(cr, uid, [('warehouse_id', '=', warehouse_id),
                                                     ('event_code', '=', event_code),
                                                     ('state', '=', EVENT_STATE_DRAFT),
                                                     ('error', '=', False),
                                                     ], context=context)

        try:
            processed_event_ids = func(cr, uid, ids, event_ids, context=context)
        except Exception as e:
            error_message = "Warehouse with ID={0}: Error on event {1}, over events {2}: {3}".format(warehouse_id,
                                                                                                     event_code,
                                                                                                     event_ids,
                                                                                                     format_exception(e))
            logger.error(error_message)
            project_issue_obj.create_issue(cr, uid, 'stock.warehouse', warehouse_id, error_message, tags=['warehouse'], context=context)
            raise

        logger.debug("{0} Event {1}: processed {2} of {3} events".format(warehouse_id, event_code, len(processed_event_ids), len(event_ids)))
        logger.debug("{0} Event {1}: untouched events: {2}".format(warehouse_id, event_code, list(set(event_ids) - set(processed_event_ids))))

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
