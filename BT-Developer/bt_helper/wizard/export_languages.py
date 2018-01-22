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

import os
import cStringIO
import logging
import re
import subprocess
import shutil
from openerp import tools
from osv import osv, fields, orm
from openerp.tools.misc import get_iso_codes
from tools.translate import _
from openerp.addons.bt_helper.log_rotate import format_exception

logger = logging.getLogger(__name__)

SORT_PO_PATH_CONFIG_PARAM = 'bt_helper.sort_po_path'


class export_languages(osv.osv_memory):
    _name = "export.languages"
    _description = "Export all the language files to the indicated folder."

    _columns = {
        'format': fields.selection([('csv', 'CSV File'),
                                    ('po', 'PO File'),
                                    ('tgz', 'TGZ Archive'),
                                    ], string='File Format',
                                   required=True),
        'module_name_regexp': fields.char('Regular Expression for Module Names',
                                          help='If checked, only those modules with a name matching the '
                                               'regular expression are taken into account.'),
        'destination_folder': fields.char('Destination Folder', required=True,
                                          help='The folder that will store the generated language files.'),
        'sort_po_files': fields.boolean('Sort PO Files?',
                                        help='If checked, the content of the PO files will be sorted '
                                             'according to its key. System Parameter {0} is required'
                                             'to exist, and to point to the script sort-po.py'.format(SORT_PO_PATH_CONFIG_PARAM)),
        'state': fields.selection([('set_export_configuration', 'set_export_configuration'),
                                   ('export_finished', 'export_finished'),
                                   ]),
        'info': fields.text('Information',
                            help='Stores feedback to be provided to the user when the export finishes.'),
    }

    _defaults = {
        'format': 'po',
        'sort_po_files': True,
        'state': 'set_export_configuration',
    }

    def export_all_languages(self, cr, uid, ids, context=None):
        ''' Generates the language files (as 'po', 'csv' or 'tgz') for all the installed
            languages and for all the modules of the system the name of which
            (optionally) matches a regular expression. The files are stored as files in the
            folder indicated on the wizard.
        '''
        if context is None:
            context = {}

        ir_module_module_obj = self.pool.get('ir.module.module')
        res_lang_obj = self.pool.get('res.lang')

        wizard = self.browse(cr, uid, ids[0], context=context)

        # If it was checked to sort the PO file, then we search for the system's parameter
        # which includes it.
        sort_po_path = self.pool.get('ir.config_parameter').get_param(cr, uid, SORT_PO_PATH_CONFIG_PARAM, False)
        if wizard.sort_po_files:
            if not sort_po_path:
                raise orm.except_orm(_('System Parameter Not Found'),
                                     _('System Parameter {0} required to sort the PO files was not found.').format(SORT_PO_PATH_CONFIG_PARAM))
            elif not os.path.exists(sort_po_path):
                raise orm.except_orm(_('System Parameter Value Is Incorrect'),
                                     _('System Parameter {0} indicates a path for sort-po.py which does not exist.').format(SORT_PO_PATH_CONFIG_PARAM))

        # Checks that the destination folder doesn't exist, and that we can
        # create it.
        error_when_creating_destination_folder = False
        if os.path.exists(wizard.destination_folder):
            error_when_creating_destination_folder = _('The destination folder already exists.')
        else:
            try:
                os.makedirs(wizard.destination_folder)
            except Exception as e:
                error_when_creating_destination_folder = _('Could not create the destination folder: {0}').format(format_exception(e))
        if error_when_creating_destination_folder:
            raise orm.except_orm(_('Error when creating the folder.'), error_when_creating_destination_folder)

        # If a regular expression for the name of the modules has been indicated,
        # then we cache the machine used to do the matching of the expression.
        pattern_module_names = False
        if wizard.module_name_regexp:
            pattern_module_names = re.compile(wizard.module_name_regexp)

        # Finds the names of the modules to export, and store its name.
        module_names = []
        modules_ids = ir_module_module_obj.search(cr, uid, [('state', '=', 'installed')], context=context)
        for module in ir_module_module_obj.browse(cr, uid, modules_ids, context=context):
            if (not pattern_module_names) or pattern_module_names.match(module.name):
                module_names.append(module.name)

        # Finds all the languages installed.
        installed_langs = []
        installed_langs_ids = res_lang_obj.search(cr, uid, [], context=context)
        for installed_lang in res_lang_obj.browse(cr, uid, installed_langs_ids, context=context):
            installed_langs.append(installed_lang.code)

        # Now, starts the creation of the files. It creates one sub-folder per each module
        # considered, and inside stores as many language files per languages existing on
        # the system.
        for num_module in xrange(len(module_names)):
            module_name = module_names[num_module]

            logger.info('Exporting the languages of module {0} ({1} out of {2} modules)'.format(module_name,
                                                                                                num_module + 1,
                                                                                                len(module_names)))

            destination_folder = '{output_dir}/{module_name}/i18n'.format(output_dir=wizard.destination_folder.rstrip('/'),
                                                                          module_name=module_name)
            os.makedirs(destination_folder)

            for lang in installed_langs:
                buf = cStringIO.StringIO()
                tools.trans_export(lang, [module_name], buf, wizard.format, cr)

                lang_file_name = '{folder}/{lang_iso}.{ext}'.format(folder=destination_folder,
                                                                    lang_iso=get_iso_codes(lang),
                                                                    ext=wizard.format)

                f = open(lang_file_name, 'w')
                f.write(buf.getvalue())
                f.close()

                buf.close()

                # Optionally, we sort the PO files according to its content.
                if wizard.sort_po_files:
                    sorted_lang_file_name = lang_file_name + '.tmp'
                    execution_arguments = [sort_po_path, '-m', module_name, '-i1', lang_file_name, '-s', '-o', sorted_lang_file_name]
                    subprocess.call(execution_arguments, stdout=subprocess.PIPE)
                    shutil.move(sorted_lang_file_name, lang_file_name)

        info_message = _('The following modules were exported to folder {0}: {1}.').format(wizard.destination_folder, ', '.join(module_names))
        wizard.write({'state': 'export_finished', 'info': info_message})
        return {
            'type': 'ir.actions.act_window',
            'res_model': self._name, 'res_id': ids[0],
            'view_mode': 'form', 'target': 'new',
        }

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
