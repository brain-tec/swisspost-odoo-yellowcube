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
import base64
import os


class ir_attachment_ext(osv.Model):
    _inherit = 'ir.attachment'

    def get_docout_followup_email_address(self, cr, uid, ids, context=None):
        ''' This is the email address the follow-ups which must be sent to a doc-out are sent to.
        '''
        if context is None:
            context = {}
        configuration_data = self.pool.get('configuration.data').get(cr, uid, None, context)
        return configuration_data.docout_followup_email_address

    def _sel_get_docout_file_type(self, cr, uid, context=None):
        ''' Overrides the default method to add the option of exporting a follow-up.
        '''
        ret = super(ir_attachment_ext, self)._sel_get_docout_file_type(cr, uid, context=context)
        ret.append(('followup', 'Follow-up'))
        return ret

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
