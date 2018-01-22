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
import sys
from xsd.xml_tools import _XmlTools, xml_export_filename_translation
import shutil
import os
from openerp.addons.pc_log_data.log_data import write_log
from openerp.addons.pc_connect_master.utilities.others import format_exception
from openerp.tools.translate import _
import subprocess
from openerp import tools, SUPERUSER_ID
import codecs
import warnings
import functools
from lxml import etree

import logging
logger = logging.getLogger(__name__)
if '--test-enable' in sys.argv:
    logger.setLevel(logging.DEBUG)
else:
    logger.setLevel(logging.INFO)


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
        return _class
    return _xml_factory_decorator


def get_factory(env, name, *args, **kargs):
    factory = get_factory_class(name)
    return factory(env, *args, **kargs)


def get_factory_class(name):
    global __xml_factories
    if name in __xml_factories:
        factory = __xml_factories[name]
    else:
        raise Exception("Factory not defined")
    return factory


def get_customer_order_number(order_name):
    # Must have at least 10 chars (maximum of 25), so it fills with zeros if needed.
    MIN_LENGTH_ORDER_NUMBER = 10
    MAX_LENGTH_ORDER_NUMBER = 25
    order_number = order_name.zfill(MIN_LENGTH_ORDER_NUMBER)
    if len(order_number) > MAX_LENGTH_ORDER_NUMBER:
        raise Exception('Bad length for the object number/name (it was of lenght {0})'.format(len(order_number)))
    return order_number


class xml_abstract_factory(object):

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

        # Sets the default language, that will be overridden for certain
        # types of Yellowcube files (at least WAB and WAR).
        self.context['lang'] = self.pool['stock.connect'].browse(
            self.cr, self.uid, self.connection_id,
            self.context).yc_language_default

        self.main_file_id = None
        self.print_errors = self.context.get('yc_print_errors', True)
        self.cr.execute('select current_catalog')
        self.db_name = str(self.cr.fetchall()[0][0]).translate(xml_export_filename_translation)
        self.xml_tools = _XmlTools

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
        new_cr = self.pool.db.cursor()
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

    def import_file(self, file_text):
        raise Exception("Misdefined factory for {0} model".format(self._factory_name))

    def get_main_file_name(self, _object):
        return _object.name

    def generate_files(self, domain=None):
        logger.debug("Exporting {0} files".format(self._factory_name))
        self.main_file_id = None
        sender = self.get_param('sender', required=True)
        table_model = self.pool[self._table]
        # search_domain = []#[('xml_export_state', '=', 'draft')]
        # For each object that matches the domain, we create its xml file
        object_ids = table_model.search(
            self.cr, self.uid, domain, context=self.context)
        for object_id in object_ids:  # TODO: Check that self.context contains the yc_language_default set.
            try:
                _object = table_model.browse(self.cr, self.uid, object_id, context=self.context)

                # We generated the final filename, according to task with ID=2922
                main_file_name = self.get_main_file_name(_object)
                if not main_file_name:
                    raise Warning(_('Missing filename for main object {0} {1}#{2}').format(_object.name, self._table, _object.id))
                object_filename = "{sender}_{factory_name}_{name}.xml".format(sender=sender,
                                                                              factory_name=self._factory_name,
                                                                              name=self.xml_tools.export_filename(main_file_name, self.context))

                logger.debug("Exporting xml for {2} {0} into file {1}".format(object_id, object_filename, self._table))
                # The name of the main xml, is appened to each related file
                self.context['filename_prefix'] = "{0}_".format(object_filename[:-4])
                # The XML root is generated
                self.processed_items = []
                xml_node = self.generate_root_element(_object)
                if xml_node is not None:
                    xml_node.append(etree.Comment("Model: {0} ID: {1} Name: {2}".format(self._table, _object.id, _object.name)))
                    xml_output = self.xml_tools.xml_to_string(xml_node, remove_ns=True)
                    # The associated files are copied
                    self.save_file(xml_output, object_filename, main=True, binary=False, record_id=_object.id)
                    export_files = self.get_export_files(_object)
                    logger.debug("Exporting files {0}".format(export_files))
                    for name in export_files:
                        src = export_files[name]

                        data = None
                        with open(src, 'rb') as f:
                            data = f.read()
                        self.save_file(data, name)

                    self.mark_as_exported(_object.id)
                    # Finally, the XML file is copied. This ensures that XML files have its dependencies copied to the folder
                    write_log(self, self.cr, self.uid, self._table, _object.name, object_id, 'XML export successful', correct=True, extra_information=object_filename, context=self.context)
            except Exception as e:
                write_log(self, self.cr, self.uid, self._table, _object.name, object_id, 'XML export error', correct=False, extra_information=format_exception(e), context=self.context)
                logger.error("Exception exporting into xml {0}: {1}".format(object_id, format_exception(e)))
                raise
            finally:
                if 'filename_prefix' in self.context:
                    del self.context['filename_prefix']
        return len(object_ids) > 0

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
        logger.info("The factory {0} does not require to mark elements as exported".format(self._factory_name))

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
