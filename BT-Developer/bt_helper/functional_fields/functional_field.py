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
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program. If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

from osv import fields, osv
from openerp.tools.translate import _
from osv import fields, osv, expression

from bt_helper.log_rotate import get_log
logger = get_log('DEBUG')


def str2tuple(s):
    return eval('tuple(%s)' % (s or ''))


class functional_field(osv.osv):
    _name = 'bt_helper.functional_field'
    _description = 'BT Functional field'

    _columns = {
        'model_id': fields.many2one('ir.model', 'Model', required=True),
        'field_id': fields.many2one('ir.model.fields', _('Field to Modify'), required=True, domain="[('model_id', '=', model_id)]"),
        'function': fields.char('Method', size=64, help="Name of the method to be called when this job is processed."),
        'multi_function': fields.boolean('Multi', help="Set true if the function is multi"),
        'args': fields.text('Arguments', help="Arguments to be passed to the method, e.g. (uid,)."),
        'conditions': fields.text('Conditions', help="Conditions"),
        'add_to_cron': fields.boolean('Add to Cron', help="Adds this functional field to a cron job"),
        'update_write_date': fields.boolean('Update Write Date', help="To update write date"),
    }

    _defaults = {
        'add_to_cron': False,
        'conditions': '[]',
        'args': '',
        'update_write_date': False
    }

    def do_calculate_functional(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        new_cr = self.pool.db.cursor()

        for functional_field in self.browse(cr, uid, ids, context):
            conditions = expression.normalize(eval(functional_field.conditions, {}))
            model_obj = self.pool.get(functional_field.model_id.model)
            object_ids = model_obj.search(cr, uid, conditions, context=context)
            method = getattr(model_obj, functional_field.function)
            chunks = [object_ids[x:x + 100] for x in xrange(0, len(object_ids), 100)]

            for object_ids in chunks:
                values = method(cr, uid, object_ids, functional_field.field_id.name, str2tuple(functional_field.args))

                if functional_field.multi_function:
#                     values = values[functional_field.field_id.name]
                    for k, v in values.iteritems():
                        values[k] = v[functional_field.field_id.name]

                for k, v in values.iteritems():
                    database_name = functional_field.model_id.model.replace(".", "_")

                    try:

                        if functional_field.update_write_date:
                            query = """UPDATE {0} SET {1} = {2}, write_date = NOW() AT TIME ZONE 'UTC' WHERE id = {3}"""
                            query = query.format(database_name, functional_field.field_id.name, (("'" + v.replace("'", "''") + "'") if isinstance(v, basestring) else v), k)
                        else:
                            query = """UPDATE {0} SET {1} = {2} WHERE id = {3}"""
                            query = query.format(database_name, functional_field.field_id.name, (("'" + v.replace("'", "''") + "'") if isinstance(v, basestring) else v), k)

                        logger.debug(query)
                        new_cr.execute(query)
                        new_cr.commit()
                    except:
                        logger.error("Error while updating {0} {1} {2} {3}".format(database_name, functional_field.field_id.name, v, k))
                        new_cr.close()
                        new_cr = self.pool.db.cursor()

        new_cr.close()
        return True

    def cron_update_functional_field(self, cr, uid, context={}):
        functional_field_ids = self.search(cr, uid, [('add_to_cron', '=', True)], context=context)

        for functional_field in self.browse(cr, uid, functional_field_ids, context):
            functional_field.do_calculate_functional()

        return True
