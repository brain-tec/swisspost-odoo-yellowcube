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
    "name": "one2many_filter",
    "version": "1.0",
    "author": "brain-tec AG",
    "category": "Dynamic Filter",
    "website": "http://www.brain-tec.ch",
    "description": """
        """,
    'depends': ['base', 'sale', 'sale_stock', 'product', 'bt_helper', 'account'],
    'init_xml': [
    ],
    'data': [
             'view/sale_order_ext_view.xml',
             ],
    'demo_xml': [],
    "js": [],
    'test': [],
    'installable': True,
    'active': False,

}

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
