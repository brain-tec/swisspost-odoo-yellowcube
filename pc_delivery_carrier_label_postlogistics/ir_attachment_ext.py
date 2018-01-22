# b-*- encoding: utf-8 -*-
##############################################################################
#
#    Copyright (c) 2016 brain-tec AG (http://www.braintec-group.com)
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


class ir_attachment_ext(osv.Model):
    _inherit = 'ir.attachment'

    def _sel_get_document_type(self, cr, uid, context=None):
        ''' Extends the default method to add the option for the barcode report.
            (Read the doc-string of the extended method for the logic behind this way of
            extending the selection field).
        '''
        ret = super(ir_attachment_ext, self)._sel_get_document_type(cr, uid, context=context)
        ret.append(('barcode_out_report', 'Barcode Report for Picking Out'))
        return ret

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
