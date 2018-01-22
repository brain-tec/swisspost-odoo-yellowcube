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
    "name": "PostCommerce AP1/Connect Master",
    "version": "1.0",
    "description": """
    Provides the skeleton of features and views the other modules can build on.
        Git dependencies:
            * connector: git@github.com:brain-tec/connector.git
            * partner_firstname: git@github.com:brain-tec/partner-contact.git
            * sale_payment_method: git@github.com:brain-tec/e-commerce.git
            * sale_exceptions: git@github.com:brain-tec/sale-workflow.git
        Python dependencies:
            * pip install XlsxWriter
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
                'pc_log_data',
                'bt_tax',  # For the reports of E-Commerce.
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
             'data/log_data_filter.xml',
             'data/only_mister_and_madam_titles.xml',
             'data/product_uom.xml',
             'data/res_country_data_ext.xml',
             'data/schedulers.xml',
             'data/standard_report.xml',
             'data/account_invoice_workflow_ext.xml',

             'views/account_invoice_ext_view.xml',
             'views/configuration_data.xml',
             'views/delivery_carrier_ext_view.xml',
             'views/delivery_carrier_product_category_view.xml',
             'views/delivery_carrier_product_template_view.xml',
             'views/delivery_carrier_yc_option_view.xml',
             'views/export_account_invoice.xml',
             'views/export_sale_order.xml',
             'views/export_stock_picking.xml',
             'views/gift_card_view.xml',
             'views/gift_text_type_view.xml',
             'views/ir_attachment_ext_view.xml',
             'views/ir_cron_ext_view.xml',
             'views/payment_method_ext_view.xml',
             'views/procurement_order_ext_view.xml',
             'views/product_category_ext_view.xml',
             'views/product_expiry_view_ext.xml',
             'views/product_product_ext_view.xml',
             'views/product_template_ext_view.xml',
             'views/product_standard_price_history_view.xml',
             'views/product_supplierinfo_ext_view.xml',
             'views/product_uom_ext.xml',
             'views/purchase_order_ext_view.xml',
             'views/queue_job_view.xml',
             'views/res_company_ext.xml',
             'views/res_partner_bank_ext.xml',
             'views/res_partner_ext.xml',
             'views/sale_order_ext_view.xml',
             'views/standard_report_view.xml',
             'views/standard_view_report_view.xml',
             'views/stock_move_list_view.xml',
             'views/stock_picking_out_ext_view.xml',
             'views/stock_production_lot_ext.xml',
             'views/stock_type_view.xml',
             'views/stock_view_ext.xml',

             'wizard/wizard_knowledge_export_view.xml',
             'wizard/wizard_popup.xml',
             'wizard/wizard_check_sale_order.xml',
             'wizard/wizard_check_res_partner.xml',
             'wizard/wizard_invoice_report_view.xml',
             'wizard/wizard_inventory_report_view.xml',
             'wizard/wizard_inventory_additional_report_view.xml',

             'security/security.xml',
             'security/ir.model.access.csv',

             'views/menu.xml',
             'wizard/menu.xml',

             'data/standard_view_report.xml',
             ],

    "demo": ['demo/configuration_data.xml',
             'demo/sale_order_exception.xml',
             'demo/sale.xml',

             # Keep the order of the following three files as is.
             'demo/locations.xml',
             'demo/warehouses.xml',
             'demo/shops.xml',
             ],

    "test": [],

    "installable": True,

    # We don't want this module to be automatically installed when all its dependencies are loaded,
    # but we want us to install it under our control.
    "auto_install": False,
}

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
