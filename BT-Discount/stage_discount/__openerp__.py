# b-*- encoding: utf-8 -*-
##############################################################################
#
#    Copyright (c) 2014 brain-tec AG (http://www.brain-tec.ch)
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
    "name": "stage_discount",
    "version": "1.0",
    "author": "brain-tec AG",
    "category": "Stage Discount",
    "website": "http://www.brain-tec.ch",
    "description": """
                    Allow us to generate different discount in invoice lines.


                """,
    'depends': ['base_setup',
                'base',
                'sale',
                'sale_stock',
                'product',
                'bt_helper',
                'bt_account',
                'account',
                'one2many_filter',
                ],
    'init_xml': [
    ],
    'data': ['data/sequence.xml',
             'view/discount_line_view.xml',
             'view/discount_view.xml',
             'view/menu.xml',
             'view/account_invoice_view.xml',
             'view/account_invoice_line_ext_view.xml',
             'view/res_partner_ext_view.xml',
             'view/sale_order_line_ext_view.xml',
             'view/sale_order_ext_view.xml',
             'security/ir.model.access.csv',
             ],
    'demo_xml': [],
    'demo': [
              'data/account.account.type.csv',
              'data/account.account.csv',
              'data/account.tax.code.csv',
              'data/account.tax.csv'
             ],
    "js": [],
    'installable': True,
    'active': False,
    'test': ['test/fixed_discount_ink.yml',
             'test/fixed_discount_ex.yml',
             'test/fixed_discount_mix.yml',
             'test/fixed_percentage_discount_2ink.yml',
             'test/fixed_percentage_discount_2ex.yml',
             'test/fixed_percentage_discount_2mix.yml',
              'test/percentage_discount_ex.yml',
              'test/percentage_discount_ink.yml',
              'test/percentage_discount_mix.yml',
              'test/percentage_discount_2ex.yml',
              'test/percentage_discount_2ink.yml',
              'test/percentage_discount_2mix.yml',
              'test/subtotal_discount.yml',
              'test/percentage_subtotal_discount.yml',
              'test/fixed_percentage_discount.yml',
        ]

}

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
