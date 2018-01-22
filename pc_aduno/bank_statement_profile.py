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
from openerp.osv.orm import Model, fields


class bank_statement_profile(Model):
    _inherit = 'account.statement.profile'

    _columns = {
        'merchant_id': fields.char(string="Merchant ID"),
        'merchant_subsidiary_id': fields.char(string="Merchant Subsidiary ID"),
        # PAyment difference type: Abschreibungsgrund: Skonto: ID 1
        'payment_type_discount_id': fields.many2one('payment.difference.type',
                                                    string="Discount Payment type", required=True),
        # PAyment difference type: Kreditkartengebühr
        'payment_type_commission_id': fields.many2one('payment.difference.type',
                                                    string="Commission Payment type", required=True),
    }
