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
    'name': 'PostCommerce AP1/Graphical User Interface-based Reports (BT-Discount Extension)',
    'version': '1.0',
    'description': 'Extends the Graphical User Interface-based Reports under the menu E-Commerce, taking into account BT-Discount extensions',
    'author': 'Brain-tec',
    'category': '',

    'depends': ['pc_report_gui',
                'stage_discount',
                ],

    'data': [],

    'installable': True,

    # We DO want this module to be automatically installed when all its dependencies are loaded.
    'active': True,  # This is only for compatibility, since 'active' is now 'auto_install'.
    'auto_install': True,
}

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
