# b-*- encoding: utf-8 -*-
##############################################################################
#
#    Copyright (c) 2017 brain-tec AG (http://www.braintec-group.com)
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
    "name": "pc_followup_pf",
    "version": "1.0",
    'category': 'PC Followup PF',
    'description': """
                   Extends pc_followup with new reports & routes per
                   follow-up level, and a new way of generating dunning 
                   invoices than can actually be paid.
                   """,
    'author': 'brain-tec AG',
    "website": "http://www.braintec-group.com",
    'depends': [
        'account_cancel',
        'account_voucher',
        'account',

        'pc_connect_master',
        'pc_followup',
        'pc_account_pf',
        'pc_account_invoice_automation',
        'pc_log_data',
    ],

    'init_xml': [
    ],
    'data': [
        'data/email_routing_template.xml',

        'view/follow_level_ext_view.xml',

        'report/menu.xml',
    ],
    'css': [
    ],
    'demo_xml': [],
    'installable': True,

    # We don't want this module to be automatically installed when all its
    # dependencies are loaded, but we want us to install it under our control.
    "auto_install": False,
}

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
