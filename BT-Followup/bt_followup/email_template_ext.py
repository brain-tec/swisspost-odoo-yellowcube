# b-*- encoding: utf-8 -*-
#
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


from tools.translate import _
from osv import fields, osv


class email_template_ext(osv.osv):
    _inherit = "email.template"

    def generate_email(self, cr, uid, template_id, res_id, context=None):
        ''' Overriden because we need to:
            - Provide a wildcard substitution mechanism.
            - Mark the emails as type 'email' to allow an automatic sending.
        '''
        if context is None:
            context = {}

        values = super(email_template_ext, self).generate_email(cr, uid, template_id, res_id, context=context)

        if 'default_type' in context:
            values['type'] = context['default_type']

        if 'wildcards' in context:
            # If 'wildcards' is in context, then we want to substitute some wildcards.
            for body_type in ('body', 'body_html'):
                if body_type in values:
                    for wildcard, content in context['wildcards']:
                        values[body_type] = values[body_type].replace(wildcard, str(content or ''))

        return values
