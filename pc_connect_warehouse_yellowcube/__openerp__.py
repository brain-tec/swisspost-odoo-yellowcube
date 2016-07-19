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
    "name": "SwissPost YellowCube Odoo / Connect Warehouse YellowCube",

    "version": "1.0",

    "description": "Provides an interface to create and manage connections to YellowCube",

    "author": "Brain-tec",

    "category": "",

    'depends': ['account',
                'pc_connect_warehouse',
                'pc_connect_transport_FDS',
                'pc_connect_master',
                'delivery',
                'sale_payment_method',
                'purchase',
                'product',
                'stock',
                'report_webkit',
                ],

    "data": ['security/ir.model.access.csv',
             'data/schedulers.xml',

             'views/configuration_data.xml',
             'views/delivery_carrier_ext_view.xml',
             'views/mapping_bur_transactiontypes_view.xml',
             'views/stock_connect_ext.xml',
             'views/stock_warehouse_ext.xml',
             'views/stock_picking_ext_view.xml',
             'views/stock_picking_return_ext.xml',
             'views/stock_production_lot_ext_view.xml',
             'views/stock_move_ext_view.xml',
             'views/product_product_ext_view.xml',
             'views/sale_order_ext_view.xml',
             'views/res_partner_ext_view.xml',
             ],

    "demo": ['demo/connection.xml',
             'demo/partner.xml',
             'demo/product.xml',
             'demo/warehouse.xml',
             'demo/sale.xml',
             ],

    "test": ['test/test_bar_process_correct_file.yml',
             'test/test_bar_process_incorrect_file.yml',  # Commented out because this test raises an exception.
             ],

    "installable": True,

    # We don't want this module to be automatically installed when all its dependencies are loaded,
    # but we want us to install it under our control.
    "auto_install": False,
}

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
