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
    "name": "PostCommerce AP1/Post Barcode Labels",
    "version": "1.0",
    "description": "Extends the module which gets the barcode labels to account for Post's requirements.",
    "author": "Brain-tec",
    "category": "",

    'depends': ['delivery_carrier_label_postlogistics',
                'document',
                'pc_connect_master',
                'pc_sale_order_automation',
                'pc_generics',
                ],

    "data": ['views/configuration_data_view.xml',

             'security/ir.model.access.csv',

             'reports/menu.xml',
             ],

    "demo": [
             ],

    "test": [
             ],

    "installable": True,

    # We don't want this module to be automatically installed when all its dependencies are loaded,
    # but we want us to install it under our control.
    "active": False,  # This is only for compatibility, since 'active' is now 'auto_install'.
    "auto_install": False,
}

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
