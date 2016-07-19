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

{
    "name": "SwissPost YellowCube Odoo / Connect Warehouse",

    "version": "1.0",

    "description": """Provides an interface to create and manage connections to electronic warehouses

    Depends on the following modules from OCA:
    - connector (from repository connector: https://github.com/OCA/connector)
    - product_links (from repository e-commerce: https://github.com/OCA/e-commerce)
    """,

    "author": "Brain-tec",

    "category": "",

    'depends': ['stock',
                'product_links',
                'connector',
                'pc_connect_master',
                'pc_connect_transport',
                'pc_config',
                'pc_issue',
                ],

    "data": ['security/ir.model.access.csv',
             'data/schedulers.xml',
             'data/stock_warehouse_location.xml',
             'data/stock_connect_file.xml',

             # Views
             'views/stock_connect.xml',
             'views/stock_connect_file.xml',
             'views/stock_event.xml',
             'views/stock_location_ext.xml',
             'views/stock_picking_ext_view.xml',
             'views/stock_warehouse_ext.xml',
             'views/alarming_config_view.xml',

             # This must be last
             'views/menu.xml'
             ],

    "demo": ['demo/connection.xml',
             ],

    "test": [
    ],

    "installable": True,

    # We don't want this module to be automatically installed when all its dependencies are loaded,
    # but we want us to install it under our control.
    "auto_install": False,
}

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
