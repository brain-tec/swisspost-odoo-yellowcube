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
from audittrail.audittrail import audittrail_objects_proxy
from openerp import SUPERUSER_ID


def __get_data(self, cr, uid, pool, res_ids, model, method, returns=None, iteration_limit=2):
    """
    This function simply read all the fields of the given res_ids, and also recurisvely on
    all records of a x2m fields read that need to be logged. Then it returns the result in
    convenient structure that will be used as comparison basis.

        :param cr: the current row, from the database cursor,
        :param uid: the current user’s ID. This parameter is currently not used as every
            operation to get data is made as super admin. Though, it could be usefull later.
        :param pool: current db's pooler object.
        :param res_ids: Id's of resource to be logged/compared.
        :param model: Object whose values are being changed
        :param method: method to log: create, read, unlink, write, actions, workflow actions
        :return: dict mapping a tuple (model_id, resource_id) with its value and textual value
            { (model_id, resource_id): { 'value': ...
                                         'textual_value': ...
                                       },
            }
    """
    if iteration_limit <= 0:
        return None
    return_key = '{0}#[{1}]'.format(model.id, ','.join(map(str, res_ids)))
    if returns is None:
        returns = {}
    data = {}
    if return_key in returns:
        return returns[return_key]
    if not res_ids or not res_ids[0]:
        return {}
    returns[return_key] = None
    resource_pool = pool.get(model.model)
    # read all the fields of the given resources in super admin mode
    for resource in resource_pool.read(cr, SUPERUSER_ID, res_ids, resource_pool._all_columns):
        values = {}
        values_text = {}
        resource_id = resource['id']
        # loop on each field on the res_ids we just have read
        for field in resource:
            if field in ('__last_update', 'id'):
                continue
            values[field] = resource[field]
            # get the textual value of that field for this record
            values_text[field] = self.get_value_text(cr, SUPERUSER_ID, pool, resource_pool, method, field, resource[field])

            field_obj = resource_pool._all_columns.get(field).column
            if field_obj._type in ('one2many','many2many'):
                # check if an audittrail rule apply in super admin mode
                if self.check_rules(cr, SUPERUSER_ID, field_obj._obj, method):
                    # check if the model associated to a *2m field exists, in super admin mode
                    x2m_model_ids = pool.get('ir.model').search(cr, SUPERUSER_ID, [('model', '=', field_obj._obj)])
                    x2m_model_id = x2m_model_ids and x2m_model_ids[0] or False
                    assert x2m_model_id, _("'%s' Model does not exist..." % (field_obj._obj))
                    x2m_model = pool.get('ir.model').browse(cr, SUPERUSER_ID, x2m_model_id)
                    field_resource_ids = list(set(resource[field]))
                    if model.model == x2m_model.model:
                        # we need to remove current resource_id from the many2many to prevent an infinit loop
                        if resource_id in field_resource_ids:
                            field_resource_ids.remove(resource_id)
                    val = self.get_data(cr, SUPERUSER_ID, pool, field_resource_ids, x2m_model, method, returns=returns, iteration_limit=iteration_limit - 1)
                    if val is not None:
                        data.update(val)

        data[(model.id, resource_id)] = {'text': values_text, 'value': values}
    if return_key in returns:
        del returns[return_key]
    return data


def __prepare_audittrail_log_line(self, cr, uid, pool, model, resource_id, method, old_values, new_values, field_list=None, returns=None, iteration_limit=2):
    """
    This function compares the old data (i.e before the method was executed) and the new data
    (after the method was executed) and returns a structure with all the needed information to
    log those differences.

    :param cr: the current row, from the database cursor,
    :param uid: the current user’s ID. This parameter is currently not used as every
        operation to get data is made as super admin. Though, it could be usefull later.
    :param pool: current db's pooler object.
    :param model: model object which values are being changed
    :param resource_id: ID of record to which values are being changed
    :param method: method to log: create, read, unlink, write, actions, workflow actions
    :param old_values: dict of values read before execution of the method
    :param new_values: dict of values read after execution of the method
    :param field_list: optional argument containing the list of fields to log. Currently only
        used when performing a read, it could be usefull later on if we want to log the write
        on specific fields only.

    :return: dictionary with
        * keys: tuples build as ID of model object to log and ID of resource to log
        * values: list of all the changes in field values for this couple (model, resource)
          return {
            (model.id, resource_id): []
          }

    The reason why the structure returned is build as above is because when modifying an existing
    record, we may have to log a change done in a x2many field of that object
    """
    if iteration_limit <= 0:
        return None
    if field_list is None:
        field_list = []
    key = (model.id, resource_id)
    lines = {
        key: []
    }
    return_key = '{0}#[{1}]'.format(model.id, resource_id)
    if returns is None:
        returns = {}
    if return_key in returns:
        return returns[return_key]
    returns[return_key] = None
    # loop on all the fields
    for field_name, field_definition in pool.get(model.model)._all_columns.items():
        if field_name in ('__last_update', 'id'):
            continue
        # if the field_list param is given, skip all the fields not in that list
        if field_list and field_name not in field_list:
            continue
        field_obj = field_definition.column
        if field_obj._type in ('one2many', 'many2many'):
            # checking if an audittrail rule apply in super admin mode
            if self.check_rules(cr, SUPERUSER_ID, field_obj._obj, method):
                # checking if the model associated to a *2m field exists, in super admin mode
                x2m_model_ids = pool.get('ir.model').search(cr, SUPERUSER_ID, [('model', '=', field_obj._obj)])
                x2m_model_id = x2m_model_ids and x2m_model_ids[0] or False
                assert x2m_model_id, _("'%s' Model does not exist..." % (field_obj._obj))
                x2m_model = pool.get('ir.model').browse(cr, SUPERUSER_ID, x2m_model_id)
                # the resource_ids that need to be checked are the sum of both old and previous values (because we
                # need to log also creation or deletion in those lists).
                x2m_old_values_ids = old_values.get(key, {'value': {}})['value'].get(field_name, [])
                x2m_new_values_ids = new_values.get(key, {'value': {}})['value'].get(field_name, [])
                # We use list(set(...)) to remove duplicates.
                res_ids = list(set(x2m_old_values_ids + x2m_new_values_ids))
                if model.model == x2m_model.model:
                    # we need to remove current resource_id from the many2many to prevent an infinit loop
                    if resource_id in res_ids:
                        res_ids.remove(resource_id)
                for res_id in res_ids:
                    val = self.prepare_audittrail_log_line(cr, SUPERUSER_ID, pool, x2m_model, res_id, method, old_values, new_values, field_list, returns=returns, iteration_limit=iteration_limit - 1)
                    if val is not None:
                        lines.update(val)
        # if the value value is different than the old value: record the change
        if key not in old_values or key not in new_values or old_values[key]['value'].get(field_name, None) != new_values[key]['value'].get(field_name, None):
            data = {
                'name': field_name,
                'new_value': key in new_values and new_values[key]['value'].get(field_name),
                'old_value': key in old_values and old_values[key]['value'].get(field_name),
                'new_value_text': key in new_values and new_values[key]['text'].get(field_name),
                'old_value_text': key in old_values and old_values[key]['text'].get(field_name)
            }
            lines[key].append(data)
        # On read log add current values for fields.
        if method == 'read':
            data = {
                'name': field_name,
                'old_value': key in old_values and old_values[key]['value'].get(field_name),
                'old_value_text': key in old_values and old_values[key]['text'].get(field_name)
            }
            lines[key].append(data)
    if return_key in returns:
        del returns[return_key]
    return lines

audittrail_objects_proxy.get_data = __get_data
audittrail_objects_proxy.prepare_audittrail_log_line = __prepare_audittrail_log_line

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
