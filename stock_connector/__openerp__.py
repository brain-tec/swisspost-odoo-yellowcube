# -*- coding: utf-8 -*-
##############################################################################
#
#    Copyright (c) 2016 brain-tec AG (http://www.braintec-group.com)
#    All Right Reserved
#
#    See LICENSE file for full licensing details.
##############################################################################
{
    'name': "Warehouse Connector",
    'author': "brain-tec AG",
    'license': 'LGPL-3',
    'version': '9.0.1.0.0',
    'summary': "",
    'category': 'Inventory',
    'website': 'http://www.braintec-group.com',
    'images': [
    ],
    'depends': [
        'connector',
        'stock',
        'product',
    ],
    'data': [
        # Views
        'views/product_uom_ext.xml',
        'views/stock_connector_binding.xml',
        'views/stock_connector_backend.xml',  # depends _binding
        'views/stock_connector_event.xml',
        'views/stock_connector_file.xml',
        'views/stock_connector_transport.xml',
        'views/stock_connector.xml',
        'views/stock_picking_ext.xml',
        'views/stock_picking_return_type.xml',
        'views/stock_return_picking.xml',
        'views/menu.xml',
        # Security
        'security/ir.model.access.csv',
        # Data
        'data/product.uom.csv',
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
