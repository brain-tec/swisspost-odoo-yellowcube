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
    'name': 'bt_payment_difference',
    'version': '1.3',
    'category': 'Generic Modules',
    'description': """
    Custom modul for brain-tec customers
    Problem with discount solved
    Problem with payment terms solved
    Bugfix: changed in account_voucher_extended field payment_difference_id required=False because of an error message when adding in bank statement by wysi1
    
    version 1.2
    revised whole module
    added ability to substract credits
    
    version 1.3
    bugfixes
    code review
    """,
    'author': 'brain-tec',
    'website': 'http://www.brain-tec.ch',
    'depends': ['base','account','account_payment','bt_helper'],
    'init_xml': [],
    'update_xml': [
        'security/ir.model.access.csv',
        'view/view.xml',
    ],
    'demo_xml': [],
    'installable': True,
    'active': False,
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
