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
    "name": "PostCommerce AP1/Doc-out for Remote Printing",
    "version": "1.0",
    "description": '''Provides the functionality of remote printing, by sending documents to a
                      remote folder or email address, where documents can be printed from there.''',
    "author": "brain-tec AG",
    "category": "",

    'depends': [
        'delivery',
        'document',
        'pc_connect_transport',
        'pc_connect_master',
        'pc_config',
        'pc_issue',
        'l10n_ch_payment_slip',  # Doc-out depends on the account being BVR.
    ],

    "data": ['data/issue_tracking.xml',

             'view/ir_attachment_ext_view.xml',
             'view/configuration_view.xml',
             ],

    "demo": [
        'demo/res_partner_bank.xml',
    ],

    "test": [],

    "installable": True,

    # We don't want this module to be automatically installed when all its
    # dependencies are loaded, but we want us to install it under our control.
    "auto_install": False,
}

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
