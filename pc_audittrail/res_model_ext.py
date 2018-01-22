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


def get_audit_logs(model_name):
    """
    This method creates a function that iterates through the audit logs associated with a model
    """
    def _get_audit_logs(self, cr, uid, ids, field, arg, context=None):
        result = {}
        model_id = self.pool.get('ir.model').search(cr, uid, [('model', '=', model_name)])[0]
        for object_id in ids:
            cr.execute("""SELECT id from audittrail_log WHERE object_id = {0} AND res_id = {1}""".format(model_id, object_id))
            audit_log_ids = [x[0] for x in cr.fetchall()]
            result[object_id] = audit_log_ids
        return result
    return _get_audit_logs

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
