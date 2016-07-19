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
    "name": "SwissPost YellowCube Odoo / Connect Warehouse YellowCube over SOAP",

    "version": "1.0",

    "description": "Provides an interface to create and manage connections to YellowCube",

    "author": "Brain-tec",

    "category": "",

    'depends': ['pc_connect_master',
                'pc_connect_warehouse_yellowcube',
                'pc_config',
                ],

    "data": ['security/ir.model.access.csv',
             'views/stock_connect_ext.xml',
             ],

    "demo": ['demo/connection.xml',
             ],

    "test": [],

    "installable": True,

    # We don't want this module to be automatically installed when all its dependencies are loaded,
    # but we want us to install it under our control.
    "auto_install": False,
}

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
