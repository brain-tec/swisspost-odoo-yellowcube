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
###############################################################################

{
    "name": "PostCommerce AP1/Purchase order report",

    "version": "1.0",

    'category': 'PC Purchase',

    'description': """
        Module responsible for generating the report for the purchase order.
    """,

    'author': 'brain-tec AG',

    'website': 'http://www.braintec-group.com',

    'depends': ['base',
                'purchase',
                'sale_margin',
                'report_webkit',
                'delivery',
                'pc_connect_master',
                'pc_generics',
                'pc_config',
                ],

    'init_xml': [
    ],

    'data': [
        'report/menu.xml',
        'data/email_template.xml',
        'view/purchase_config_view.xml',
    ],

    'css': [
    ],

    'demo_xml': [],

    'installable': True,
    
    # We don't want this module to be automatically installed when all its dependencies are loaded,
    # but we want us to install it under our control.
    "auto_install": False,

}

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
