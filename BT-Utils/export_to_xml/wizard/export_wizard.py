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
import logging
import random
from openerp import SUPERUSER_ID
from openerp import tools
from openerp.osv import fields, osv
from openerp.osv import expression
from openerp.tools.translate import _
from openerp.tools.safe_eval import safe_eval
from openerp.tools.convert import convert_xml_import
import openerp
import base64
import tempfile
import openerp.tools as tools
_logger = logging.getLogger(__name__)

def get_xml_id_from_ir_model_data(delegator, model, cr, uid, ids, context=None):
    if not isinstance(ids, list):
        ids = [ids]
    if context is None:
        context = {}
    ir_model_data_obj = delegator.pool.get('ir.model.data')
    result = {}
    for id in ids:
        if isinstance(id, tuple):
            id = id[0]
        delegator_model = delegator.pool.get(model)
        for row in delegator_model.browse(cr, uid, ids, context):
            delegator_model.export_data(cr, uid, ids, ['id'], context)
        to_search = [('model', '=', model),
                                               ('res_id', '=', id)]
        ir_model_data_ids = ir_model_data_obj.search(cr,
                                              uid,
                                              to_search,
                                              context=context)
        xml_id = '__export__.{0}_{1}'.format(model.replace('.', '_'), id)
        if ir_model_data_ids:
            ir_model_data = ir_model_data_obj.browse(cr, uid, ir_model_data_ids[0], context)
            xml_id = "{module}.{name}".format(module=ir_model_data.module,
                                              name=ir_model_data.name,)
        else:
            raise Exception("Not data found")
        result[id] = xml_id
    return result

def to_print(delegator, model, cr, uid, ids, already_exported, level, context=None):
    if not isinstance(ids, list):
        ids = [ids]
    if context is None:
        context = {}
    xml_ids = get_xml_id_from_ir_model_data(delegator, model, cr, uid, ids, context)
    R = ""
    for elem in delegator.pool.get(model).browse(cr, uid, ids, context=context):
        if xml_ids[elem.id] in already_exported:
            return ""
        else:
            already_exported[xml_ids[elem.id]] = True
        try:
            elems = elem.read()[0]
        except:
            continue

        result = """<record id='{xml_id}' model="{inherit}">""".format(xml_id=xml_ids[elem.id],
                                                                       inherit=model)

        result += '\n'
        pre = ""
        post = ""
        var_model_ids = delegator.pool.get('ir.model').search(cr, uid, [('model', '=', model)], context=context)
        FIELDS = {}
        FIELDS_M2M = {}
        FIELDS_O = {}
        for var_model in delegator.pool.get('ir.model').browse(cr, uid, var_model_ids, context=context):
            for field in var_model.field_id:
                if 'one2many' in field.ttype or 'many2many' in field.ttype:
                    FIELDS_M2M[field.name] = field.relation
                elif 'many2one' in field.ttype:
                    FIELDS_O[field.name] = field.relation
                else:
                    if field.ttype == 'binary' and context.get('remove_binary', False):
                        pass
                    else:
                        FIELDS[field.name] = field.ttype
        for key in elems: 
            if key in FIELDS:
                value = "{0}".format(elems[key])
                if FIELDS[key] == 'boolean':
                    result += """<field name="{key}" eval="{value}" />""".format(key=key,
                                                                                 value=elems[key])
                elif FIELDS[key] in ['html', 'text', 'char', 'selection']:
                    if elems[key]:
                        result += """<field name="{key}"><![CDATA[{value}]]></field>""".format(key=key,
                                                                       value=elems[key])
                elif elems[key]:
                    result += """<field name="{key}">{value}</field>""".format(key=key,
                                                                       value=elems[key])
            elif key in FIELDS_M2M:
                if level > 0:
                    if isinstance(elems[key], tuple):
                        if elems[key][0]:
                            post += to_print(delegator, FIELDS_M2M[key], cr, uid, elems[key][0], already_exported, level - 1, context=context)
                    else:
                        if elems[key]:
                            post += to_print(delegator, FIELDS_M2M[key], cr, uid, elems[key], already_exported, level - 1, context=context)

            elif key in FIELDS_O:
                '''
                Get the XML ID
                '''
                id_to_search = elems[key]
                if isinstance(elems[key], tuple):
                    id_to_search = elems[key][0]
                if id_to_search:
                    xml_idsa = get_xml_id_from_ir_model_data(delegator,
                                                            FIELDS_O[key],
                                                            cr,
                                                            uid,
                                                            [id_to_search],
                                                            context)
                    if xml_idsa[id_to_search] != "not_known":
                        result += """<field name="{key}" ref="{value}" />""".format(key=key,
                                                                                value=xml_idsa[id_to_search])
                    if level > 0:
                        if isinstance(elems[key], tuple):
                            if elems[key][0]:
                                pre += to_print(delegator,
                                                FIELDS_O[key],
                                                cr,
                                                uid,
                                                elems[key][0],
                                                already_exported,
                                                level - 1,
                                                context=context)
                        else:
                            if elems[key]:
                                pre += to_print(delegator, FIELDS_O[key], cr, uid, elems[key], already_exported, level - 1, context=context)
            result += '\n'
        result += """</record>"""
        result += '\n'
        R += pre
        R += result
        R += post
    return R

class export_wizard(osv.TransientModel):
    _name = 'export.wizard'
    _description = 'Export Wizard'

    """Override of create() to auto-compute the action name"""

    def create(self, cr, uid, values, context=None):
        print "VALUES", values
        if 'action_id' in values and not 'name' in values:
            action = self.pool.get('ir.actions.actions').browse(cr, uid, values['action_id'], context=context)
            values['name'] = action.name
        return super(export_wizard, self).create(cr, uid, values, context=context)

    _columns = {
        'action_id': fields.many2one('ir.actions.act_window', 'Action to share', 
                help="The action that opens the screen containing the data you wish to share."),
        'name': fields.char('Share Title', size=64, required=True, help="Title for the share (displayed to users as menu and shortcut name)"),
        'get_selected_ids': fields.char('Ids to export'),
        'export_xml': fields.text('Export XML'),
        'level': fields.integer('Levels', default=1),
        'remove_binary': fields.boolean('Remove Binary Fields'),
        'data': fields.binary('View.xml'),
        'data_import': fields.binary('XML To Import'),
        'data_name': fields.char('export.xml', required=True),
        'state': fields.selection([('draft', 'Draft'), ('done', 'Done')], string="State", required=True),
        'import': fields.boolean('Import XML'),
        'module_id': fields.many2one('ir.module.module', string="Módulo", domain="[('state', '=', 'installed')]")
    }
    _defaults = {
                'action_id': lambda self, cr, uid, context, *a: context.get('action_id'),
                'export_xml': '',
                'state': 'draft',
                'data_name': 'export.xml'
    }

    def go_step_1(self, cr, uid, ids, context=None):
        wizard_data = self.browse(cr, uid, ids, context)[0]
        model, res_id = self.pool.get('ir.model.data').get_object_reference(cr, uid, 'export_to_xml', 'action_share_wizard_step1')
        action = self.pool.get(model).read(cr, uid, res_id, context=context)
        action['res_id'] = ids[0]
        action.pop('context', '')
        return action

    def go_step_2(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        wizard_data = self.browse(cr, uid, ids, context)[0]
        already_exported = {}
        context['remove_binary'] = wizard_data.remove_binary
        result = """<?xml version="1.0" encoding="utf-8"?>
                        <openerp>
                                <data>"""
        ids_to_export = eval(wizard_data.get_selected_ids)
        for id_to_export in ids_to_export: 
            result += to_print(self, wizard_data.action_id.res_model, cr, uid, id_to_export, already_exported, wizard_data.level, context)
        result += """    </data>
                    </openerp>"""

        wizard_data.write({'export_xml': result,
                           'data': base64.b64encode(result),
                           'state': 'done'
                           })
        model, res_id = self.pool.get('ir.model.data').get_object_reference(cr, uid, 'export_to_xml', 'action_share_wizard_step1')
        action = self.pool.get(model).read(cr, uid, res_id, context=context)
        action['res_id'] = ids[0]
        action.pop('context', '')
        return action

    def go_step_3(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        wizard_data = self.browse(cr, uid, ids, context)[0]
        fp = tempfile.NamedTemporaryFile()
        xml_to_import_data = wizard_data.data_import.decode('base64')
        for line in xml_to_import_data:
            fp.write(line)
            fp.flush()
        convert_xml_import(cr,
                           wizard_data.module_id.name,
                           fp.name)
        fp.close()
        return {}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
