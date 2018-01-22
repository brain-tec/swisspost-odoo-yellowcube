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
    'name': 'PostCommerce AP1/Graphical User Interface-based Reports',
    'version': '1.0',
    'description': 'Provides Graphical User Interface-based Reports under the menu E-Commerce',
    'author': 'Brain-tec',
    'category': '',

    'depends': ['pc_connect_master',
                'bt_account',  # For the extra column in the account.invoice.line about the amount with discount.
                'bt_tax',  # For the reports of E-Commerce.
                'bt_followup',  # To change the permissions of the tab.
                'board',  # For the reports of E-Commerce.
                'sale'
                ],

    'data': ['views/account_invoice_report_view_ext.xml',
             'views/account_invoice_reporting.xml',
             'views/product_product_reporting.xml',
             'views/res_partner_reporting.xml',
             'views/stock_production_lot_reporting.xml',
             'views/sale_report_view_ext.xml',

             'security/ir.model.access.csv',

             'views/menu.xml',
             ],

    'installable': True,

    # We don't want this module to be automatically installed when all its dependencies are loaded,
    # but we want us to install it under our control.
    'active': False,  # This is only for compatibility, since 'active' is now 'auto_install'.
    'auto_install': False,
}

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
