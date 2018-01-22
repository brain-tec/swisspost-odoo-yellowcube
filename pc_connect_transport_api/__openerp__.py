# -*- coding: utf-8 -*-
#
#    Copyright (c) 2017 brain-tec AG (http://www.braintec-group.com)
#    All Right Reserved
#
#    See LICENSE file for full licensing details.

{
    "name": "PostCommerce AP1/Connect Transport API",
    "version": "1.0",
    "description": "Provides an interface receive to create and manage connections",
    "author": "Brain-tec",
    "category": "",

    'depends': ['pc_connect_warehouse',
                'pc_connect_warehouse_yellowcube',
                ],

    "css": [],

    "data": ['security/res.groups.csv',
             'security/ir.model.access.csv',
             'security/rules.xml',

             'views/connect_transport_api_view.xml',
             'views/connect_transport_api_log_view.xml',
             'views/stock_connect_file_view.xml',
             ],

    "demo": ['demo/res.partner.csv',
             'demo/res.users.csv',
             'demo/stock_connect.xml',
             'demo/stock_warehouse.xml',
             'demo/connect_transport_api.xml',
             ],

    "test": [],

    "installable": True,

    # We don't want this module to be automatically installed when all its dependencies are loaded,
    # but we want us to install it under our control.
    "auto_install": False,
}

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
