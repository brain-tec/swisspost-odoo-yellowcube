# b-*- encoding: utf-8 -*-
##############################################################################
#
#    Copyright (c) 2014 brain-tec AG (http://www.brain-tec.ch)
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

from osv import osv, fields
from tools import config
import decimal_precision as dp
from discount_line import _DISCOUNT_TYPE


class account_invoice_line_ext(osv.osv):
    _inherit = "account.invoice.line"
    _order = "is_discount asc,invoice_id,sequence,id"
    _columns = {'is_discount': fields.boolean('Discount'),
                'discount_type': fields.selection(_DISCOUNT_TYPE, 'Discount Type'),
                'is_subtotal': fields.boolean('Is  subtotal'),
                'is_fixed_amount': fields.boolean('Is fixed amount'),
                'is_rounding_line': fields.boolean('Is rounding line'),
                'discount_description': fields.text('Description of discount'),
                'discount_amount': fields.text('Discount value'),
                'discount_account_id': fields.many2one('account.account', 'Account')
                }
    _defaults = {
        'is_discount': False,
        'is_subtotal': False,
        'is_fixed_amount': False,
        'is_rounding_line': False
    }

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
