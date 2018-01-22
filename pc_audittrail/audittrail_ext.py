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

from openerp.addons.audittrail.audittrail import audittrail_objects_proxy


_old_process_data = audittrail_objects_proxy.process_data


def __patch_process_data(self, cr, uid, pool, res_ids, model, method, old_values=None, new_values=None, field_list=None):
    ''' Modifies the method in order to miss the None values in the res_ids list
    '''
    new_res_ids = filter(lambda res_id: res_id is not None, res_ids)
    return _old_process_data(self, cr, uid, pool, new_res_ids, model, method, old_values, new_values, field_list)


# We change the process_data function for the new function patched __patch_process_data
audittrail_objects_proxy.process_data = __patch_process_data


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
