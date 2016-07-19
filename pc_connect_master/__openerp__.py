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
    "name": "SwissPost YellowCube Odoo / Connect Master",

    "version": "1.0",

    "description": """
    Provides the skeleton of features and views the other modules can build on.

    Depends on the following modules from OCA:
    - connector (from repository connector: https://github.com/OCA/connector)
    - sale_exceptions (from repository sale-workflow: https://github.com/OCA/sale-workflow)
    - partner_firstname (from repository partner-contact: https://github.com/OCA/partner-contact)
    - sale_payment_method (from reposutory e-commerce: https://github.com/OCA/e-commerce)

    Python dependencies:
    - pip install XlsxWriter
    """,

    "author": "Brain-tec",

    "category": "",

    'depends': ['base',
                'product',
                'product_expiry',
                'sale',
                'sale_stock',
                'account',
                'stock',
                'delivery',
                'purchase',
                'sale_payment_method',  # For the payment.method.
                'sale_exceptions',
                'product_expiry',
                'document',
                'connector',
                'partner_firstname',
                'pc_issue',
                'pc_config',
                'pc_connect_transport',
                'board',  # For the reports of E-Commerce.
                'mail',
                ],

    "data": ['data/clocking_support.xml',
             'data/decimal_precision_ext.xml',
             'data/default_configuration.xml',
             'data/email_template.xml',
             'data/init_invoice_report.xml',
             'data/invoice_to_partner_templates.xml',
             'data/ir_filters.xml',
             'data/only_mister_and_madam_titles.xml',
             'data/product_uom.xml',
             'data/res_country_data_ext.xml',
             'data/schedulers.xml',

             'views/account_invoice_ext_view.xml',
             'views/configuration_data.xml',
             'views/delivery_carrier_ext_view.xml',
             'views/gift_text_type_view.xml',
             'views/ir_cron_ext_view.xml',
             'views/payment_method_ext_view.xml',
             'views/product_expiry_view_ext.xml',
             'views/product_product_ext_view.xml',
             'views/product_uom_ext.xml',
             'views/queue_job_view.xml',
             'views/res_company_ext.xml',
             'views/res_partner_bank_ext.xml',
             'views/res_partner_ext.xml',
             'views/sale_order_ext_view.xml',
             'views/stock_move_list_view.xml',
             'views/stock_picking_out_ext_view.xml',
             'views/stock_production_lot_ext.xml',
             'views/stock_view_ext.xml',

             'wizard/wizard_knowledge_export_view.xml',
             'wizard/wizard_popup.xml',
             'wizard/wizard_check_sale_order.xml',
             'wizard/wizard_check_res_partner.xml',

             'security/security.xml',
             'security/ir.model.access.csv',

             'wizard/menu.xml',
             'views/menu.xml',
             ],

    "demo": ['demo/configuration_data.xml',
             ],

    "installable": True,

    # We don't want this module to be automatically installed when all its dependencies are loaded,
    # but we want us to install it under our control.
    "auto_install": False,
}

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
