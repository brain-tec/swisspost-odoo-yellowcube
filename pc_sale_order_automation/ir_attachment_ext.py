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


_DOCOUT_STATES = [
    ('not_applicable', 'Not Applicable'),
    ('to_send', 'To Send'),
    ('sent', 'Sent'),
]


class ir_attachment_ext(osv.Model):
    _inherit = 'ir.attachment'

    def default_get(self, cr, uid, fields_list, context=None):
        ret = super(ir_attachment_ext, self).default_get(cr, uid, fields_list, context=context)

        for docout_variable in ['docout_state_email', 'docout_state_remote_folder']:
            if docout_variable not in ret:
                ret[docout_variable] = 'not_applicable'

        return ret

    def get_docout_invoice_email_address(self, cr, uid, ids, context=None):
        ''' This is the email address the invoices which must be sent to a doc-out are sent to.
        '''
        if context is None:
            context = {}
        configuration_data = self.pool.get('configuration.data').get(cr, uid, None, context)
        return configuration_data.docout_invoice_email_address

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
