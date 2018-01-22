# b-*- encoding: utf-8 -*-
##############################################################################
#
#    Copyright (c) 2014 brain-tec AG (http://www.braintec-group.com)
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
    "name": "PostCommerce AP1/Audittrail",

    "version": "1.0",

    "description": """
    """,

    "author": "Brain-tec",

    "category": "Connector",

    'depends': ['base',
                'product',
                'stock',
                'sale',
                'account',
                'audittrail',
                'pc_connect_master',
                ],

    "data": ["security/ir.model.access.csv",

             "data/audittrail_rule_account_invoice.xml",
             "data/audittrail_rule_ir_cron.xml",
             "data/audittrail_rule_product_product.xml",
             # res_partner rule fails on test mode
#              "data/audittrail_rule_res_partner.xml",
             "data/audittrail_rule_sale_order.xml",
             "data/audittrail_rule_stock_picking.xml",
             "data/audittrail_rule_stock_picking_in.xml",
             "data/audittrail_rule_stock_picking_out.xml",

             "views/audittrail_log_view.xml",
             "views/product_product_ext_view.xml",
             "views/sale_order_ext_view.xml",
             "views/res_partner_ext_view.xml",
             "views/stock_picking_out_ext_view.xml",
             "views/account_invoice_ext_view.xml",

             # DO NOT CHANGE THE ORDER
             "views/menu.xml",
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
