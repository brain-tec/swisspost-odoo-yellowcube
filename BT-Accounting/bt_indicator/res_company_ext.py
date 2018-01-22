# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2012 OpenERP SA (<http://openerp.com>)
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

from openerp.osv import fields, osv

class res_company_balance(osv.osv):
    _inherit = 'res.company'
    _columns = {
        'property_balance_start_account': fields.property(
            'account.account',
            type='many2one',
            relation='account.account',
            string="Balance Start Account",
            method=True,
            view_load=True,
            required=True,
            domain="[('type', '=', 'view')]",
            help="This Account is used for start view account in balance sheet for bt_indicator."),
        'property_balance_actives_account': fields.property(
            'account.account',
            type='many2one',
            relation='account.account',
            string="Balance Actives Account",
            method=True,
            view_load=True,
            required=True,
            domain="[('type', '=', 'view')]",
            help="This Account is used for actives view account in balance sheet for bt_indicator."),
        'property_balance_passives_account': fields.property(
            'account.account',
            type='many2one',
            relation='account.account',
            string="Balance Passives Account",
            method=True,
            view_load=True,
            required=True,
            domain="[('type', '=', 'view')]",
            help="This Account is used for passives view account in balance sheet for bt_indicator."),
    }

res_company_balance()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: