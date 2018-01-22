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


class log_data_ext(osv.Model):

    _inherit = 'log.data'

    def create(self, cr, uid, values, context=None):
        if context is None:
            context = {}
        ret = super(log_data_ext, self).create(cr, uid, values, context=context)
        correct = values['correct']
        table_name = values['table_name']
        ref_id = values['ref_id']
        tags = ['error', 'log.data'] if not correct else ['log.data']
        tb = context.get('thread_body', values['information'])

        issue_ids = self.pool.get('project.issue').find_resource_issues(cr, uid, table_name, ref_id, tags=tags, create=(not correct), reopen=(not correct), context=context)
        for issue in self.pool.get('project.issue').browse(cr, uid, issue_ids, context=context):
            issue.message_post(tb)
        return ret


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: