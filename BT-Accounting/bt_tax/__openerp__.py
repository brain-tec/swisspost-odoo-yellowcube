# -*- encoding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution	
#    Copyright (C) 2004-2009 Tiny SPRL (<http://tiny.be>). All Rights Reserved
#    $Id$
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################


{
    'name': 'bt_tax',
    'version': '1.1',
    'category': 'Generic Modules',
    'description': """
	Custom Module tax for customer of brain-tec
    
    version 1.1
    revised whole module
    """,
    'author': 'brain-tec',
    'website': 'http://www.brain-tec.ch',
    'depends': ['sale', 'account', 'bt_account'],
    'init_xml': [],
    'update_xml': [
        'view.xml',
        'wizard/account_vat_view.xml',
    ],
    'demo_xml': [],
    'installable': True,
    'active': True,
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
