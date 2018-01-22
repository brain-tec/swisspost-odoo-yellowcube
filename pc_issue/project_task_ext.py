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
from openerp.osv import osv, fields
from openerp.tools.translate import _


class project_task_ext(osv.Model):
    _inherit = 'project.task'

    def _count_issues(self, cr, uid, ids, field, arg, context=None):
        res = {}
        for _id in ids:
            res[_id] = len(self.pool['project.issue'].search(cr, uid, [('task_id', '=', _id), ('stage_id.state', 'in', arg)], context=context))
        return res

    def _store_by_issues(self, cr, uid, ids, ctx):
        return [x['task_id'][0] for x in self.pool['project.issue'].read(cr, uid, ids, ['task_id']) if 'task_id' in x and x['task_id']]

    def _before_close(self, cr, uid, ids, context=None):
        for task in self.browse(cr, uid, ids, context=context):
            if task.stage_id is None:
                continue
            if task.stage_id.state in ['done', 'cancelled'] and task.issue_opened > 0:
                return False
        return True

    _columns = {
        'issue_ids': fields.one2many('project.issue', 'task_id', string='Associated issues'),
        'issue_opened': fields.function(_count_issues,
                                        arg=['open', 'draft', 'pending'],
                                        type='integer',
                                        store={'project.issue': (_store_by_issues,
                                                                 ['task_id', 'stage_id'],
                                                                 10
                                                                 )}
                                        ),
        'issue_closed': fields.function(_count_issues,
                                        arg=['done'],
                                        type='integer',
                                        store={'project.issue': (_store_by_issues,
                                                                 ['task_id', 'stage_id'],
                                                                 10
                                                                 )}
                                        ),
    }

    _constraints = [(_before_close, _("No task with open issues can be closed"), ['stage_id'])]

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: