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

{
    'name': 'pc_intrum',
    'version': '1.0',
    'category': 'PC intrum justitia credit worthiness checker',
    'description': '''Module responsible of checking redit worthiness of partners''',
    'author': 'brain-tec AG',
    'website': 'http://www.braintec-group.com',
    'depends': ['base',
                'sale',
                'pc_connect_master',
                'pc_config',
                'account_voucher',
                'pc_issue',
                ],
    'init_xml': [],
    'data': [
        'data/schedulers.xml',
        'data/issue_tracking.xml',
        'data/intrum_response_codes_for_default_config.xml',

        'views/account_invoice_ext_view.xml',
        'views/account_voucher_ext_view.xml',
        'views/intrum_request_view.xml',
        'views/res_partner_ext_view.xml',
        'views/sale_order_ext_view.xml',
        'views/config_view.xml',
        'views/intrum_response_code_view.xml',
        'views/intrum_response_code_config_line_view.xml',

        "security/ir.model.access.csv",

        'views/menu.xml',
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
