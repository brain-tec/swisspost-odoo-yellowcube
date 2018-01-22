# b-*- encoding: utf-8 -*-
##############################################################################
#
#    Copyright (c) 2016 brain-tec AG (http://www.braintec-group.com)
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
    "name": "PostCommerce AP1/Followup",
    "version": "1.0",
    'category': 'PC Followup',
    'description': """ Adding dunning_block boolean value
                        to the follow up.

                        If the dunning_block value is set=> We do not send
                        any e-mail from the system.

                        Otherwise it works as expected.
                        Adapted for account_followup wizard and bt_followup.
                        """,
    'author': 'brain-tec AG',
    "website": "http://www.braintec-group.com",
    'depends': ['pc_connect_master',
                'account',
                'partner_firstname',
                'base',
                'sale',
                'pc_generics',
                'pc_config',
                'pc_docout',
                'pc_log_data',
                'email_template',
                'bt_followup',
                ],

    'init_xml': [
    ],
    'data': [
        'view/res_partner_ext_view.xml',
        'view/follow_level_ext_view.xml',
        'view/followup_view.xml',
        'view/followup_config_view.xml',
        'view/clocking_config_view.xml',
        'view/account_invoice_ext_view.xml',
        'view/docout_config_view.xml',

        'data/email_template_followup_handled.xml',
        'data/invoice_followup_data.xml',
        'data/clocking_followup.xml',
        'data/docout_email_templates.xml',
        'data/schedulers.xml',
        'data/punchcard_followup.xml',

        'security/ir.model.access.csv',

        'view/menu.xml',
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
