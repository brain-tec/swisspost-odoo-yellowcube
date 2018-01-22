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

from openerp.osv import fields, osv


class wizard_account_invoice_refund_ext(osv.osv_memory):

    _inherit = "account.invoice.refund"

    def compute_refund(self, cr, uid, ids, mode='refund', context=None):
        """ Extended so that we keep track of the invoice which was refunded.
        """
        context['refunded_invoice_id'] = context.get('active_id', False)
        data = super(wizard_account_invoice_refund_ext, self).compute_refund(cr, uid, ids, mode, context)
        del context['refunded_invoice_id']
        return data

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
