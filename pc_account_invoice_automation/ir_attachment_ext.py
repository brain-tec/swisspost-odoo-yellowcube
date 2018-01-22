# b-*- encoding: utf-8 -*-
##############################################################################
#
#    Copyright (c) 2017 brain-tec AG (http://www.braintec-group.com)
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

from openerp.osv import osv, fields, orm
from openerp.tools import DEFAULT_SERVER_DATETIME_FORMAT, \
    DEFAULT_SERVER_DATE_FORMAT
from datetime import datetime


class ir_attachment_ext(osv.Model):
    _inherit = 'ir.attachment'

    def get_docout_exported_file_name(self, cr, uid, ids, context=None):
        """ Overridden because the original code assumes that an invoice
            has always a sale.order, but that is not the case for the
            Account.Invoice Automation.
        """
        if context is None:
            context = {}
        if not isinstance(ids, list):
            ids = [ids]
        assert len(ids) == 1, "ids must be a 1-element list."

        inv_obj = self.pool.get('account.invoice')

        attachment = self.browse(cr, uid, ids[0], context=context)
        invoice = inv_obj.browse(cr, uid, attachment.res_id, context=context)

        if not invoice.sale_ids:
            invoice_yyyymmdd = datetime.strptime(
                invoice.date_invoice, DEFAULT_SERVER_DATE_FORMAT). \
                strftime('%Y%m%d')
            docout_exported_file_name = \
                '{db}_ZS_{order_num}_{invoice_num}_{date}.pdf'.format(
                    db=cr.dbname,
                    order_num='NOORDER',
                    invoice_num=invoice.number.replace('/', ''),
                    date=invoice_yyyymmdd)

        else:
            docout_exported_file_name =\
                super(ir_attachment_ext, self).get_docout_exported_file_name(
                    self, cr, uid, ids, context=context)

        return docout_exported_file_name

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
