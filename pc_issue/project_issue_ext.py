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
from openerp.tools.translate import _
from openerp import SUPERUSER_ID
import logging
logger = logging.getLogger(__name__)


class project_issue_ext(osv.Model):
    _inherit = 'project.issue'

    def create_issue(self, cr, uid, res_model, res_id, error_message, tags=None, context=None):
        ''' Eases the creation of an issue: creates an issue with the indicated tags over
            the indicated res_id of the corresponding res_model. If no tags are indicated,
            then the issues are logged to the ['error'] category.
        '''
        if context is None:
            context = {}
        if tags is None:
            tags = ['error']

        new_cr = self.pool.db.cursor()
        try:
            project_issue_obj = self.pool.get('project.issue')
            issue_ids = project_issue_obj.find_resource_issues(new_cr, uid, res_model, res_id, tags=tags, create=True, reopen=True, context=context)
            for issue_id in issue_ids:
                project_issue_obj.message_post(new_cr, uid, issue_id, error_message, context=context)
        finally:
            new_cr.commit()
            new_cr.close()

        return True

    def open_record(self, cr, uid, ids, context=None):
        if context is None:
            context = {}

        for issue in self.browse(cr, uid, ids, context=context):
            return {
                'name': issue.name,
                'context': context,
                'view_type': 'form',
                'view_mode': 'form',
                'res_model': issue.model_id.model,
                'res_id': issue.res_id,
                'type': 'ir.actions.act_window',
                'target': None,
            }

    def _get_tag_ids(self, cr, uid, tags, context=None):
        ret = []
        if not tags:
            return []
        tags_obj = self.pool.get('project.category')
        for t in tags:
            _id = tags_obj.search(cr, uid, [('name', '=', t)], context=context)
            if len(_id) > 0:
                ret.extend(_id)
            else:
                ret.append(tags_obj.create(cr, SUPERUSER_ID, {'name': t}, context=context))
        return tags_obj.search(cr, uid, [('id', 'in', ret)], context=context)

    def find_resource_issues(self, cr, uid, table_name, res_id, tags=None, create=False, reopen=False, context=None):
        """
        This method finds the related Issues to a record, attending to a set of tags.

        In the case it does not exist, a Issue may be created, or and old one opened.

        @param table_name: record table of the object
        @param res_id: resource ID
        @param tags: list of tags (text) to filter by
        @param create: If no issue exists, should a new one be created
        @param reopen: If the issue is close, should the state be set to reopen
        @return: list of issue ids

        """
        if context is None:
            context = {}
        if isinstance(res_id, list):
            res_id = res_id[0]
        model_obj = self.pool.get('ir.model')
        model_ids = model_obj.search(cr, uid, [('model', '=', table_name)], context=context)
        new_stage_id = self.pool['ir.model.data'].get_object_reference(cr, uid, 'pc_issue', 'issue_new')[1]

        tags_set = set(tags or [])

        if not create or reopen:
            # Get the list of issues related with the record, that are not cancelled
            issue_ids = self.search(cr,
                                    uid,
                                    [('model_id', '=', model_ids[0]),
                                     ('res_id', '=', res_id),
                                     ('stage_id.state', '!=', 'cancelled'),
                                     # ('project_id', '=', support_project_id),
                                     ],
                                    context=context)
            if issue_ids:
                set_ids = []

                # If there is a tag filter, only consider those issues that share at least a tag name
                for issue in self.browse(cr, uid, issue_ids, context=context):
                    for categ in issue.categ_ids:
                        if categ.name in tags_set:
                            set_ids.append(issue.id)
                            break

                for issue in self.browse(cr, uid, set_ids, context=context):

                    if reopen and issue.stage_id.state == 'done':
                        # open any issues that where closed
                        self.write(cr, uid, [issue.id], {'stage_id': new_stage_id}, context=context)

                if set_ids:
                    return set_ids
            if not create:
                return []
        if create:
            # If an issue is not found, then create a new one
            support_project_id = self.pool['ir.model.data'].get_object_reference(cr, uid, 'pc_issue', 'support_project')[1]
            # Try to found a project that shares one of the tags, in order
            project_obj = self.pool.get('project.project')
            project_ids = project_obj.search(cr,
                                             uid,
                                             [('parent_id', '=', support_project_id)],
                                             context=context)
            tags_in_order = self._get_tag_ids(cr, uid, tags, context)
            tag = None
            if tags_in_order:
                tag = self.pool.get('project.category').browse(cr, uid, tags_in_order[0], context=context)
            project_id = None
            for tag_id in tags_in_order:
                if project_id:
                    break
                for project in project_obj.browse(cr, uid, project_ids, context=context):
                    if tag_id in [x.id for x in project.categ_ids]:
                        project_id = project.id
                        break

            # If not project is found, use default project
            if project_id is None:
                project_id = support_project_id

            model_name = model_obj.read(cr, uid, model_ids, ['name'], context=context)[0]['name']
            data = self.pool.get(table_name).read(cr, uid, res_id, ['name'], context=context)
            if data and ('name' in data):
                obj_name = data['name'].encode('ascii', 'xmlcharrefreplace')
            else:
                obj_name = '?{0}:{1}'.format(table_name, res_id)

            # Gets the partner associated to the user.
            res_user = self.pool.get('res.users').browse(cr, uid, uid, context=context)

            # On creating, issue tags are set
            data = {
                'name': context.get('issue_name', '{0}#{1}: {2}'.format(model_name, res_id, obj_name)),
                'description': context.get('issue_description', None),
                'stage_id': new_stage_id,
                'project_id': project_id,
                'model_id': model_ids[0],
                'res_id': res_id,
                'categ_ids': [(6, 0, tags_in_order)],
                'priority': tag.priority if tag else None,
                'partner_id': res_user.partner_id.id,
            }
            return [self.create(cr, uid, data, context=context)]
        return []

    def _reopen_tasks(self, cr, uid, ids, context=None):
        for issue in self.browse(cr, uid, ids, context=context):
            if issue.task_id is None or issue.task_id.stage_id is None:
                continue
            if issue.task_id.stage_id.state in ['done', 'cancelled'] and issue.task_id.issue_opened > 0:
                issue.task_id.do_reopen()
        return True

    _columns = {
        'model_id': fields.many2one('ir.model', 'Model', required=False),
        'res_id': fields.integer('Resource ID', required=False),
    }

    _constraints = [(_reopen_tasks, _("No task with open issues can be closed"), ['stage_id', 'task_id'])]


def __open_record_issue(self, cr, uid, ids, create=True, tags=None, context=None):
    """
    @param ids: id of the record, or None (in that case it is required an active_id
    @param create: is it a creationg process? (only when no-matching issue is found
    @param tags: list of tags to filter by, or assign on creation
    """
    if context is None:
        context = {}
    ids = ids or context.get('active_ids', [context['active_id']])
    if not isinstance(ids, list):
        ids = [ids]
    table_name = context.get('active_model', self._name)
    issue_ids = self.pool.get('project.issue').find_resource_issues(cr, uid, table_name, ids[0], tags=tags, create=create, reopen=create, context=context)
    if not create:
        return {
            'name': 'Open issues',
            'context': context,
            'view_type': 'form',
            'view_mode': 'tree,form',
            'domain': [('id', 'in', issue_ids)],
            'res_model': 'project.issue',
            'type': 'ir.actions.act_window',
            'target': None,
        }
    for issue in self.pool.get('project.issue').browse(cr, uid, issue_ids, context=context):
        return {
            'name': issue.name,
            'context': context,
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'project.issue',
            'res_id': issue.id,
            'type': 'ir.actions.act_window',
            'target': None,
        }

    raise osv.except_osv("Issue tracking", "Something went wrong with the issue tracking module.")


def __open_record_issue_v2(self, cr, uid, ids, create=True, tags=None, context=None):
    """
    @param ids: id of the record, or None (in that case it is required an active_id
    @param create: is it a creationg process? (only when no-matching issue is found
    @param tags: list of tags to filter by, or assign on creation
    """
    if context is None:
        context = {}
    ids = ids or context.get('active_ids', [context['active_id']])
    if not isinstance(ids, list):
        ids = [ids]
    table_name = context.get('active_model', self._name)
    vals = {
        'name': '',
        'description': '',
        'res_id': ids[0],
        'model_name': table_name,
        'tags': ' '.join(tags or []),
    }
    issue_wiz = self.pool.get('project.issue.open_wizard').create(cr, uid, vals, context=context)
    return {
        'name': 'Open Issue',
        'context': context,
        'view_type': 'form',
        'view_mode': 'form',
        'res_model': 'project.issue.open_wizard',
        'res_id': issue_wiz,
        'type': 'ir.actions.act_window',
        'target': 'new',
        'multi': 'f',
    }


osv.Model.open_record_issue = __open_record_issue
osv.Model.open_record_issue_v2 = __open_record_issue_v2

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
