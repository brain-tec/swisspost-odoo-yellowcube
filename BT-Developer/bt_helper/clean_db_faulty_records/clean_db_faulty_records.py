# b-*- encoding: utf-8 -*-
##############################################################################
#
#    Copyright (c) 2015 brain-tec AG (http://www.brain-tec.ch)
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
from osv import osv, fields
from openerp import netsvc
from openerp.tools import ustr
import sys
import openerp.pooler as pooler
import logging
logger = logging.getLogger(__name__)


def _clean_db_faulty_records(models=None):
    # helper functions
    helper_functions = []

    def helper(f):
        """This decorator is used to ease the invocation of deleters"""
        helper_functions.append(f)

    @helper
    def _remove_ir_ui_view(pool, cr, model, res_id, modules, ctx):
        if model != 'ir.ui.view':
            return False
        # Avoid recursion
        if 'removed_ir_ui_view' not in ctx:
            ctx['removed_ir_ui_view'] = []
        elif res_id in ctx['removed_ir_ui_view']:
            return True
        ctx['removed_ir_ui_view'].append(res_id)

        cr.execute('select id from ir_ui_view where inherit_id = {0};'.format(res_id))
        for x in cr.fetchall():
            unlink_model(pool, cr, model, x[0], modules, ctx)

        unlink(pool, cr, model, res_id, modules, ctx)
        return True

    @helper
    def _remove_ir_model(pool, cr, model, res_id, modules, ctx):
        """Deleting models may have some side-effects"""
        if model != 'ir.model':
            return False

        cr.execute("SAVEPOINT deleting_ir_model;")
        try:
            unlink(pool, cr, model, res_id, modules, ctx)
        except Exception as e:
            cr.execute("ROLLBACK TO SAVEPOINT deleting_ir_model;")
            logger.error("Error unlinking model {0}: {1}".format(res_id, str(e)))
        else:
            cr.execute("RELEASE TO SAVEPOINT deleting_ir_model;")
        return True

    def mark_unlink(pool, cr, model, res_id, modules, ctx):
        """This function updates the list of modified modules"""
        cr.execute('select name, module from ir_model_data where res_id={0} and model=\'{1}\';'.format(res_id, model))
        for result in cr.fetchall():
            res_name = result[0]
            module_name = result[1]
            module = modules.get(module_name, {})
            if not module:
                modules[module_name] = module
            if res_name not in module:
                module[res_name] = {'name': res_name, 'model': model, 'res_id': res_id}
        pass

    def unlink(pool, cr, model, res_id, modules, ctx):
        """This function uses unlink, and marks the model as removed"""
        obj_pool = pool.get(model)
        obj_pool.unlink(cr, 1, res_id)
        mark_unlink(pool, cr, model, res_id, modules, ctx)

    def unlink_model(pool, cr, model, res_id, modules, ctx):
        """This function delegates the way models are deleted"""
        unlinked = False
        # Look for a valid unlink function
        for func in helper_functions:
            if func(pool, cr, model, res_id, modules, ctx):
                unlinked = True
                break
        # If not, use standard unlink
        if not unlinked:
            unlink(pool, cr, model, res_id, modules, ctx)

    # List of modules that changed
    changed_modules = {}
    db_name = sys.argv[1 + sys.argv.index('-d')]
    logger.debug('Checking database {0}import res for faulty ir.model.data'.format(db_name))
    registry, pool = pooler.get_db_and_pool(db_name)
    cr = registry.cursor()
    model_pool = pool.get('ir.model.data')
    # ids to check
    cr.execute('select id from ir_model_data where create_uid = 0;')
    model_ids = [x[0] for x in cr.fetchall()]

    for model_data in model_pool.browse(cr, 1, model_ids):
        # Only remove models on list
        if model_data.model is None or model_data.model in models:
            unlink_model(pool, cr, model_data.model, model_data.res_id, changed_modules, ctx={})

    cr.commit()
    cr.close()
    if changed_modules:
        logger.warning('Some records had been removed')
        for module_name in changed_modules:
            logger.warning('Update module {0}'.format(module_name))
            module = changed_modules[module_name]
            for item in module.values():
                logger.info('Deleted {model} {name}'.format(**item))
    else:
        logger.info('No record was changed')

"""

HOW-TO-USE

Run odoo with the option -d <database> and --stop-after-init

Mark any ir.model.data that needs to be deleted with create_uid=0
This code will remove the record (and any associate) that matches the condition,
and is one of the accepted models (Or any, if the list in this file last line is None)

Any modifications will appear in the logger


HOW-TO-EXTEND

Some models may require extra care, in that case, create a function and decorate with @helper

Take as an example _remove_ir_ui_view which checks recursion, and deletes items
(and marks them from deletion),

"""
if '-d' in sys.argv and '--stop-after-init' in sys.argv:
    _clean_db_faulty_records(['ir.ui.view', 'ir.model'])

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: