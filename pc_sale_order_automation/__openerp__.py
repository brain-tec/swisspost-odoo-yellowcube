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
    "name": "PostCommerce AP1/Sale Order Automation",

    "version": "1.0",

    "description": """
        Automates a sale.order if its check-box 'Automate sale order process'
        is set when created from a quotation. If that is the case, then
        the sale.order creates a job (from the module 'connector') which,
        in collaboration with a scheduler, moves the sale.order through
        a list of states.
    """,

    "author": "Brain-tec",

    "category": "",

    'depends': ['base',
                'product',
                'sale',
                'sale_stock',
                'account',
                'stock',
                'delivery',
                'sale_payment_method',  # For the payment.method.
                'sale_exceptions',
                'procurement',
                'product_expiry',
                'connector',
                'pc_connect_master',
                'pc_issue',
                'pc_config',
                'pc_docout',
                'pc_log_data',

                # Modules for the reports are added since we require
                # the use of a report on the SOA, otherwise we raise.
                'pc_account',
                'pc_stock',
                ],

    "data": ['data/docout_email_templates.xml',
             'data/sale_order_alarming.xml',
             'data/sale_order_exception.xml',
             'data/sale_stock_workflow_ext.xml',
             'data/sale_workflow_ext.xml',
             'data/schedulers.xml',

             'views/configuration_view.xml',
             'views/delivery_carrier_ext_view.xml',
             'views/docout_config_view.xml',
             'views/packaging_type_view.xml',
             'views/procurement_order_ext_view.xml',
             'views/product_product_ext_view.xml',
             'views/res_partner_bank_ext_view.xml',
             'views/sale_order_ext_view.xml',
             'views/stock_move_ext_view.xml',
             'views/stock_picking_in_ext_view.xml',
             'views/stock_picking_out_ext_view.xml',
             'views/stock_tracking_ext_view.xml',

             'security/ir.model.access.csv',

             'wizard/sale_order_automation_joiner.xml',
             ],

    "demo": [
        'demo/account_payment_term_demo.xml',
        'demo/payment_method_demo.xml',
        'demo/res_partner_demo.xml',
        'demo/sale_order_exception_demo.xml',
        'demo/stock_type_demo.xml',
        'demo/account_fiscal_position_demo.xml',
        'demo/delivery_carrier_demo.xml',
    ],

    "test": [
        'test/quotation_creation_correct.yml',
        'test/quotation_creation_correct_with_line.yml',
        'test/quotation_creation_payment_term_check.yml',
    ],

    "installable": True,

    # We don't want this module to be automatically installed when
    # all its dependencies are loaded, but we want us to install it
    # under our control.
    "auto_install": False,
}

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
