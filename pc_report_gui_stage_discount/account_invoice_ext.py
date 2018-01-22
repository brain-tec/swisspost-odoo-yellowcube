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


class account_invoice_ext(osv.Model):
    _inherit = 'account.invoice'

    def _fun_discount(self, cr, uid, ids, discount, arg, context=None):
        ''' Computes the total amount corresponding to discounts on the invoice.
                This overrides the default function to take also into account the
            lines which are discount lines.
        '''
        if context is None:
            context = {}
        res = {}

        for invoice in self.browse(cr, uid, ids, context=context):
            res[invoice.id] = 0.0

            # Sums up the discounts applied to every line.
            for invoice_line in invoice.invoice_line:
                if invoice_line.discount:
                    res[invoice.id] += (invoice_line.price_total - invoice_line.price_total_less_disc)

            # Sums up the discounts indicated in the discount lines.
            for discount_line in invoice.discount_invoice_line_ids:
                if discount_line.is_discount and (discount_line.price_unit < 0):
                    res[invoice.id] += abs(discount_line.price_unit)

        return res

    _columns = {
        'discount': fields.function(_fun_discount, string='Total Discount', type='float', readonly=True,
                                    help='Computes the total amount discounted on the invoice.',
                                    store=False)
    }

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
