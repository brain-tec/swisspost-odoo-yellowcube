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

{
    "name": "PostCommerce AP1/Connect Warehouse External Email",
    "version": "1.0",
    "description": "Provides a pseudo-warehouse which consists in sending the orders by email.",
    "author": "Brain-tec",
    "category": "",

    'depends': ['mail',
                'pc_connect_master',
                'pc_connect_warehouse',
                'pc_config',
                'pc_generics',
                'pc_delivery_carrier_label_postlogistics',
                'pc_issue',
                ],

    "data": ['data/email_template_external.xml',

             'views/configuration_data.xml',
             'views/stock_connect_view_ext.xml',
             'views/mail_mail_view_ext.xml',

             'views/menu.xml',
             'reports/menu.xml',
             ],

    "demo": [],

    "test": [],

    "installable": True,

    # We don't want this module to be automatically installed when all its dependencies are loaded,
    # but we want us to install it under our control.
    "active": False,  # This is only for compatibility, since 'active' is now 'auto_install'.
    "auto_install": False,
}

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
