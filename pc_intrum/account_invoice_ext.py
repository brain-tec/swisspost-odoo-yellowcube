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

import csv
from datetime import datetime
from openerp.osv import osv, fields
from openerp.addons.pc_connect_master.utilities.reports import \
    associate_ir_attachment_with_object
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT, DEFAULT_SERVER_DATETIME_FORMAT
from tempfile import mkstemp
import os
import re
import logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.WARNING)


class account_invoice_ext(osv.Model):
    _inherit = 'account.invoice'

    def _send_files_to_intrum_server(self, connect_transport_id, local_full_path, remote_file_path):
        ''' Sends the specified @local_full_path to the @remote_file_path in the server
            @param connect_transport_id: Is the connect_transport object associated
        '''
        # Connects to the server.
        connection = connect_transport_id.create_connection()
        try:
            connection.open()
            connection.put(local_full_path, remote_file_path)
        finally:
            connection.close()

        return True

    def _log_an_issue(self, cr, uid, issue_model, issue_model_id, issue_second_tag, issue_description_message, issue_error_message, issue_name, context=None):
        ''' Log an issue to the Intrum project.
            @param issue_model is the model associated to the issue
            @param issue_model_id is the id of the object that belongs to the model model
            @param issue_second_tag is the second tag of the issue
            @param issue_description_message is the description message of the issue
            @param issue_error_message is the message to post in the issue
            @param issue_name is the name of the issue

            @rtype Int. Id of the generated issue
        '''
        if context is None:
            context = {}

        project_issue_obj = self.pool.get('project.issue')
        issue_ids = project_issue_obj.find_resource_issues(cr, uid, issue_model,
                                                           issue_model_id,
                                                           tags=['intrum', issue_second_tag],
                                                           create=True, reopen=False,
                                                           context=context)
        context['mail_thread_no_duplicate'] = True
        for issue in project_issue_obj.browse(cr, uid, issue_ids, context=context):
            issue.message_post(issue_error_message)
        project_issue_obj.write(cr, uid, issue_ids,
                                {'description': issue_description_message,
                                 'name': issue_name},
                                context=context)
        del context['mail_thread_no_duplicate']

        if type(issue_ids) is list:
            issue_ids = issue_ids[0]

        return issue_ids

    def cron_send_invoices_to_intrum(self, cr, uid, context=None):
        ''' Sends the invoices to the Intrum.
        '''
        if context is None:
            context = {}

        payment_methods_to_check_ids = self.pool.get('payment.method').search(cr, uid, [('credit_check', '=', True)], context=context)
        sales_ids_with_payment_methods_to_check_ids = self.pool.get('sale.order').search(cr, uid,
                                                                                         [('payment_method_id', 'in', payment_methods_to_check_ids)],
                                                                                         context=context)
        out_invoices_paid = self.search(cr, uid,
                                        [('type', '=', 'out_invoice'),
                                         ('state', '=', 'paid'),
                                         ('reported_to_intrum', '=', False),
                                         ('sale_ids', 'in', sales_ids_with_payment_methods_to_check_ids)],
                                        context=context)

        if out_invoices_paid:
            self._send_invoices_to_intrum(cr, uid, out_invoices_paid, context=context)

        return True

    def _send_invoices_to_intrum(self, cr, uid, ids, context=None):
        ''' Send to Intrum those invoices whose payment method has been checked
             @ids: ids of the invoices to be sent
        '''
        if context is None:
            context = {}

        configuration_data = self.pool.get('configuration.data').get(cr, uid, None, context)
        now = datetime.now()
        remote_folder = configuration_data.intrum_remote_folder or './'
        if remote_folder[0] != '.':
            remote_folder = './{0}'.format(remote_folder)
        remote_file_name = re.sub(r"//*", "/", os.sep.join([remote_folder, 'Invoice_{0}.csv'.format(now.strftime('%Y%m%d_%H%M'))]))
        fd, file_name = mkstemp(suffix='_{0}.csv'.format(now.strftime('%Y%m%d_%H%M')), prefix='Invoice_')
        field_names = ['ClientID', 'OrderId', 'ResponseID', 'PaymentMethod',
                       'InvoiceReference', 'InvoiceDate', 'CustomerReference',
                       'InvoiceAmount', 'InvoiceCurrency', 'PartyType',
                       'Name1', 'Name2', 'Name3', 'Gender', 'FirstLine',
                       'SecondLine', 'PostCode', 'Town', 'CountryCode',
                       'Email', 'Telephone', 'DateOfBirth']

        with open(file_name, 'wb') as csvfile:
            writer = csv.DictWriter(csvfile, delimiter=';', fieldnames=field_names)
            writer.writerow(dict((fn, fn) for fn in field_names))
            for invoice in self.pool.get('account.invoice').browse(cr, uid, ids, context=context):
                if len(invoice.sale_ids) != 1:
                    logger.error("Invoice files could not be sent: {0}{1}".format("There are more than one sale in the invoice with ID ", invoice.id))
                    return False
                else:
                    sale_id = invoice.sale_ids[0]

                if invoice.partner_id.is_company:
                    is_company = '1'
                    date_of_birth = ""
                else:
                    is_company = '0'
                    date_of_birth = invoice.partner_id.birthdate or ''

                street_name = invoice.partner_id.street or ''
                house_number = invoice.partner_id.street_no or ''

                writer.writerow({'ClientID': configuration_data.intrum_client_id,
                                 'OrderId': invoice.id,
                                 'ResponseID': sale_id.last_intrum_check.response_id,
                                 'PaymentMethod': sale_id.last_intrum_check.payment_method,
                                 'InvoiceReference': invoice.reference,
                                 'InvoiceDate': invoice.date_invoice,
                                 'CustomerReference': invoice.partner_id.ref,
                                 'InvoiceAmount': str(invoice.amount_total).replace(".", ","),
                                 'InvoiceCurrency': invoice.currency_id.name,
                                 'PartyType': is_company,
                                 'Name1': invoice.partner_id.lastname,
                                 'Name2': invoice.partner_id.name,
                                 'Name3': invoice.partner_id.firstname,
                                 'Gender': "",  # gender is not sent
                                 'FirstLine': "{0} {1}".format(street_name, house_number).strip(),
                                 'SecondLine': "",  # SecondLine is not sent
                                 'PostCode': invoice.partner_id.zip,
                                 'Town': invoice.partner_id.city,
                                 'CountryCode': invoice.partner_id.country_id.code,
                                 'Email': invoice.partner_id.email,
                                 'Telephone': invoice.partner_id.phone,
                                 'DateOfBirth': date_of_birth,
                                 })
        # Encoding the file for attachments
        with open(file_name, "rb") as f:
            data = f.read()
            file_encoded_base_64 = data.encode("base64")
        intrum_project_model, intrum_project_id = self.pool.get('ir.model.data').get_object_reference(cr, uid,
                                                                                                      'pc_intrum',
                                                                                                      'intrum_project')
        issue_second_tag = ""
        issue_description_message = ""
        issue_error_message = ""
        # Sending the file to Intrum
        if configuration_data.intrum_connect_transport_id:
            try:
                self._send_files_to_intrum_server(configuration_data.intrum_connect_transport_id,
                                                  file_name, remote_file_name)

                # Registering changes in order to avoid sending these invoices again
                self.write(cr, uid, ids, {'reported_to_intrum': True}, context=context)

                # Attaching the file to the project Intrum
                attachment_id = associate_ir_attachment_with_object(
                    self, cr, uid, file_encoded_base_64, remote_file_name,
                    'project.project', intrum_project_id)
            except Exception as e:
                issue_second_tag = 'connection failure'
                issue_description_message = "Invoice files could not be sent to Intrum"
                issue_error_message = "{0}: {1}. The scheduler will try to send them again the next time.".format(issue_description_message, e)
        else:
            issue_second_tag = 'authentication failure'
            issue_description_message = "Invoice files could not be sent to Intrum because parameters are not set (see POST configuration tab in the Settings menu)"
            issue_error_message = "{0}. The scheduler will try to send them again the next time.".format(issue_description_message)

        if issue_second_tag or issue_description_message or issue_error_message:
            issue_id = self._log_an_issue(cr, uid, intrum_project_model, intrum_project_id, issue_second_tag,
                                          issue_description_message, issue_error_message,
                                          "Error sending invoice files to Intrum", context=None)
            # Attaching the file to the issue
            attachment_id = associate_ir_attachment_with_object(
                self, cr, uid, file_encoded_base_64, remote_file_name,
                'project.issue', issue_id)

        # Removing temporal file
        os.close(fd)
        if os.path.exists(file_name):
            os.remove(file_name)

        return True

    def get_account_voucher_line_ids(self, cr, uid, context=None):
        ''' Returns the list of IDS for those account.voucher.line belonging to a posted
            account.voucher which have not yet been sent to Intrum.
        '''
        if context is None:
            context = {}
        account_voucher_line_ids = []

        account_voucher_obj = self.pool.get('account.voucher')
        posted_account_voucher_ids = account_voucher_obj.search(cr, uid, [('state', '=', 'posted')], context=context)
        for posted_account_voucher in account_voucher_obj.browse(cr, uid, posted_account_voucher_ids, context=context):
            for credit_line in posted_account_voucher.line_cr_ids:
                if not credit_line.sent_to_intrum:
                    account_voucher_line_ids.append(credit_line.id)

        return account_voucher_line_ids

    def cron_send_payment_transactions_to_intrum(self, cr, uid, context=None):
        ''' Sends the invoices to the Intrum.
        '''
        if context is None:
            context = {}

        return self._send_payment_transactions_to_intrum(cr, uid, context=context)

    def _send_payment_transactions_to_intrum(self, cr, uid, context=None):
        ''' Send to Intrum the transaction data for managing limits:
            Three types of transaction messages are supported:
            - RECEIPT of payments from your customers
            - REFUNDs if a customer cancels the order after the invoice has been paid
            - CANCELlations and partial cancellations
             @ids: ids of the invoices to be sent
        '''
        if context is None:
            context = {}

        account_voucher_line_obj = self.pool.get('account.voucher.line')

        def get_date_intrum_format(cr, uid, date_str, date_format, context=None):
            ''' Gets a date in the format of Odoo and returns it in the format expected by Intrum
            '''
            if context is None:
                context = {}

            date_intrum_format = datetime.strftime(fields.datetime.context_timestamp(cr, uid, datetime.strptime(date_str, date_format), context), '%d.%m.%Y')
            return date_intrum_format

        configuration_data = self.pool.get('configuration.data').get(cr, uid, None, context)
        refunded_or_cancelled_invoices_ids = self.search(cr, uid,
                                                         ['|',
                                                          ('type', '=', 'out_refund'),
                                                          ('state', '=', 'cancel')],
                                                         context=context)
        now = datetime.now()
        remote_folder = configuration_data.intrum_remote_folder or './'
        if remote_folder[0] != '.':
            remote_folder = './{0}'.format(remote_folder)
        remote_file_name = re.sub(r"//*", "/", os.sep.join([remote_folder, 'Transactionfile_{0}.csv'.format(now.strftime('%Y%m%d_%H%M'))]))
        fd, file_name = mkstemp(suffix='_{0}.csv'.format(now.strftime('%Y%m%d_%H%M')), prefix='Transactionfile_')
        field_names = ['ClientID', 'CustomerReference', 'OrderId', 'TransactionType',
                       'TransactionDate', 'TransactionAmount', 'TransactionCurrency',
                       'Additional1', 'OpenBalance', 'Additional2']
        account_invoice_objs = self.pool.get('account.invoice').browse(cr, uid,
                                                                       refunded_or_cancelled_invoices_ids,
                                                                       context=context)

        # Gets the payment lines which has not yet been sent to Intrum.
        account_voucher_line_ids = self.get_account_voucher_line_ids(cr, uid, context=None)
        account_voucher_lines = account_voucher_line_obj.browse(cr, uid, account_voucher_line_ids, context=context)

        if account_invoice_objs or account_voucher_lines:
            with open(file_name, 'wb') as csvfile:
                writer = csv.DictWriter(csvfile, delimiter=';', fieldnames=field_names)
                writer.writerow(dict((fn, fn) for fn in field_names))
                for invoice in self.pool.get('account.invoice').browse(cr, uid,
                                                                       refunded_or_cancelled_invoices_ids,
                                                                       context=context):

                    # Set the transaction type (all of them can be found in the intrum_request.py):
                    # account.invoice can access to REFUND invoices, and CANCEL invoices,
                    # RECEIPT invoices are registered in account.voucher.line (that is the reason of the second loop).
                    # The rest of the transaction types are not implemented in this project
                    if invoice.state == "cancel":
                        transaction_type = "CANCEL"
                        transaction_date = get_date_intrum_format(cr, uid, invoice.date_cancel, DEFAULT_SERVER_DATETIME_FORMAT, context) if invoice.date_cancel else ""
                    elif invoice.type == "out_refund":
                        transaction_type = "REFUND"
                        transaction_date = get_date_intrum_format(cr, uid, invoice.date_invoice, DEFAULT_SERVER_DATE_FORMAT, context)
                    else:
                        transaction_type = ""
                        transaction_date = ""

                    writer.writerow({'ClientID': configuration_data.intrum_client_id,
                                     'CustomerReference': invoice.partner_id.ref,
                                     'OrderId': invoice.id,
                                     'TransactionType': transaction_type,
                                     'TransactionDate': transaction_date,
                                     'TransactionAmount': str(invoice.amount_total).replace(".", ","),
                                     'TransactionCurrency': invoice.currency_id.name,
                                     'Additional1': "",  # Nothing for refunds or cancellations
                                     'OpenBalance': invoice.residual,
                                     'Additional2': invoice.reference,
                                     })

                for account_voucher_line in account_voucher_lines:

                    writer.writerow({'ClientID': configuration_data.intrum_client_id,
                                     'CustomerReference': account_voucher_line.partner_id.ref,
                                     'OrderId': account_voucher_line.id,
                                     'TransactionType': "RECEIPT",
                                     'TransactionDate': get_date_intrum_format(cr, uid, account_voucher_line.voucher_id.date, DEFAULT_SERVER_DATE_FORMAT, context),
                                     'TransactionAmount': str(account_voucher_line.amount).replace(".", ","),
                                     'TransactionCurrency': account_voucher_line.currency_id.name,
                                     'Additional1': "",  # Different payment types implemented
                                     'OpenBalance': account_voucher_line.amount_unreconciled,
                                     'Additional2': "",
                                     })

            # Encoding the file for attachments
            with open(file_name, "rb") as f:
                data = f.read()
                file_encoded_base_64 = data.encode("base64")
            intrum_project_model, intrum_project_id = self.pool.get('ir.model.data').get_object_reference(cr, uid,
                                                                                                          'pc_intrum',
                                                                                                          'intrum_project')
            issue_second_tag = ""
            issue_description_message = ""
            issue_error_message = ""

            # Sending the file to Intrum
            if configuration_data.intrum_connect_transport_id:
                try:
                    self._send_files_to_intrum_server(configuration_data.intrum_connect_transport_id,
                                                      file_name, remote_file_name)
                    # Registering changes in order to avoid sending these invoices again
                    self.write(cr, uid, refunded_or_cancelled_invoices_ids,
                               {'reported_to_intrum': True}, context=context)
                    account_voucher_line_obj.write(cr, uid, account_voucher_line_ids,
                                                   {'sent_to_intrum': True}, context=context)
                    attachment_id = associate_ir_attachment_with_object(
                        self, cr, uid, file_encoded_base_64, remote_file_name,
                        'project.project', intrum_project_id)
                except Exception as e:
                    issue_second_tag = 'connection failure'
                    issue_description_message = "Payment transaction files could not be sent to Intrum"
                    issue_error_message = "{0}: {1}. The scheduler will try to send them again the next time.".format(issue_description_message, e)
            else:
                issue_second_tag = 'authentication failure'
                issue_description_message = "Payment transactions could not be sent to Intrum because parameters are not set (see POST configuration tab in the Settings menu)"
                issue_error_message = ". The scheduler will try to send them again the next time.".format(issue_description_message)

            if issue_second_tag or issue_description_message or issue_error_message:
                issue_id = self._log_an_issue(cr, uid, intrum_project_model, intrum_project_id,
                                              issue_second_tag, issue_description_message,
                                              issue_error_message,
                                              "Error sending payment transactions to Intrum",
                                              context=None)
                # Attaching the file to the issue
                attachment_id = associate_ir_attachment_with_object(
                    self, cr, uid, file_encoded_base_64, remote_file_name,
                    'project.issue', issue_id)
        # Removing temporal file
        os.close(fd)
        if os.path.exists(file_name):
            os.remove(file_name)

        return True

    _columns = {
        'reported_to_intrum': fields.boolean('Is the invoice reported to Intrum?', readonly=True),
    }

    _defaults = {
        'reported_to_intrum': False,
    }
