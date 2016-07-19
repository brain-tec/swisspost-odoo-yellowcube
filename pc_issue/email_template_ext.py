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
from openerp.addons.email_template.email_template import mako_template_env
from openerp import tools
import traceback
import logging
logger = logging.getLogger(__name__)


class email_template_ext(osv.osv):
    _inherit = "email.template"

    def render_template(self, cr, uid, template, model, res_id, context=None):
        """Render the given template text, replace mako expressions ``${expr}``
           with the result of evaluating these expressions with
           an evaluation context containing:

                * ``user``: browse_record of the current user
                * ``object``: browse_record of the document record this mail is
                              related to
                * ``context``: the context passed to the mail composition wizard

           :param str template: the template text to render
           :param str model: model name of the document record this mail is related to.
           :param int res_id: id of the document record this mail is related to.
        """
        if not template:
            return u""
        if context is None:
            context = {}
        try:
            template = tools.ustr(template)
            record = None
            if res_id:
                record = self.pool.get(model).browse(cr, uid, res_id, context=context)
            user = self.pool.get('res.users').browse(cr, uid, uid, context=context)
            variables = {
                'object': record,
                'user': user,
                'ctx': context,     # context kw would clash with mako internals
            }
            result = mako_template_env.from_string(template).render(variables)
            if result == u"False":
                result = u""
            return result
        except Exception as e:
            logger.exception("failed to render mako template value %r", template)
            logger.exception(e)
            issue_obj = self.pool.get('project.issue')
            for issue_id in issue_obj.find_resource_issues(cr,
                                                           uid,
                                                           model,
                                                           res_id,
                                                           tags=['email.template', 'error'],
                                                           create=True,
                                                           reopen=True,
                                                           context=context):
                # A message is trigger in a new/open issue
                issue_obj.message_post(cr, uid, issue_id, _('Exception on email.template<br/><b>{0}</b>:<br/>{1}<br/>{2}').format(e,
                                                                                                                                  traceback.format_exc(limit=10).replace('\n', '<br/>'),
                                                                                                                                  template.replace('<', '&lt;').replace('\n', '<br/>')), context=context)
            return u""

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
