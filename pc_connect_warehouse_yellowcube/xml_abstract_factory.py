# b-*- encoding: utf-8 -*-
##############################################################################
#
#    Copyright (c) 2014 brain-tec AG (http://www.brain-tec.ch)
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
import logging
import sys
logger = logging.getLogger(__name__)
from xsd.xml_tools import create_element, xml_to_string, validate_xml, export_filename, xml_export_filename_translation
import shutil
import os
from openerp.addons.pc_connect_master.utilities.misc import format_exception


def new_cursor(self):
    if hasattr(self.pool, 'db'):
        return self.pool.db.cursor()
    else:
        return self.pool.cursor()
from openerp.tools.translate import _
import subprocess
from openerp import tools, SUPERUSER_ID
import codecs
import warnings
import functools
from lxml import etree


def deprecated(func):
    '''This is a decorator which can be used to mark functions
    as deprecated. It will result in a warning being emitted
    when the function is used.'''

    @functools.wraps(func)
    def new_func(*args, **kwargs):
        warnings.warn_explicit(
            "Call to deprecated function {}.".format(func.__name__),
            category=DeprecationWarning,
            filename=func.func_code.co_filename,
            lineno=func.func_code.co_firstlineno + 1
        )
        return func(*args, **kwargs)
    return new_func


__xml_factories = {}


def xml_factory_decorator(name):
    def _xml_factory_decorator(_class):
        global __xml_factories
        __xml_factories[name] = _class
        _old_init = _class.__init__

        def _new_init(self, *args, **kargs):
            self._factory_name = name
            xml_abstract_factory.__init__(self, *args, **kargs)
            _old_init(self, *args, **kargs)
            # Variables are not checked, as they may be needed on export but not on import
            # if self._table is None:
            #    raise Exception("Missing table name")
        _class.__init__ = _new_init
    return _xml_factory_decorator


def get_factory(env, name, *args, **kargs):
    global __xml_factories
    if name in __xml_factories:
        return __xml_factories[name](env, *args, **kargs)
    else:
        raise Exception("Factory not defined")


def get_customer_order_number(order_name):
    # Must have at least 10 chars (maximum of 25), so it fills with zeros if needed.
    MIN_LENGTH_ORDER_NUMBER = 10
    MAX_LENGTH_ORDER_NUMBER = 25
    order_number = order_name.zfill(MIN_LENGTH_ORDER_NUMBER)
    if len(order_number) > MAX_LENGTH_ORDER_NUMBER:
        raise Exception('Bad length for the object number/name (it was of lenght {0})'.format(len(order_number)))
    return order_number


class xml_abstract_factory():

    ignore_import_errors = False

    post_issue_tags = ['error']
    post_issue_thread = True

    processed_items = []

    def __init__(self, env, context=None, *args, **kargs):
        if context is None:
            self.context = {}
        else:
            self.context = context.copy()
        if isinstance(env, list):
            self.env = None
            self.pool = env[0]
            self.cr = env[1]
            self.uid = SUPERUSER_ID
        else:
            self.env = env
            self.pool = env['stock.warehouse'].pool
            self.cr = env.cr
            self.uid = env.uid
        self.connection_id = context['stock_connect_id']
        self.context['lang'] = self.pool['stock.connect'].browse(self.cr, self.uid, self.connection_id, self.context).yc_language
        for p in ['attachments_from_invoice', 'attachments_from_picking']:
            self.context['yc_%s' % p] = self.get_param(p) or 0
        self.main_file_id = None
        self.print_errors = self.context.get('yc_print_errors', True)
        self.cr.execute('select current_catalog')
        global xml_export_filename_translation
        self.db_name = str(self.cr.fetchall()[0][0]).translate(xml_export_filename_translation)

    def str_date_to_postgres(self, date_str):
        ''' Converts a date of type YYYYMMDD to YYYY-MM-DD, or YYYYMMDDHHMMSS to YYYY-MM-DD HH:MM:SS
        '''
        postgres_date = False
        if date_str:
            if len(date_str) == len('YYYYMMDD'):
                postgres_date = '{year}-{month}-{day}'.format(year=date_str[0:4], month=date_str[4:6], day=date_str[6:8])
            elif len(date_str) == len('YYYYMMDDHHMMSS'):
                postgres_date = '{year}-{month}-{day} {hours}:{minutes}:{seconds}'.format(year=date_str[0:4],
                                                                                          month=date_str[4:6],
                                                                                          day=date_str[6:8],
                                                                                          hours=date_str[8:10],
                                                                                          minutes=date_str[10:12],
                                                                                          seconds=date_str[12:14])
        return postgres_date

    def keep_only_date(self, date_str):
        ''' Given a date with the format YYYY-MM-DD HH:MM:SS, returns YYYY-MM-DD.
            It relies on the assumption that the first row of non-blank spaces contain the date.
        '''
        only_date = False
        if date_str:
            only_date = date_str.split(' ')[0]
        return only_date

    def post_issue(self, obj, error_message, create=True, reopen=True):
        issue_obj = obj.pool.get('project.issue')
        new_cr = new_cursor(self)
        issue_ids = issue_obj.find_resource_issues(new_cr,
                                                   self.uid,
                                                   obj._name,
                                                   obj.id,
                                                   tags=self.post_issue_tags,
                                                   create=create,
                                                   reopen=reopen,
                                                   context=self.context)
        for issue in issue_obj.browse(new_cr, self.uid, issue_ids, context=self.context):
            body_message = '{0}: {1}<br/>{2}'.format('XML factory', self.__class__.__name__, error_message)
            issue.message_post(body_message, type='comment', subtype="mail.mt_comment", context=self.context)
        body_message = '{0}#{1}: {2}<br/>{3}'.format(obj._name, obj.id, obj.name, error_message)
        logger.debug("Posting Issue: {0}".format(body_message))
        if self.post_issue_thread and ('import_log' in self.context):
            self.pool.get('yellowcube.import.log').message_post(new_cr, self.uid, self.context['import_log'], body_message, type='comment', subtype="mail.mt_comment", context=self.context)
        new_cr.commit()
        new_cr.close()

    def set_param(self, param, value):
        param_key = 'yc_{0}'.format(param)
        self.pool.get('stock.connect').write(self.cr, self.uid, self.connection_id, {param_key: value}, self.context)

    def get_param(self, param, required=False):
        param_key = 'yc_{0}'.format(param)
        value = self.pool.get('stock.connect').read(self.cr, self.uid, self.connection_id, [param_key], self.context)[param_key]
        if not value:
            if required:
                error_msg = _('Required variable yc_{0} is not defined in the configuration data.').format(param)
                raise Warning(error_msg)
        return value

    def mark_record(self, res_id, model_name=None):
        # TODO !!!
        if model_name is None:
            model_name = self._table

        model_id = self.pool.get('ir.model').search(self.cr,
                                                    self.uid,
                                                    [('model', '=', model_name)],
                                                    context=self.context)[0]

        if 'import_log' in self.context:
            self.pool.get('yellowcube.import.log.line').create(self.cr,
                                                               self.uid,
                                                               {'model_id': model_id,
                                                                'ref_id': res_id,
                                                                'import_id': self.context['import_log']},
                                                               context=self.context)

    def import_file(self, file_text):
        raise Exception("Misdefined factory for {0} model".format(self._factory_name))

    def get_main_file_name(self, _object):
        return _object.name

    def _print_pdf_to_pcl(self, cr, uid, internal_path, context=None):
        ''' Gets a PDF and converts it to a PCL. Everything is done using system calls.
            It is highly heuristic and is intended to be used as a _temporary_ solution (ok?)
        '''
        if context is None:
            context = {}

        # Gets the parameters that we need to do the conversion.
        printer_name = self.get_param('invoice_pcl_printer_name', required=True)
        printer_output_file = self.get_param('invoice_pcl_printer_destination', required=True)
        silent_mode = self.get_param('invoice_pcl_printer_silent_printing', required=False)

        try:
            # Launches the command to print the file.
            # This prints to the file indicated by variable 'printer_output_file'.
            if silent_mode:
                commands = ['lp', '-s', '-d', printer_name, internal_path]
            else:
                commands = ['lp', '-d', printer_name, internal_path]
            output = subprocess.check_output(commands)

            # Gets the name of the job sent.
            # It parses a string of the form: xxx xxx JOB_NAME   (xx xxxx)
            job_name = output.split('(')[0].strip().split(' ')[-1]

            # Keeps waiting for the job to complete.
            job_is_completed = False
            while not job_is_completed:
                output = subprocess.check_output(['lpstat', '-W', 'not-completed'])
                if len(output) == 0:
                    job_is_completed = True
                else:
                    job_lines = output.split('\n')
                    job_was_found = False
                    for job_line in job_lines:
                        if (job_line.strip() != '') and (job_line.split(' ')[0] == job_name):
                            job_was_found = True
                    if not job_was_found:
                        job_is_completed = True

        except Exception as e:
            raise Exception('There was a problem while converting the PDF to a PCL: {0}'.format(format_exception(e)))

        return printer_output_file

    def _file_is_pcl(self, internal_file_path):
        ''' Returns whether an internal file path (field store_fname in table ir_attachment) is a pcl.
        '''
        is_pcl = False

        # 'internal_file_path' contains the full systems' path. So we need to remove the preffix in order to get the 'store_fname' field.
        ir_attachment_location = self.pool.get('ir.config_parameter').get_param(self.cr, self.uid, 'ir_attachment.location')
        internal_file_path_preffix = os.path.join(tools.config['root_path'], ir_attachment_location.replace('file:///', ''), self.cr.dbname)
        store_fname = internal_file_path[len(internal_file_path_preffix) + 1:]

        # Searches for the ir.attachment with that store_fname and checks if it's an invoice.
        ids = self.pool.get('ir.attachment').search(self.cr, self.uid, [('store_fname', '=', store_fname)], context=self.context)
        if len(ids) > 0:
            ir_attachment_obj = self.pool.get('ir.attachment').browse(self.cr, self.uid, ids[0], self.context)
            is_pcl = (ir_attachment_obj.name[-3:] == 'pcl')

        return is_pcl

    def generate_files(self, domain=None):
        logger.debug("Exporting {0} files".format(self._factory_name))
        self.main_file_id = None
        sender = self.get_param('sender', required=True)
        table_model = self.pool[self._table]
        # search_domain = []#[('xml_export_state', '=', 'draft')]
        # For each object that matches the domain, we create its xml file
        for object_id in table_model.search(self.cr, self.uid, domain, context=self.context):  # TODO: Check that self.context contains the yc_language set.
            try:
                _object = table_model.browse(self.cr, self.uid, object_id, context=self.context)

                # We generated the final filename, according to task with ID=2922
                main_file_name = self.get_main_file_name(_object)
                if not main_file_name:
                    raise Warning(_('Missing filename for main object {0} {1}#{2}').format(_object.name, self._table, _object.id))
                object_filename = "{sender}_{factory_name}_{name}.xml".format(sender=sender,
                                                                              factory_name=self._factory_name,
                                                                              name=export_filename(main_file_name, self.context))

                logger.debug("Exporting xml for {2} {0} into file {1}".format(object_id, object_filename, self._table))
                # The name of the main xml, is appened to each related file
                self.context['filename_prefix'] = "{0}_".format(object_filename[:-4])
                # The XML root is generated
                self.processed_items = []
                xml_node = self.generate_root_element(_object)
                if xml_node is not None:
                    xml_node.append(etree.Comment("Model: {0} ID: {1} Name: {2}".format(self._table, _object.id, _object.name)))
                    xml_output = xml_to_string(xml_node, remove_ns=True)
                    # The associated files are copied
                    self.save_file(xml_output, object_filename, main=True, binary=False, record_id=_object.id)
                    export_files = self.get_export_files(_object)
                    logger.debug("Exporting files {0}".format(export_files))
                    for name in export_files:
                        src = export_files[name]

                        if self._file_is_pcl(src):
                            # If the file must be submitted as PCL, then it generates the PCL
                            logger.debug("PCL conversion: PCL creation for {0} STARTED.".format(src))
                            pcl_output_path = self._print_pdf_to_pcl(self.cr, self.uid, src, self.context)
                            logger.debug("PCL conversion: PCL creation for {0} FINISHED".format(src))
                            data = None
                            with open(pcl_output_path, 'rb') as f:
                                data = f.read()
                            self.save_file(data, name)
                        else:
                            data = None
                            with open(src, 'rb') as f:
                                data = f.read()
                            self.save_file(data, name)

                    self.mark_as_exported(_object.id)
            except Exception as e:
                logger.error("Exception exporting into xml {0}: {1}".format(object_id, format_exception(e)))
                raise
            finally:
                if 'filename_prefix' in self.context:
                    del self.context['filename_prefix']
        return True

    def save_file(self, data, filename, main=False, binary=True, record_id=None, model=None):
        logger.debug("Saving {0}{1}file {2}".format('main ' if main else '', 'binary ' if binary else '', filename))
        stock_file_obj = self.pool.get("stock.connect.file")
        cr, uid, ctx = self.cr, self.uid, self.context

        if model is None:
            model = self._table

        if not self.main_file_id:
            priority = self.get_base_priority()
            vals = {'name': '', 'type': self._factory_name, 'state': 'ready', 'priority': priority}
            self.main_file_id = stock_file_obj.create(cr, uid, vals, context=ctx)
            stock_file_obj.update_priorities(cr, uid, self.get_related_items(record_id), priority + 1, context=ctx)

        if main:
            relate_ids = ','
            for m, r in self.processed_items:
                relate_ids += '{0}:{1},'.format(m, r or '')
            vals = {
                'model': model,
                'res_id': record_id,
                'name': filename,
                'related_ids': relate_ids,
            }
            stock_file_obj.write(cr, uid, self.main_file_id, vals, ctx)

        if main and not binary:
            stock_file_obj.write(cr, uid, self.main_file_id, {'binary_content': False, 'content': data}, ctx)
        elif main and binary:
            stock_file_obj.write(cr, uid, self.main_file_id, {'binary_content': True}, ctx)
            stock_file_obj.add_attachment(cr, uid, self.main_file_id, data, filename, ctx)
        else:
            stock_file_obj.add_attachment(cr, uid, self.main_file_id, data, filename, ctx)

    def mark_as_exported(self, _id):
        logger.debug("The factory {0} does not require to mark elements as exported".format(self._factory_name))

    def get_export_files(self, _object):
        """
        This method returns a dictionary of {name: src_path} of files to be copied
        """
        raise Exception("Misdefined factory for {0} model".format(self._factory_name))

    def generate_root_element(self, _object):
        """
        This method returns the root element of the file
        """
        raise Exception("Misdefined factory for {0} model".format(self._factory_name))

    def get_related_items(self, object_id):
        """
        This function returns a dictionary of models and IDs of related items
         so related items can be submitted beforehand
         E.g. {'product.product': [1, 3, 5]}
        """
        return {}

    def get_base_priority(self):
        """
        Returns the priority (higher better) of this type of file.
         Also, related items MUST have a priority higher than this
        """
        return 0

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
