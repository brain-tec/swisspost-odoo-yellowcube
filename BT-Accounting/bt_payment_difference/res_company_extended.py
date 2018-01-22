# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>).
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

from osv import fields, osv

class res_company_extended(osv.osv):
    _inherit = "res.company"
    _columns = {
        'property_currency_difference_account': fields.property(
            'account.account',
            type='many2one',
            relation='account.account',
            string="Currency Payment Difference Account",
            method=True,
            view_load=True,
            required=True,
            domain="[('type', '=', 'other')]",
            help="This Account is used for transferring currency payment differences."),
        'property_rounding_difference_cost_account': fields.property(
            'account.account',
            type='many2one',
            relation='account.account',
            string="Rounding Payment Difference Cost Account",
            method=True,
            view_load=True,
            required=True,
            domain="[('type', '=', 'other')]",
            help="This Account is used for transferring rounding payment differences for costs."),
        'property_rounding_difference_profit_account': fields.property(
            'account.account',
            type='many2one',
            relation='account.account',
            string="Rounding Payment Difference Profit Account",
            method=True,
            view_load=True,
            required=True,
            domain="[('type', '=', 'other')]",
            help="This Account is used for transferring rounding payment differences for profit."),
        'property_currency_difference_analytic_account': fields.property(
            'account.analytic.account',
            type='many2one',
            relation='account.analytic.account',
            string="Currency Payment Difference Analytic Account",
            method=True,
            view_load=True,
            required=False,
            domain="[('type', '=', 'normal'),('state', '=', 'open')]",
            help="This Analyitc Account is used for transferring currency payment differences."),
    }

res_company_extended()
