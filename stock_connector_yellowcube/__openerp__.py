# -*- coding: utf-8 -*-
##############################################################################
#
#    Copyright (c) 2016 brain-tec AG (http://www.braintec-group.com)
#    All Right Reserved
#
#    See LICENSE file for full licensing details.
##############################################################################
{
    'name': "Warehouse Connector for Yellowcube",
    'author': "brain-tec AG",
    'license': 'LGPL-3',
    'version': '9.0.1.0.0',
    'summary': "",
    'category': 'Inventory',
    'website': 'http://www.braintec-group.com',
    'images': [
    ],
    'depends': [
        'sale_stock',
        'product',
        'delivery',
        'stock_connector',
    ],
    'data': [
        # views
        'views/res_partner_ext.xml',
        'views/stock_connector_backend_ext.xml',
        'views/stock_connector_yellowcube.xml',
        'views/stock_location_ext.xml',
        'views/stock_picking_return_type_ext.xml',
        # data
        'data/stock.picking.return_type.csv',
    ],
    'qweb': [
    ],
    'test': [
    ],
    'js': [
    ],
    'external_dependencies': {
    },
    'installable': True,
    'application': False,
    'auto_install': False,
}
