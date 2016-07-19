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
import logging
logger = logging.getLogger(__name__)


class open_issue(osv.TransientModel):
    _name = 'project.issue.open_wizard'

    def create_issue(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        for wiz in self.browse(cr, uid, ids, context=context):
            context['issue_name'] = wiz.name
            context['issue_description'] = wiz.description
            issue_id = self.pool.get('project.issue').find_resource_issues(cr,
                                                                           uid,
                                                                           wiz.model_name,
                                                                           wiz.res_id,
                                                                           tags=['user-generated'],
                                                                           create=True,
                                                                           reopen=False,
                                                                           context=context)[0]
            return {
                'name': wiz.name,
                'context': context,
                'view_type': 'form',
                'view_mode': 'form',
                'res_model': 'project.issue',
                'res_id': issue_id,
                'type': 'ir.actions.act_window',
                'target': 'current',
            }

    def _issues_ids(self, cr, uid, ids, field, arg, context=None):
        ret = {}
        for wiz in self.browse(cr, uid, ids, context=context):
            ret[wiz.id] = self.pool.get('project.issue').find_resource_issues(cr,
                                                                              uid,
                                                                              wiz.model_name,
                                                                              wiz.res_id,
                                                                              tags=None,
                                                                              create=False,
                                                                              reopen=False,
                                                                              context=context)
        return ret

    _columns = {
        'name': fields.char(string='Name', required=True),
        'description': fields.text(string='Description', required=True),
        'tags': fields.text(string='Tags', required=True),
        'res_id': fields.integer(required=True),
        'model_name': fields.text(required=True),
        'issues_ids': fields.function(_issues_ids, type='one2many', obj='project.issue', string='Related issues', readonly=True)
    }

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
