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
    'name': 'PostCommerce AP1/Report generics',
    'version': '1.0',
    'category': 'Postcommerce Generics',
    'description': """

    Git dependencies:
    *report_sxw_ext : git@github.com:brain-tec/BT-Webkit.git
                   """,
    'author': 'brain-tec AG',
    'website': 'http://www.braintec-group.com',
    'depends': ['base',
                'account',
                'product',
                'report_webkit',
                'stock',
                'sale',
                'pc_connect_master',
                'pc_config',
                ],

    'init_xml': [],
    'data': [
        'data/report_header_footer.xml',
        'data/report_header_footer_pf.xml',
        'data/esr_positioning_config.xml',

        'views/reports_config_view.xml',
    ],
    'demo_xml': [],
    'installable': True,

    # We don't want this module to be automatically installed when all its dependencies are loaded,
    # but we want us to install it under our control.
    "auto_install": False,
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
