# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>).
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
    'name': 'bt_account',
    'version': '1.4',
    'category': 'Generic Modules',
    'description': """
    Custom modul for brain-tec customers
    Problem with discount solved
    Problem with payment terms solved
    v 1.1
    Replace account_statement_view to show also partial reconciled move lines in bank statement
    v 1.2
    Added report and wizard (account_general_ledger)
    v 1.3
    Added balance to tree view of account.move.line
    IMPORTANT: If you want to add "Balance" to "Buchungsjournale", you have to add this field to "Konfiguration/Finanzen/Buchungsjournale/Journalansicht" for "Journal View"
    v 1.4
    Added account_invoice_worklow.xml (button_reset_taxes() will now be executed on validating an invoice)
    """,
    'author': 'brain-tec',
    'website': 'http://www.brain-tec.ch',
    'depends': ['base','product','sale','account','account_payment','account_voucher'],
    'init_xml': [],
    'update_xml': [
         'data/add_ch5_currency.xml',

         'security/ir_rule.xml',
         'view/account_statement_view_extended.xml',
         'view/account_voucher_view_extended.xml',
         'view/account_view_extended.xml',
         'wizard/account_report_general_ledger_view.xml',
         'security/ir.model.access.csv',

        'view/account_payment_view_extended.xml',
    ],
    'demo_xml': [],
    'installable': True,
    'active': False,
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
