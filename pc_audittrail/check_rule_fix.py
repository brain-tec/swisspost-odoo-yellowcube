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
from osv import osv, fields
from openerp.tools.translate import _
from openerp import pooler
from openerp import SUPERUSER_ID
from audittrail.audittrail import audittrail_objects_proxy


def __check_rules(self, cr, uid, model, method):
    """
    Checks if auditrails is installed for that db and then if one rule match
    @param cr: the current row, from the database cursor,
    @param uid: the current user’s ID,
    @param model: value of _name of the object which values are being changed
    @param method: method to log: create, read, unlink,write,actions,workflow actions
    @return: True or False

    The difference with the original method is that: 1) if 'method' is not 'load', then it may log an action.
                                                     2) it returns False when it returned None before.
    """
    pool = pooler.get_pool(cr.dbname)
    if 'audittrail.rule' in pool.models:
        model_ids = pool.get('ir.model').search(cr, SUPERUSER_ID, [('model', '=', model)])
        model_id = model_ids and model_ids[0] or False
        if model_id:
            rule_ids = pool.get('audittrail.rule').search(cr, SUPERUSER_ID, [('object_id', '=', model_id), ('state', '=', 'subscribed')])
            for rule in pool.get('audittrail.rule').read(cr, SUPERUSER_ID, rule_ids, ['user_id','log_read','log_write','log_create','log_unlink','log_action','log_workflow']):
                if len(rule['user_id']) == 0 or uid in rule['user_id']:
                    if rule.get('log_'+method,0):
                        return True
                    elif method not in ('load','default_get','read','fields_view_get','fields_get','search','search_count','name_search','name_get','get','request_get', 'get_sc', 'unlink', 'write', 'create', 'read_group', 'import_data'):
                        if rule['log_action']:
                            return True
    return False

audittrail_objects_proxy.check_rules = __check_rules

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:





