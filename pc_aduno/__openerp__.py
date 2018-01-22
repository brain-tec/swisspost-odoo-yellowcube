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
    'name': 'pc_aduno',
    'version': '1.0',
    'category': 'PC Aduno',
    'description': '''Module responsible of Aduno reconciliations.''',
    'author': 'brain-tec AG',
    'website': 'http://www.braintec-group.com',
    'depends': ['l10n_ch_payment_slip', 
                'bt_payment_difference',
                'account_analytic_plans',
                'account_statement_ext',
                'account_statement_base_completion',
                'account_statement_transactionid_completion',
                ],

    'init_xml': [],
    'data': ["wizard/aduno_import_view.xml",
             "views/bank_statement_profile_view.xml",
             "views/bank_statement_view.xml"
    ],
    'css': [
    ],
    'demo_xml': [],
    'installable': True,

    # We don't want this module to be automatically installed when all its dependencies are loaded,
    # but we want us to install it under our control.
    "active": False,  # This is only for compatibility, since 'active' is now 'auto_install'.
    "auto_install": False,
}

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
