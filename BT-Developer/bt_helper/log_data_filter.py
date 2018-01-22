# b-*- encoding: utf-8 -*-
##############################################################################
#
#    Copyright (c) 2014 brain-tec AG (http://www.brain-tec.ch)
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

from openerp.osv import osv, fields
from bt_helper.log_rotate import get_log
logger = get_log()


class log_data_filter(osv.Model):
    '''
    Table used
    '''
    _name = 'log.data.filter'
    _description = "Log Data Filter"

    def name_get(self, cursor, uid, ids, context=None):
        res = []
        for var_filter in self.browse(cursor, uid, ids, context=context):
            res.append((var_filter.id, var_filter.model_id.name))
        return res

    _columns = {
        'model_id': fields.many2one('ir.model', 'Model', required=True),
        'log_normal_execution': fields.boolean('Log normal execution'),
        'log_error': fields.boolean('Log Error'),
    }
    _defaults = {
        'log_normal_execution': False,
        'log_error': False
    }


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
