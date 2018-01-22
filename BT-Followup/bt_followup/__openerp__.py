# b-*- encoding: utf-8 -*-
#
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
#

{
    "name": "BT Invoice Follow-up for 7 series",
    "version": "1.0",
    "category": "Accounting & Finance",
    "description": """

    Provides Followup of overdue payments based on invoices and no on account move lines.

    """,
    "author": "brain-tec AG",
    "website": "http://www.brain-tec.ch",
    "depends":
        ["base",
         "account",
         "mail",
         "report_webkit",
         "document",
         "bt_helper",
         "stock",
         "sale"],
    "data": [
        "security/invoice_followup_security.xml",
        "security/ir.model.access.csv",

        "data/invoice_followup_data.xml",
        "data/email_template_responsible.xml",
        "view/followup_level_view.xml",
        "view/followup_view.xml",
        "view/followup_error_view.xml",
        "view/account_invoice_ext_view.xml",
        "view/res_company_ext_view.xml",
        "view/res_partner_ext_view.xml",
        "view/menu.xml",
        "data/cron.xml",
        "data/header_webkit.xml",
        'data/log_data_filter.xml',
        "data/migrate_dunning_block_fields.xml",
        "data/report.xml",

        "wizard/account_invoice_followup_handle.xml",
        "wizard/customer_invoices_followup_handle.xml",
    ],
    "test": ["test/1_A_1.yml",
             "test/1_A_2.yml",
             "test/1_A_3.yml",
             "test/1_A_4.yml",
             "test/1_A_5.yml",
             "test/1_A_7.yml",
             "test/1_A_7_a.yml",
             "test/1_A_9.yml",
             "test/1_A_10.yml",
             "test/2_A_1.yml",
             "test/2_A_2.yml",
             "test/2_A_3.yml",
             "test/2_A_3_a.yml",
             "test/2_A_4.yml",
             "test/2_A_5.yml",
             "test/2_A_6.yml",
             "test/2_A_8.yml",
             "test/2_A_9.yml",
             "test/2_A_10.yml",
             "test/3_A_1.yml",
             "test/3_A_3.yml",
    ],
    "installable": True,
    "auto_install": False,
}

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
