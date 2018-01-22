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

{
    'name': 'pc_account_stage_discount',
    'version': '1.0',
    'category': 'PC Account With BT-Discount',
    'description': '''Module responsible of account.invoice's reports which have discounts
                      provided by the module stage_discount.
                   ''',
    'author': 'brain-tec AG',
    'website': 'http://www.braintec-group.com',
    'depends': ['base',
                'account',
                'account_asset',
                'pc_generics',
                'base_iban',
                'report_webkit',
                'l10n_ch_payment_slip',
                'sale',
                'pc_connect_master',
                'pc_config',
                'bt_account',
                'stage_discount',
                'pc_account',
                ],

    'init_xml': [],
    'data': [
         'report/menu.xml',

         'view/account_config_view.xml',

         'security/ir.model.access.csv',
    ],
    'css': [
    ],
    'demo_xml': [],
    'installable': True,

    # We don't want this module to be automatically installed when all its dependencies are loaded,
    # but we want us to install it under our control.
    "active": False,  # This is only for compatibility, since 'active' is now 'auto_install'.
    "auto_install": False,
}

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
