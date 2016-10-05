# -*- coding: utf-8 -*-
##############################################################################
#
#    Copyright (c) 2016 brain-tec AG (http://www.braintec-group.com)
#    All Right Reserved
#
#    See LICENSE file for full licensing details.
##############################################################################
{
    'name': "Warehouse Connector Transport for Secure-FTP",
    'author': "brain-tec AG",
    'license': 'LGPL-3',
    'version': '9.0.1.0.0',
    'summary': "",
    'category': 'Inventory',
    'website': 'http://www.braintec-group.com',
    'images': [
    ],
    'depends': [
        'stock_connector',
    ],
    'data': [
        'views/stock_connector_transport_ext.xml',
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
