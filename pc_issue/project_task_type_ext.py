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
from openerp.osv import osv, fields

_TASK_STATE = [('draft', 'New'), ('open', 'In Progress'), ('pending', 'Pending'), ('done', 'Done'), ('cancelled', 'Cancelled')]


class project_task_type_ext(osv.Model):
    _inherit = 'project.task.type'

    _columns = {
        'state': fields.selection(_TASK_STATE, 'Related Status', required=True,
                                  help="The status of your document is automatically changed regarding the selected stage. "
                                  "For example, if a stage is related to the status 'Close', when your document reaches this stage, it is automatically closed."),
    }

    _defaults = {
        'state': 'open',
    }

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
