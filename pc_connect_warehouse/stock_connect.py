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
from openerp.osv import orm, osv, fields
from openerp.tools.translate import _
from openerp.addons.pc_connect_master.utilities.others import format_exception
from openerp import SUPERUSER_ID
from stock_connect_file import FILE_STATE_READY, FILE_STATE_DRAFT, FILE_STATE_DONE, FILE_STATE_CANCEL
import os
from tempfile import mkstemp
import re
from threading import Lock
import shutil
from sys import argv
import logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


mutex = Lock()

_STOCK_CONNECT_TYPE = [
    ('yellowcube', 'YellowCube'),
    ('yellowcubesoap', 'YellowCube over SOAP'),
    ('external_email', 'External Email'),
]

_NAME_PREFIX = 'PCAP - WAREHOUSE - {0}'

_ISSUE_NO_CONNECTION = _('There was a problem with the connection')


class stock_connect(osv.Model):
    _name = 'stock.connect'
    _inherit = 'mail.thread'

    def files_needing_ack(self, cr, uid, ids, context=None):
        """ Returns a set of file-types needing an acknowledgement (i.e. ACK)
            from the server. All the models inheriting from stock.connect
            must check and call super if they extend this method.
        """
        # No files need an ACK in the default stock.connect.
        return set([])

    def copy(self, cr, uid, id_, default=None, context=None):
        if default is None:
            default = {}
        original = self.browse(cr, uid, id_, context=context)
        default['name'] = '{0} (copy)'.format(original.name)
        default['warehouse_ids'] = []
        return super(stock_connect, self).copy(cr, uid, id_, default=default, context=context)

    def open_action(self, cr, uid, ids, context):
        # We really need the context, so if missing, it must fail
        # The action will be a copy of the context
        ret = context.copy()
        if 'type' not in ret:
            ret['type'] = 'ir.actions.act_window'
        if 'domain' not in ret:
            if ret['res_model'] == 'stock.connect.file':
                ret['domain'] = [['stock_connect_id', 'in', ids]]
            elif ret['res_model'] == 'stock.event':
                warehouse_ids = self.pool.get('stock.warehouse').search(cr, uid, [('stock_connect_id', 'in', ids)], context=context)
                ret['domain'] = [['warehouse_id', 'in', warehouse_ids]]
        if 'view_mode' not in ret:
            ret['view_mode'] = 'tree,form'
        return ret

    def log_issue(self, cr, uid, ids, issue_text, context=None, vals=None, **args):
        """
        This method register a log both by log file, and as an issue.

        The issue_text is formated used (in order of preference): additional arguments, the values passed in vals, and the context.

        This is made this way, so:
        1) Data in the context is default available always.
        2) vals can be used as standard data we want to pass (e.g. in a loop for similar messages).
        3) Additional arguments are special, so the will have preferencce (e.g. in a loop where sharing vals)
        """
        if isinstance(ids, list):
            ids = ids[0]
        if context is None:
            context = {}
        else:
            context = context.copy()
        context['mail_thread_no_duplicate'] = True
        if vals is None:
            vals = {}
        issue_obj = self.pool.get('project.issue')
        formatss = {'ids': ids}
        formatss.update(context)
        formatss.update(vals)
        formatss.update(args)
        if formatss.get('log_issue_no_format', False):
            text = issue_text
        else:
            try:
                text = issue_text.format(**formatss)
            except:
                logger.error("Error on format. Args={0}, text='{1}'".format(formatss, issue_text))
                raise
        if context.get('log_errors', True):
            logger.error(text)
        ret = {
            'text': text,
            'issue_ids': []
        }
        for issue_id in issue_obj.find_resource_issues(cr, uid, 'stock.connect', ids, tags=['warehouse'], create=True, reopen=False, context=context):
            issue_obj.message_post(cr, uid, issue_id, text, context=context)
            ret['issue_ids'].append(issue_id)
        if 'active_model' in context and ('active_id' in context or 'active_ids' in context):
            _ids = [context.get('active_id', False)] or context['active_ids']
            for issue_id in issue_obj.find_resource_issues(cr, uid, context['active_model'], _ids, tags=['warehouse'], create=True, reopen=False, context=context):
                issue_obj.message_post(cr, uid, issue_id, text, context=context)
                ret['issue_ids'].append(issue_id)
        self.message_post(cr, uid, ids, text, context=context)
        return ret

    def write(self, cr, uid, ids, vals, context=None):
        ret = super(stock_connect, self).write(cr, uid, ids, vals, context=context)
        cron_obj = self.pool.get('ir.cron')
        if 'name' in vals:
            name = vals['name']
            for _id in ids:
                crons = self.find_schedulers(cr, uid, _id, context)
                if not crons:
                    cron_obj.create(cr, uid, {'name': _NAME_PREFIX.format(name),
                                              'model': 'stock.connect',
                                              'function': 'connection_do_all',
                                              'args': str((_id,)),
                                              'user_id': SUPERUSER_ID,
                                              'active': False,
                                              }, context)
                for cid in crons:
                    if name not in crons[cid]:
                        cron_obj.write(cr, uid, [cid], {'name': _NAME_PREFIX.format(name)}, context)
        return ret

    def unlink(self, cr, uid, ids, context=None):
        for _id in ids:
            self.pool.get('ir.cron').unlink(cr, uid, [x for x in self.find_schedulers(cr, uid, _id, context)], context)
        return super(stock_connect, self).unlink(cr, uid, ids, context=context)

    def create(self, cr, uid, vals, context=None):
        ret = super(stock_connect, self).create(cr, uid, vals, context=context)
        cron_obj = self.pool.get('ir.cron')
        cron_obj.create(cr, uid, {'name': _NAME_PREFIX.format(vals['name']),
                                  'model': 'stock.connect',
                                  'function': 'connection_do_all',
                                  'args': str((ret,)),
                                  'user_id': SUPERUSER_ID,
                                  'active': False,
                                  }, context)
        return ret

    def find_schedulers(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        if type(ids) is list:
            ids = ids[0]
        cron_obj = self.pool.get('ir.cron')
        ret = {}
        cr.execute("""
        SELECT id
        FROM ir_cron
        WHERE model = 'stock.connect' AND function = 'connection_do_all'
        """)
        for cron in cron_obj.browse(cr, uid, [x[0] for x in cr.fetchall()], context):
            if ids == eval(cron.args)[0]:
                ret[cron.id] = cron.name
        return ret

    def process_file_tree(self, cr, uid, ids, context=None, file_id=None, function=None):
        if context is None:
            context = {}
        if type(ids) is not list:
            ids = [ids]

        file_obj = self.pool.get('stock.connect.file')
        project_issue_obj = self.pool.get('project.issue')

        if file_id is None:
            r = True
            for _id in ids:
                file_ids = file_obj.search(cr, uid, [('stock_connect_id', '=', _id),
                                                     ('parent_file_id', '=', False),
                                                     ('state', 'not in', (FILE_STATE_DONE, FILE_STATE_CANCEL)),
                                                     ], context=context)
                for file_id in file_ids:
                    try:
                        r = self.process_file_tree(cr, uid, ids, context, file_id=file_id, function=function) and r
                    except Exception as e:
                        raise
            # We return a boolean indicating if there was any error
            # Upper code may do a rollback, process all errors, re-try, etc.
            return r

        else:
            new_cr = self.pool.db.cursor()
            try:
                file_record = file_obj.browse(cr, uid, file_id, context)
                if file_record.error or file_record.state == FILE_STATE_DRAFT:
                    # errors are returned, and draft files stop the process
                    return False
                elif file_record.state == FILE_STATE_READY:
                    # If there is no error, and the file is ready, we process if
                    for subfile in file_record.child_file_ids:
                        if not self.process_file_tree(cr, uid, ids, context=context, file_id=subfile.id, function=function):
                            # Errors are sent back
                            return False
                    for subatt in file_record.attachments:
                        if not self.process_file(cr, uid, ids, context=context, file_id=file_id, att_id=subatt.id, function=function):
                            return False
                    if not self.process_file(cr, uid, ids, context=context, file_id=file_id, function=function):
                        return False
                else:
                    return True
                # Now, we set the file as processed
                file_record.write({'state': FILE_STATE_DONE, 'error': False})

            except Exception as e:
                # Logs a software issue and stores the cause of the error.
                error_message = _('An exception ocurred with stock.connect.file with ID={0}: {1}').format(file_record.id, format_exception(e))
                project_issue_obj.create_issue(cr, uid, 'stock.connect.file', file_record.id, error_message, context=context)
                file_obj.write(new_cr, uid, file_record.id, {'error': True, 'info': error_message}, context=context)
                raise

            finally:
                new_cr.commit()
                new_cr.close()

        # When we get here, everything is fine
        return True

    def process_file(self, cr, uid, ids, context=None, file_id=None, att_id=None, function=None):
        if function is None:
            logger.debug("This stock.connect has not defined a specific process_file !!!")
            raise NotImplementedError()

        return function(cr, uid, ids, context=context, file_id=file_id, att_id=att_id)

    def connection_do_all(self, cr, uid, ids, context=None):
        ''' Each part of the process is executed in its own cursor, in order
            to isolate its errors from the errors of the other parts.
        '''
        if context is None:
            context = {}
        else:
            context = context.copy()
        if 'show_errors' not in context:
            context['show_errors'] = True

        # 1) Get new input files
        new_cr = self.pool.db.cursor()
        try:
            self.connection_get_files(new_cr, uid, ids, context)
        finally:
            new_cr.commit()
            new_cr.close()

        # 2) Process the input files
        new_cr = self.pool.db.cursor()
        try:
            self.connection_process_files(new_cr, uid, ids, context)
        finally:
            new_cr.commit()
            new_cr.close()

        # 3) Process changes in warehouses
        new_cr = self.pool.db.cursor()
        try:
            self.connection_process_events(new_cr, uid, ids, context)
        finally:
            new_cr.commit()
            new_cr.close()

        # 3) Send the changes
        new_cr = self.pool.db.cursor()
        try:
            self.connection_send_files(new_cr, uid, ids, context)
        finally:
            new_cr.commit()
            new_cr.close()

        return True

    def connection_get_files(self, cr, uid, ids, context=None):
        ''' We GET the files from the server. However, since the server may have a counter set on
            each file to limit the number of times it can be downloaded, and some versions of
            paramiko somehow open a file to check its size when a listing of the file is done,
            we download the files just once, and  put it on a temporal folder.
                We download *all* the files from the output folder, from *all* the clients, into
            the temporal folder. Then the files are moved into the archiving folder taking into
            account the filename-template set for each client.
        '''
        if type(ids) is not list:
            ids = [ids]
        if context is None:
            context = {}

        connect_obj = self.pool.get('stock.connect')
        file_obj = self.pool.get('stock.connect.file')
        project_issue_obj = self.pool.get('project.issue')

        for connection in connect_obj.browse(cr, uid, ids, context):

            # We check that the folder we are going to store the files for archive is created,
            # otherwise we raise an exception.
            if not os.path.exists(connection.local_archive_input_dir):
                error_message = _('Folder {0} does not exist on the local machine, and it is needed to archive the downloaded files.').format(connection.local_archive_input_dir)
                project_issue_obj.create_issue(cr, uid, 'stock.connect', connection.id, error_message, context=context)
                raise orm.except_orm(_('Error'), error_message)

            if not os.path.exists(connection.local_archive_input_dir_temporal):
                error_message = _('Folder {0} does not exist on the local machine, and it is needed to archive the downloaded files.').format(connection.local_archive_input_dir_temporal)
                project_issue_obj.create_issue(cr, uid, 'stock.connect', connection.id, error_message, context=context)
                raise orm.except_orm(_('Error'), error_message)

            if self._name == 'stock.connect' and connection.type:
                pool = self.pool['stock.connect.{0}'.format(connection.type)]
                pool.connection_get_files(cr, uid, connection.id, context)
            else:
                logger.debug("Standard get files behaviour")

                # Tests the connection. If the testing fails, then it logs and issue.
                # If the the 'show errors' is set in the context, then no exception is
                # raised (this is intended to be used when the downloading of the files
                # is the first step of the processing of files, events, and submitting new files).
                try:
                    connection.connect_transport_id.test_connection()
                except Exception as e:
                    connection.log_issue(_ISSUE_NO_CONNECTION, exception=e)
                    project_issue_obj.create_issue(cr, uid, 'stock.connect', connection.id, format_exception(e), context=context)
                    if context.get('show_errors', False):
                        logger.error(format_exception(e))
                        break
                    else:
                        raise

                # Connects to the server and downloads all the files which are there.
                try:
                    pattern = re.compile(connection.remote_file_template)

                    mutex.acquire()
                    con = connection.connect_transport_id.create_connection()
                    con.open()

                    # Lists all the files in the remote INcoming folder.
                    list_result = con.list(connection.remote_input_dir)
                    for path in list_result:
                        _name = path.split('/')[-1]
                        if _name and (pattern.match(_name) or connection.promiscuous_file_import):
                            # It downloads all the files it to a local temporal-folder which is used
                            # We do this so that we can empty the remote folder in a safe way,
                            # by keeping a copy of the processed files.
                            remote_file_path = os.path.join(connection.remote_input_dir, _name).replace('//', '/')
                            temporal_local_file_path = os.path.join(connection.local_archive_input_dir_temporal, _name).replace('//', '/')
                            con.get(remote_file_path, temporal_local_file_path)

                            # Once we have copied it to the local folder used to archive the files, we
                            # delete it from the server, but only if it was actually copied in local.
                            if os.path.exists(temporal_local_file_path):
                                con.remove(remote_file_path)

                    # Moves to the archiving folder all the files of the temporary folder
                    # which are already in the database and which matches with the pattern.
                    #     We do not create the file into the database first because in that
                    # case we risk that a roll-back makes some files which were already archived
                    # not to be in the database.
                    for file_name in os.listdir(connection.local_archive_input_dir_temporal):
                        if pattern.match(file_name) and \
                           file_obj.search(cr, uid, [('name', '=', file_name),
                                                     ('stock_connect_id', '=', connection.id),
                                                     ('input', '=', True),
                                                     ], count=True, context=context):
                            temporal_local_file_path = os.path.join(connection.local_archive_input_dir_temporal, file_name).replace('//', '/')
                            destination_file_path = os.path.join(connection.local_archive_input_dir, file_name).replace('//', '/')
                            shutil.copy2(temporal_local_file_path, destination_file_path)
                            if os.path.exists(destination_file_path):
                                os.remove(temporal_local_file_path)

                    # Stores the files in the temporal folder into the database,
                    # but only if they are not there already and they matches with the name pattern.
                    for file_name in os.listdir(connection.local_archive_input_dir_temporal):
                        if pattern.match(file_name) and \
                           not file_obj.search(cr, uid, [('name', '=', file_name),
                                                         ('stock_connect_id', '=', connection.id),
                                                         ('input', '=', True),
                                                         ], count=True, context=context):
                            temporal_local_file_path = os.path.join(connection.local_archive_input_dir_temporal, file_name).replace('//', '/')
                            with open(temporal_local_file_path, 'r') as f:
                                file_obj.create(cr, uid, {'name': file_name,
                                                          'content': f.read(),
                                                          'input': True,
                                                          'stock_connect_id': connection.id,
                                                          }, context)

                except Exception as e:
                    # If there is an exception in this case, we do raise because maybe we got
                    # an error which otherwise would result in our database being corrupted.
                    project_issue_obj.create_issue(cr, uid, 'stock.connect', connection.id, format_exception(e), context=context)
                    raise

                finally:
                    con.close()
                    mutex.release()

        return True

    def connection_process_files(self, cr, uid, ids, context=None):
        if type(ids) is not list:
            ids = [ids]
        if context is None:
            context = {}
        else:
            context = context.copy()

        connect_obj = self.pool.get('stock.connect')
        project_issue_obj = self.pool.get('project.issue')

        for obj in connect_obj.browse(cr, uid, ids, context):
            if not obj.type:
                error_message = _('No connection type was indicated, and one is required in order to process the files.')
                project_issue_obj.create_issue(cr, uid, 'stock.connect', obj.id, error_message, context=context)
                raise orm.except_orm(_('Error'), error_message)

            if self._name == 'stock.connect':
                ctx = context.copy()
                ctx['stock_connect_id'] = obj.id
                self.pool['stock.connect.{0}'.format(obj.type)].connection_process_files(cr, uid, obj.id, context=ctx)
            else:
                raise NotImplementedError()
        return True

    def connection_process_events(self, cr, uid, ids, context=None):
        if type(ids) is not list:
            ids = [ids]
        if context is None:
            context = {}

        connect_obj = self.pool.get('stock.connect')
        project_issue_obj = self.pool.get('project.issue')

        for obj in connect_obj.browse(cr, uid, ids, context):
            if not obj.type:
                error_message = _('No connection type was indicated, and one is required in order to process the events.')
                project_issue_obj.create_issue(cr, uid, 'stock.connect', obj.id, error_message, context=context)
                raise orm.except_orm(_('Error'), error_message)

            if self._name == 'stock.connect':
                ctx = context.copy()
                ctx['stock_connect_id'] = obj.id
                self.pool['stock.connect.{0}'.format(obj.type)].connection_process_events(cr, uid, obj.id, context=ctx)
            else:
                raise NotImplementedError()
        return True

    def connection_send_files(self, cr, uid, ids, context=None):
        if type(ids) is not list:
            ids = [ids]
        if context is None:
            context = {}

        connect_obj = self.pool.get('stock.connect')
        for obj in connect_obj.browse(cr, uid, ids, context):
            ctx = context.copy()
            ctx['stock_connect_id'] = obj.id
            if self._name == 'stock.connect' and obj.type:
                self.pool['stock.connect.{0}'.format(obj.type)].connection_send_files(cr, uid, obj.id, context=ctx)
            else:
                logger.debug("Standard send files behaviour")
                fd, tmp_path = mkstemp(prefix='connection_{0}_output_file'.format(obj.id), dir="/tmp", text=False)
                con = obj.connect_transport_id.create_connection()
                try:
                    con.open()
                    paths = con.list(obj.remote_output_dir)

                    def _send_file(cr, uid, ids, context, file_id, att_id):
                        file_obj = self.pool.get('stock.connect.file')
                        att_obj = self.pool.get('ir.attachment')

                        _name = None
                        _data = None
                        _binary = None
                        _file = file_obj.browse(cr, uid, file_id, context)
                        if att_id:
                            att = att_obj.browse(cr, uid, att_id, context)
                            _name = att.name
                            _binary = True
                            _data = att.datas.decode('base64')
                        elif file_id:
                            _name = _file.name
                            _data = _file.content
                            _binary = _file.binary_content
                        else:
                            raise Exception('This code must never be achieved')
                        if _name in paths:
                            _file.write({'state': 'cancel', 'info': 'File already on remote.<br/>{0}'.format(_file.info)})
                        else:
                            mode = 'w'
                            if _binary:
                                mode = 'wb'
                            with open(tmp_path, mode) as f:
                                f.write(_data)
                            con.put(tmp_path, '{0}/{1}'.format(obj.remote_output_dir, _name))
                        return True

                    self.process_file_tree(cr, uid, ids, context=ctx, function=_send_file)

                except Exception as e:
                    # process_file_tree() must raise, but just in case...
                    raise

                finally:
                    os.close(fd)
                    if os.path.exists(tmp_path):
                        os.unlink(tmp_path)
                    con.close()

        return True

    def _type_installed(self, cr, uid, ids):
        """
        This constraint checks that the type is supported by some model
        """
        for con in self.browse(cr, uid, ids):
            if con.type:
                if not self.pool.get('stock.connect.{0}'.format(con.type)):
                    if '--test-enable' in argv:
                        logger.error('This check cannot be done on test,'
                                     ' because of how modules are loaded')
                        return True
                    else:
                        return False
        return True

    def get_event_codes_to_ignore(self, cr, uid, ids, context=None):
        """ Returns the list of event_code to ignore AND mark as ignored.
        """
        return []

    _columns = {
        'name': fields.char("Name", length="32", required=True),
        'type': fields.selection(_STOCK_CONNECT_TYPE, 'Connection type', required=False),
        'warehouse_ids': fields.one2many('stock.warehouse', 'stock_connect_id', 'Configured Warehouses'),
        'stock_connect_file_ids': fields.one2many('stock.connect.file', 'stock_connect_id', 'Files'),
        'stock_event_ids': fields.related('warehouse_ids', 'stock_event_ids', relation="stock.event", type="one2many", string='Events'),
        'connect_transport_id': fields.many2one('connect.transport', 'Connection', required=False),
        'remote_input_dir': fields.char('Remote directory where to GET files', required=True),
        'local_archive_input_dir_temporal': fields.char('Temporal local directory where to place the input files to archive', required=True),
        'local_archive_input_dir': fields.char('Local directory where to archive the input files', required=True),
        'remote_output_dir': fields.char('Remote directory where to PUT files', required=True),
        'remote_file_template': fields.char('Filename template for files to import', required=True),
        'limit_of_connections': fields.integer('Number of connections made on sync', required=False),
        'log_about_already_existing_files': fields.boolean('Log about already existing files?',
                                                           help='If activated, a line in the log will appear every time it sees a file that it already has.'),
        'promiscuous_file_import': fields.boolean('Promiscuous File Import (read and remove ALL from remote)'),
    }

    _defaults = {
        'remote_input_dir': './',
        'local_archive_input_dir': './archive_input_dir',
        'local_archive_input_dir_temporal': './archive_input_dir_temporal',
        'remote_output_dir': './',
        'remote_file_template': '[a-zA-Z0-9].*',
        'limit_of_connections': 0,
        'log_about_already_existing_files': False,
        'promiscuous_file_import': True,
    }

    _sql_constraints = [
        ('archive_folders_must_be_different',
         'CHECK (local_archive_input_dir <> local_archive_input_dir_temporal)',
         'The two folders used to download the files must be different.'),
    ]

    _constraints = [
        (_type_installed, 'Selected type is not present on the server. Install related module', ['type']),
    ]

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
