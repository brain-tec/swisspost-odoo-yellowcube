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
from openerp.addons.pc_connect_master.utilities.others import format_exception
import base64
import os
import shutil
from tempfile import mkstemp
from openerp.tools import DEFAULT_SERVER_DATETIME_FORMAT, \
    DEFAULT_SERVER_DATE_FORMAT
from datetime import datetime
from openerp.addons.pc_connect_master.utilities.pdf import \
    concatenate_pdfs, get_hash
from openerp.addons.pc_connect_master.utilities.files import FileManager
from openerp.addons.pc_connect_master.utilities.db import create_db_index
import logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)



_DOCOUT_STATES = [
    ('not_applicable', 'Not Applicable'),
    ('to_send', 'To Send'),
    ('skipped', 'Skipped'),
    ('sent', 'Sent'),
]


class ir_attachment_ext(osv.Model):
    _inherit = 'ir.attachment'

    def init(self, cr):
        create_db_index(cr, 'ir_attachment_name_docout_file_type_docout_state_email_index', 'ir_attachment', 'name, docout_file_type, docout_state_email')

    def default_get(self, cr, uid, fields_list, context=None):
        ret = super(ir_attachment_ext, self).default_get(cr, uid, fields_list, context=context)
        if 'docout_state_email' not in ret:
            ret['docout_state_email'] = 'not_applicable'
        if 'docout_state_remote_folder' not in ret:
            ret['docout_state_remote_folder'] = 'not_applicable'
        return ret

    def create_issue(self, cr, uid, ids, error_message, context=None):
        """ Adds an issue to the project with label 'doc-out',
            associated to the current attachment.
        """
        if context is None:
            context = {}
        if type(ids) is not list:
            ids = [ids]

        issue_obj = self.pool.get('project.issue')
        for res_id in ids:
            issue_obj.create_issue(
                cr, uid, 'ir.attachment', res_id, error_message,
                tags=['doc-out'], create=True, reopen=False, context=context)

        return True

    def __create_single_attachment_from_multiple_ones(self, cr, uid, ids, file_type, context=None):
        """ Given a list of several ir.attachments, returns a tuple of two elements:
            1. The ID of the new attachment created, having as content the concatenation of all the
               attachments received, or False if no attachment was created.
            2. The list of IDs of the attachments that were concatenated, to allow the caller to detect
               if some attachment could not be included in the final file.
        """
        if context is None:
            context = {}
        if type(ids) is not list:
            ids = [ids]

        new_attachment_id = False
        concatenated_attachment_ids = []

        # Gets the file path where we store the resulting file.
        file_manager = FileManager('/tmp')
        attachment_local_full_path = file_manager.create_new_file()

        # Gets the full paths of the files to be concatenated. They are stored into a dictionary
        # where the keys are the file paths and the values the ids of the attachments they come from.
        full_paths_to_concatenate = {}
        for attachment in self.browse(cr, uid, ids, context=context):
            attachment_path = attachment.get_attachment_local_full_path(file_manager)
            full_paths_to_concatenate[attachment_path] = attachment.id

        # Makes the concatenation of PDFs.
        full_paths_concatenated = concatenate_pdfs(attachment_local_full_path, full_paths_to_concatenate.keys())

        if full_paths_concatenated:
            for path in full_paths_concatenated:
                concatenated_attachment_ids.append(full_paths_to_concatenate[path])

            # Creates the attachment for the new file generated.
            with open(attachment_local_full_path, "rb") as f:
                attachment_content_base64 = base64.b64encode(f.read())
            attachment_name = '{0}_{1}.pdf'.format(file_type, get_hash(attachment_local_full_path))
            attachment_data = {
                'docout_exported_file_name': attachment_name,
                'name': attachment_name,
                'datas_fname': attachment_name,
                'datas': attachment_content_base64,
            }
            new_attachment_id = self.create(cr, uid, attachment_data, context=context)

        file_manager.clear()
        return new_attachment_id, concatenated_attachment_ids

    def send_pending_files_to_docout_email(self, cr, uid, ids, file_type, sending_option, email_template_id, email_address, context=None):
        ''' Sends the attachments to the doc-out email address.
        '''
        if context is None:
            context = {}

        # Performs error checking.
        error_messages = []
        mandatory_parameters = [file_type, sending_option, email_template_id, email_address]
        mandatory_parameters_str = ['file_type', 'sending_option', 'email_template_id', 'email_address']
        for param_it in xrange(len(mandatory_parameters)):
            if not mandatory_parameters[param_it]:
                error_messages.append(_('Missing parameter {0} on method send_pending_files_to_docout_email.').format(mandatory_parameters_str[param_it]))
        if error_messages:
            raise orm.except_orm(_('Error in Parameters'), '\n'.join(error_messages))

        # The ID's of the attachments that we could sent (a subset of parameter 'ids')
        attachment_sent_ids = []

        # Sends the files to the doc-out.
        if sending_option == 'multi_sending':
            attachment_sent_ids, errors = self.send_pending_files_to_docout_email_multi_files(cr, uid, ids, email_template_id, email_address, file_type, context=context)
        else:  # if sending_option == 'single_sending':
            attachment_sent_ids, errors = self.send_pending_files_to_docout_email_single_file(cr, uid, ids, email_template_id, email_address, file_type, context=context)

        # Sets as sent the the attachments that were sent.
        # If we sent the concatenation of several files, then all the files have the same name.
        if attachment_sent_ids:
            write_values = {
                'docout_state_email': 'sent',
                'docout_sending_date_email': datetime.now().strftime(DEFAULT_SERVER_DATETIME_FORMAT),
            }
            if sending_option == 'single_sending':
                concatenation_file_name = self.browse(cr, uid, attachment_sent_ids[0], context=context).name  # Concatenated attachment is first one.
                write_values.update({'docout_exported_file_name_email': concatenation_file_name})
            self.write(cr, uid, attachment_sent_ids, write_values, context=context)

        # Logs an issue over those attachments that were not sent because of any error.
        for attachment_id, error_message in errors:
            error_message = _('Error over attachment with ID={0}: {1}').format(attachment_id, error_message)
            logger.error(error_message)
            self.create_issue(cr, uid, attachment_id, error_message, context=None)

        return attachment_sent_ids, errors

    def send_pending_files_to_docout_email_single_file(self, cr, uid, ids, email_template_id, email_address, file_type, context=None):
        ''' Sends the attachments to the doc-out email address, joined into one (all the files are
            concatenated into a bigger one, which is the one which is sent).

            Returns a tuple of two elements:
            1. The list of attachment's IDs that could be sent to the doc-out, which in this case will have
               one more element, since we want to send one attachment which is the join of many others, but we mark
               the concatenated attachments to have been sent. In this case, the ID of the new attachment created is
               returned at the beginning of the list.
            2. The errors found, each one being a tuple of (attachment's id, error message), over any
               attachment's ID belonging to the initial list received (ids). Take into account that, even though
               we send only one attachment (because of the concatenation) it may be possible that we say that many
               attachments could not be found (because of errors when doing the concatenated files).
        '''
        if context is None:
            context = {}
        if type(ids) is not list:
            ids = [ids]

        errors = []  # Stores any error found.

        # Creates the attachment which is the concatenation of all the attachments that we want to send.
        new_attachment_id, concatenated_attachment_ids = self.__create_single_attachment_from_multiple_ones(cr, uid, ids, file_type, context=context)

        # Adds an error over those attachments that couldn't be concatenated.
        att_not_concatenated_ids = set(ids) - set(concatenated_attachment_ids)
        for att_not_concatenated_id in att_not_concatenated_ids:
            errors.append((att_not_concatenated_id, _('Attachment with ID={0} could not be concatenated.').format(att_not_concatenated_id)))

        # We re-use the case in which se send multi files, but with the difference that the list of files to send just contains one.
        summary_attachment_ids, errors_multi_files = self.send_pending_files_to_docout_email_multi_files(cr, uid, [new_attachment_id], email_template_id, email_address, file_type, context=context)
        errors.extend(errors_multi_files)

        # If we didn't manage to send the attachment which has the concatenation of all the others, then
        # is like if we had not sent any of the attachments.
        if not summary_attachment_ids:
            for att_concatenated_id in concatenated_attachment_ids:
                errors.append((att_concatenated_id, _('Attachment with ID={0} could not be sent because the attachment '
                                                      'that contained it could not be sent to the doc-out').format(att_concatenated_id)))
            attachments_sent_ids = []
            self.unlink(cr, uid, new_attachment_id, context=context)  # Removes the attachment created as the concatenation.
        else:
            attachments_sent_ids = summary_attachment_ids + concatenated_attachment_ids

        return attachments_sent_ids, errors

    def send_pending_files_to_docout_email_multi_files(self, cr, uid, ids, email_template_id, email_address, file_type, context=None):
        ''' Sends the attachments to the doc-out email address.

            Returns a tuple of two elements:
            1. The list of attachment's IDs that could be sent to the doc-out.
            2. The errors found, each one being a tuple of (attachment's id, error message), over any
               attachment's ID belonging to the initial list received (ids).
        '''
        if context is None:
            context = {}
        if type(ids) is not list:
            ids = [ids]

        errors = []  # Stores any error found.

        mail_template_obj = self.pool.get("email.template")
        mail_mail_obj = self.pool.get('mail.mail')

        error_when_creating_email = False

        try:
            values = mail_template_obj.generate_email(cr, uid, email_template_id, ids[0], context=context)
            msg_id = mail_mail_obj.create(cr, uid, values, context=context)
            mail_mail_obj.write(cr, uid, msg_id, {'attachment_ids': [(6, 0, ids)]}, context=context)

        except Exception as e:
            error_when_creating_email = True
            for attachment_id in ids:
                errors.append((attachment_id, _('Attachment with ID={0} could not be attached to the email '
                                                'to be sent to the doc-out  because some problem happened '
                                                'while creating the email which contained it: {1}').format(attachment_id, format_exception(e))))

        # Sending the email is a one-or-all process.
        if error_when_creating_email:
            attachment_sent_ids = []
        else:
            attachment_sent_ids = ids

        return attachment_sent_ids, errors

    def send_pending_files_to_docout_folder(self, cr, uid, ids, file_type, sending_option, connect_transport, remote_folder, context=None):
        ''' Sends the attachments to the doc-out remote folder.
        '''
        if context is None:
            context = {}

        # Performs error checking.
        error_messages = []
        mandatory_parameters = [file_type, sending_option, connect_transport, remote_folder]
        mandatory_parameters_str = ['file_type', 'sending_option', 'connect_transport', 'remote_folder']
        for param_it in xrange(len(mandatory_parameters)):
            if not mandatory_parameters[param_it]:
                error_messages.append(_('Missing parameter {0} on method send_pending_files_to_docout_folder.').format(mandatory_parameters_str[param_it]))
        if error_messages:
            raise orm.except_orm(_('Error in Parameters'), '\n'.join(error_messages))

        # Sends the files to the doc-out.
        if sending_option == 'multi_sending':
            attachment_sent_ids, errors = self.__send_to_docout_folder_multi_files(cr, uid, ids, connect_transport, remote_folder, file_type, context=context)
        else:  # if sending_option == 'single_sending':
            attachment_sent_ids, errors = self.__send_to_docout_folder_single_file(cr, uid, ids, connect_transport, remote_folder, file_type, context=context)

        # Sets as sent the the attachments that were sent.
        if attachment_sent_ids:
            write_values = {
                'docout_state_remote_folder': 'sent',
                'docout_sending_date_remote_folder': datetime.now().strftime(DEFAULT_SERVER_DATETIME_FORMAT),
            }
            if sending_option == 'single_sending':
                concatenation_file_name = self.browse(cr, uid, attachment_sent_ids[0], context=context).name  # Concatenated attachment is first one.
                write_values.update({'docout_exported_file_name_remote_folder': concatenation_file_name})
            self.write(cr, uid, attachment_sent_ids, write_values, context=context)

        # Logs an issue over those attachments that were not sent because of any error.
        for attachment_id, error_message in errors:
            error_message = _('Error over attachment with ID={0}: {1}').format(attachment_id, error_message)
            logger.error(error_message)
            self.create_issue(cr, uid, attachment_id, error_message, context=context)

        return attachment_sent_ids, errors

    def __send_to_docout_folder_single_file(self, cr, uid, ids, connect_transport, remote_folder, file_type, context=None):
        ''' Sends the attachments to the doc-out remote folder, joined into one (all the files are
            concatenated into a bigger one, which is the one which is sent).

            Returns a tuple of two elements:
            1. The list of attachment's IDs that could be sent to the doc-out, which in this case will have
               one more element, since we want to send one attachment which is the join of many others, but we mark
               the concatenated attachments to have been sent. The new attachment created (the one which is the
               concatenation) is placed at the beginning of the list.
            2. The errors found, each one being a tuple of (attachment's id, error message), over any
               attachment's ID belonging to the initial list received (ids). Take into account that, even though
               we send only one attachment (because of the concatenation) it may be possible that we say that many
               attachments could not be found (because of errors when doing the concatenated files).
        '''
        if context is None:
            context = {}
        if type(ids) is not list:
            ids = [ids]

        errors = []  # Stores any error found.

        # Creates the attachment which is the concatenation of all the attachments that we want to send.
        new_attachment_id, concatenated_attachment_ids = self.__create_single_attachment_from_multiple_ones(cr, uid, ids, file_type, context=context)

        # Adds an error over those attachments that couldn't be concatenated.
        att_not_concatenated_ids = set(ids) - set(concatenated_attachment_ids)
        for att_not_concatenated_id in att_not_concatenated_ids:
            errors.append((att_not_concatenated_id, _('Attachment with ID={0} could not be concatenated.').format(att_not_concatenated_id)))

        # We re-use the case in which we send multi files, but with the difference that the list of files to send just contains one.
        summary_attachment_ids, errors_multi_files = self.__send_to_docout_folder_multi_files(cr, uid, [new_attachment_id], connect_transport, remote_folder, file_type, context=context)
        errors.extend(errors_multi_files)

        # If we didn't manage to send the attachment which has the concatenation of all the others, then
        # is like if we had not sent any of the attachments.
        if not summary_attachment_ids:
            for att_concatenated_id in concatenated_attachment_ids:
                errors.append((att_concatenated_id, _('Attachment with ID={0} could not be sent because the attachment '
                                                      'that contained it could not be sent to the doc-out').format(att_concatenated_id)))
            attachments_sent_ids = []
            self.unlink(cr, uid, new_attachment_id, context=context)  # Removes the attachment created as the concatenation.
        else:
            attachments_sent_ids = summary_attachment_ids + concatenated_attachment_ids

        return attachments_sent_ids, errors

    def __send_to_docout_folder_multi_files(self, cr, uid, ids, connect_transport, remote_folder, file_type, context=None):
        ''' Sends the attachments to the doc-out remote folder.

            Returns a tuple of two elements:
            1. The list of attachment's IDs that could be sent to the doc-out.
            2. The errors found, each one being a tuple of (attachment's id, error message), over any
               attachment's ID belonging to the initial list received (ids).
        '''
        if context is None:
            context = {}
        if type(ids) is not list:
            ids = [ids]

        errors = []  # Stores any error found.

        file_manager = FileManager('tmp/')
        connection = False

        try:
            # Connects to the server.
            connection = connect_transport.create_connection()
            connection.open()

            # Lists the content of the remote folder used for the doc-out.
            files_in_remote_folder = connection.list(remote_folder)

            for attachment in self.browse(cr, uid, ids, context=context):
                attachment_local_full_path = attachment.get_attachment_local_full_path(file_manager)
                if attachment_local_full_path:

                    remote_file_path = '{0}'.format(attachment.docout_exported_file_name_remote_folder)

                    try:
                        # We do not send files which are already on the remote server.
                        if os.path.basename(remote_file_path) not in files_in_remote_folder:
                            connection.put(attachment_local_full_path, './{0}/{1}'.format(remote_folder.rstrip('/'), remote_file_path.strip('/')))

                    except Exception as e:
                        errors.append((attachment.id, _('Attachment with ID={0} could not be sent to the remote server.').format(attachment.id)))
                else:
                    errors.append((attachment.id, _('Attachment with ID={0} does not have a local full path, '
                                                    'and it needs one in order to be sent to the doc-out').format(attachment.id)))

        except Exception as e:
            for attachment_id in ids:
                errors.append((attachment_id, _('Attachment with ID={0} could not be sent to the remote server '
                                                'because of a problem while establishing the connection: {1}').format(attachment_id, format_exception(e))))

        finally:
            file_manager.clear()
            if connection:
                connection.close()

        # Determines which attachments could be found, which are those which didn't result in an error.
        attachment_not_sent_ids = [error[0] for error in errors]
        attachment_sent_ids = list(set(ids) - set(attachment_not_sent_ids))

        return attachment_sent_ids, errors

    def get_attachment_local_full_path(self, cr, uid, ids, file_manager, context=None):
        ''' Returns the local, full path to the file in which the attachment is stored.

            It can happen that the attachment is not stored on a file, but directly on
            the database as a base64-encoded string; in that case we return the full path
            of the temporal file created.
        '''
        if context is None:
            context = {}
        if type(ids) is not list:
            ids = [ids]

        attachment_local_full_path = False

        attachment = self.browse(cr, uid, ids[0], context=context)

        # Checks if we already have the file on disk, we just save the full path to it.
        if attachment.store_fname:
            location = self.pool.get('ir.config_parameter').get_param(cr, uid, 'ir_attachment.location')
            attachment_local_full_path = self.pool.get('ir.attachment')._full_path(cr, uid, location, attachment.store_fname)

        # If it's not on disk, we check if we have its base64 content stored in the database.
        elif attachment.db_datas:
            # In this case, we create a temporal file that we can copy.
            attachment_local_full_path = file_manager.create_new_file()

            data_decoded = base64.b64decode(attachment.db_datas)
            with open(attachment_local_full_path, "wb") as attachment_local_full_path_file:
                attachment_local_full_path_file.write(data_decoded)

        return attachment_local_full_path

    def _sel_get_docout_file_type(self, cr, uid, context=None):
        ''' - Returns the list of possible values for the selection field which indicates
              the type of field to export.
            - The idea is that this method is extended so that the list of types increases.
            - EVERY TIME this method is extended, the field 'docout_file_type' must be redefined to assure
              the recalculation of the list of options.
        '''
        ret = [('invoice', 'Invoice'),
               ]
        return ret

    def __sel_get_docout_file_type(self, cr, uid, context=None):
        return self._sel_get_docout_file_type(cr, uid, context)

    def get_docout_exported_file_name(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        if not isinstance(ids, list):
            ids = [ids]

        inv_obj = self.pool.get('account.invoice')

        attach = self.browse(cr, uid, ids[0], context=context)
        invoice = inv_obj.browse(cr, uid, attach.res_id, context=context)

        # We get the order from the invoice. There is just one order per
        # invoice in our case, so we take the first one.
        order = invoice.sale_ids[0]

        sale_order_yyyymmdd = datetime.strptime(
            order.date_order, DEFAULT_SERVER_DATE_FORMAT). \
            strftime('%Y%m%d')
        docout_exported_file_name = \
            '{db}_ZS_{order_num}_{invoice_num}_{date}.pdf'.format(
                db=cr.dbname,
                order_num=order.name,
                invoice_num=invoice.number.replace('/', ''),
                date=sale_order_yyyymmdd)

        return docout_exported_file_name

    _columns = {
        'docout_state_email': fields.selection(_DOCOUT_STATES, 'Doc-out Email Status', required=False,
                                               help='Indicates if the doc-out is applicable for this attachment, '
                                                    'and if so, in which state of the doc-out it is for the doc-out email.'),
        'docout_state_remote_folder': fields.selection(_DOCOUT_STATES, 'Doc-out Remote Folder Status', required=False,
                                                       help='Indicates if the doc-out is applicable for this attachment, '
                                                            'and if so, in which state of the doc-out it is for the doc-out email.'),
        'docout_file_type': fields.selection(__sel_get_docout_file_type, 'File Type', help='Indicates the type of the document to send.'),
        'docout_exported_file_name_email': fields.char('Exported File Name (Email)', help='The name it was given to the file when it was exported to the doc-out email address.'),
        'docout_exported_file_name_remote_folder': fields.char('Exported File Name (Remote Folder)', help='The name it was given to the file when it was exported to the doc-out remote folder.'),
        'docout_sending_date_email': fields.datetime('Date of Sending Doc-out Email', help='The date and time the file was sent to the doc-out email.'),
        'docout_sending_date_remote_folder': fields.datetime('Date of Sending Doc-out Remote Folder', help='The date and time the file was sent to the doc-out remote folder.'),
    }

    _defaults = {
        'docout_state_email': 'not_applicable',
        'docout_state_remote_folder': 'not_applicable'
    }

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
