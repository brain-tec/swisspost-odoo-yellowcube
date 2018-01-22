# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>).
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

import tools
from osv import osv, fields
from tools.translate import _

class module_updater(osv.osv_memory):
    _name = "module.updater"
    _description = "Update Modules and Languages"

    _columns = {
        'update_module_ids': fields.many2many('ir.module.module','update_module_module_updater','update_module_id','updater_id','Modules to update', required=False, domain="[('state','=','installed')]"),
        'lang_ids': fields.many2many('res.lang','res_lang_module_updater','lang_id','updater_id','Languages', required=False),
        'lang_module_ids': fields.many2many('ir.module.module','lang_module_module_updater','lang_module_id','updater_id','Modules', required=False, domain="[('state','=','installed')]"),
        'lang_overwrite': fields.boolean('Overwrite Existing Terms', help="If you check this box, your customized translations will be overwritten and replaced by the official ones."),
        'state':fields.selection([('init','init'),('done','done')], 'state', readonly=True),
    }
    _defaults = {
        'state': 'init',
        'lang_overwrite': True,
        'lang_ids': lambda self, cr, uid, context = None: self.pool.get('res.lang').search(cr, uid, [], context=context),
    }
    def update_modules(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        
        updater_obj = self.browse(cr, uid, ids)[0]
        modobj = self.pool.get('ir.module.module')
        modupobj = self.pool.get('base.module.upgrade')

        # Update modules
        if updater_obj.update_module_ids:
            module_ids = [x.id for x in updater_obj.update_module_ids]
            modobj.button_upgrade(cr, uid, module_ids, context=context)
            modupobj.upgrade_module(cr, uid, [], context=context)
            modupobj.config(cr, uid, [], context=context)
        
        # Update languages
        if updater_obj.lang_module_ids and updater_obj.lang_ids:
            if updater_obj.lang_overwrite:
                context = {'overwrite': True}        
            
            languages = [x.code for x in updater_obj.lang_ids]
            
            modobj.update_translations(cr, uid, [x.id for x in updater_obj.lang_module_ids], languages, context or {})
        
        self.write(cr, uid, ids, {'state': 'done'}, context=context)

        return {
            'name': _('Modules/Languages updated'),
            'view_type': 'form',
            'view_mode': 'form',
            'view_id': False,
            'res_model': 'module.updater',
            'domain': [],
            'context': dict(context, active_ids=ids),
            'type': 'ir.actions.act_window',
            'target': 'new',
            'res_id': ids and ids[0] or False,
        }
        
    def load_lang_modules(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
            
        for record in self.browse(cr, uid, ids, context=context):
            self.write(cr, uid, [record.id], {'lang_module_ids': [(6, 0, [x.id for x in record.update_module_ids])]}, context=context)

        return {
            'name':"Update Modules/Languages",
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'view_type': 'form',
            'res_model': 'module.updater',
            'res_id': ids[0],
            'target': 'new',
            'context': context,
        }
        
module_updater()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
