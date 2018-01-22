# b-*- encoding: utf-8 -*-
##############################################################################
#
#    Copyright (c) 2017 brain-tec AG (http://www.braintec-group.com)
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
    "name": "PostCommerce AP1/Account Invoice Automation",

    "version": "1.0",

    "description": """
        Automates a sale.order if its check-box 'Account Invoice Automation'
        is set. If that is the case, then the account.invoice creates a 
        job (from the module 'connector') which, in collaboration with a 
        scheduler, moves the account.invoice through a list of states.
    """,

    "author": "brain-tec AG",

    "category": "",

    'depends': [
        'account',
        'base',
        'connector',
        'report_webkit',

        'pc_config',
        'pc_connect_master',
        'pc_docout',
        'bt_account',
        'bt_helper',

        'pc_account_pf',  # For the reports (will change with the new templates)
    ],

    "data": [
        'data/invoice_routing_email_default_template.xml',

        'views/account_invoice_view_ext.xml',
        'views/configuration_data_view_ext.xml',
    ],

    "demo": [
    ],

    "test": [
    ],

    "installable": True,

    # We don't want this module to be automatically installed when
    # all its dependencies are loaded, but we want us to install it
    # under our control.
    "auto_install": False,
}

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
