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

from osv import osv, fields
from tools.translate import _
import time


class database_information(osv.osv):
    _name = 'bt_helper.database_information'
    _description = 'Database information'

    _columns = {
        'partial_calculation_ids': fields.one2many('bt_helper.partial_calculation', 'wizard_id',
                                                        _('Database information')),
        'state': fields.selection([('init', 'init'), ('done', 'done')], 'Status', readonly=True),
        'name': fields.datetime(_('Due Date'), required=True),


    }

    _defaults = {
               'state': 'init',
               'name': lambda self, cr, uid, context: time.strftime('%Y-%m-%d'),
               }

    def get_classes_columns(self, cr, uid, ids, context={}):
        query = """select table_name,column_name
                    from INFORMATION_SCHEMA.COLUMNS as info"""
        cr.execute(query)
        data_information = cr.dictfetchall()
        not_check = ['information_schema_catalog_name', 'applicable_roles',
                                         'administrable_role_authorizations',
                                         'attributes',
                                         'character_sets',
                                         'check_constraint_routine_usage']
        for element in data_information:
            if element['table_name'] in not_check:
                continue
            new_cursor = self.pool.db.cursor() 
            query = """select pg_size_pretty(sum(octet_length({0}::text))) as size
                        from {1}""".format(element['column_name'], element['table_name'])
            try:
                new_cursor.execute(query)
            except:
                new_cursor.close()
                not_check.append(element['table_name'])
                continue
            size = new_cursor.dictfetchone()['size']
            new_cursor.close()
            values = {
                     'table': element['table_name'],
                     'column': element['column_name'],
                     'size': size,
                     'wizard_id': ids[0],
                     }
            self.pool.get('bt_helper.partial_calculation').create(cr, uid, values)
       
        return self.write(cr, uid, ids, {'state': 'done'})


class partial_calculation(osv.osv):
    _name = 'bt_helper.partial_calculation'

    def _fun_calculate_size(self, cr, uid, ids, name, args, context=None):
        result = {}
        for elem in self.browse(cr, uid, ids, context):
            if not elem.size:
                result[elem.id] = 0
                continue
            unit = elem.size.split(' ')[1]
            result[elem.id] = float(elem.size.split(' ')[0])
            if unit == 'bytes':
                base = 1024 * 1024
            elif unit == 'GB':
                base = 1.0 / 1024
            elif unit == 'MB':
                base = 1.0
            elif unit == 'kB':
                base = 1024

            result[elem.id] = result[elem.id] / base
        return result

    _columns = {
        'table': fields.text('Table'),
        'column': fields.text(_('Column')),
        'size': fields.text('Size'),
        'wizard_id': fields.many2one('bt_helper.database_information', _('Report'), ondelete='cascade'),
        'size_number': fields.function(_fun_calculate_size, type='float', string='Size in MB',
                                       store={
                                              'bt_helper.partial_calculation': (lambda self, cr, uid, ids, c={}: ids, ['size'], 10),
                                              }
                                       ),
        }
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
