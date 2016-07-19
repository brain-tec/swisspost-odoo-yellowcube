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


class payment_method_ext(osv.Model):
    _inherit = 'payment.method'

    _columns = {
        'epayment': fields.boolean('ePayment?', help='Does this payment method allow ePayment?'),
        'pre_payment': fields.boolean('Pre-Payment?', help='If checked, the delivery is sent only if the invoice has been already paid.'),
        'amount_limit': fields.float('Amount Limit', help='The maximum allowed amount that can be paid using this payment method.'),
        'credit_check': fields.boolean('Credit Check?', help='Does the system have to check the creditworthiness of customers with this payment method?'),
    }

    _defaults = {
        'credit_check': True,
        'pre_payment': True,
        'epayment': False,
        'amount_limit': 0,
    }

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
