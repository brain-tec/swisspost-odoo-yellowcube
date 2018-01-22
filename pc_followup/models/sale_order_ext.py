# b-*- encoding: utf-8 -*-
##############################################################################
#
#    Copyright (c) 2014 brain-tec AG (http://www.braintec-group.com)
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


class sale_order_ext(osv.Model):
    _inherit = 'sale.order'

    def is_sale_order_rejected_because_of_creditworthiness(self, cr, uid, ids, context=None):
        ''' This checks whether the sale.order must be rejected.
            If it is rejected, it must remain in state 'draft'.
            Returns an error message indicating the reason why the sale.order was rejected, or None
            otherwise.
        '''
        if context is None:
            context = {}
        if type(ids) is not list:
            ids = [ids]

        sale_order = self.browse(cr, uid, ids[0], context=context)

        # Checks if any previous checks result in some error message.
        error_message = super(sale_order_ext, self).is_sale_order_rejected_because_of_creditworthiness(cr, uid, sale_order.id, context=context)

        # If the sale order was e-paid, we do not take into account the follow-up block.
        # Thus, if it was not e-paid and the partner is under a follow-up block, then we block the invoice.
        if (not sale_order.payment_method_id.epayment) and sale_order.partner_id.under_followup_block:
            error_message = '{0}\n{1}'.format(error_message, _("Sale order cancelled due to pending follow-up actions"))

        return error_message

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
