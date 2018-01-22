# b-*- encoding: utf-8 -*-
##############################################################################
#
#    Copyright (c) 2015 brain-tec AG (http://www.braintec-group.com)
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
    "name": "PostCommerce AP1/Connect Webshop",
    "version": "1.0",
    "description": "Provides the skeleton of features and views the other modules related to a webshop can build on.",
    "author": "Brain-tec",
    "category": "",

    'depends': ['base',
                'product',
                'product_images',
                'product_links',
                'pc_connect_master',
                'pc_issue',
                ],

    "data": ['wizard/product_image_massive_setting_wizard.xml',
             'wizard/product_import_wizard.xml',

             'data/checkpoint_management.xml',
             'data/schedulers.xml',

             'views/checkpoint_management_view.xml',
             'views/product_ext_view.xml',
             'views/product_alternative_view.xml',
             'views/product_manual_view.xml',
             'views/product_images_ext.xml',
             'views/res_partner_ext.xml',
             'views/payment_method_ext_view.xml',
             'views/product_images_view.xml',

             'security/ir.model.access.csv',

             'views/menu.xml',
             ],

    "demo": [],

    "test": [],

    "installable": True,

    # We don't want this module to be automatically installed when all its dependencies are loaded,
    # but we want us to install it under our control.
    "auto_install": False,
}

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
