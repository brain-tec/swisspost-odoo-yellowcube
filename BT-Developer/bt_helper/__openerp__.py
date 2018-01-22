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
    "name": "bt_helper",
    "version": "1.0",
    "author": "brain-tec",
    "description": """brain-tec helper module.

* Module Updater Wizard to update installed modules and/or its languages.
* Add 'Execute Job' button to each cron job.
* Provides some usable date/time functions.
* Provides some extensions in users search by group.
* Provides some extensions in group to see the xml_id
* Hides the OpenERP announcement bar
<br>Requires:<br/>
 pip install rstr
 apt-get install python-pexpect

    """,
    "category": "base",
    "website": "http://www.brain-tec.ch",
    "depends": ['mail', 'base', 'fetchmail'],
    "init_xml": [],

    "demo_xml": [],

    "update_xml": [
        "view/base_view.xml",
        "data/mail_data.xml",
    ],
    "update_xml" : [
        'security/ir.model.access.csv',]
        ,
    "data": [
        "data/cron.xml",
        'data/fields_not_duplicate.xml',
        "view/view.xml",
        "view/ir_cron_ext_view.xml",
        "view/res_groups_ext_view.xml",
        "view/ir_ui_menu_ext_view.xml",
        "view/ir_ext.xml",
        'view/fields_view.xml',
        "view/name_generator_view.xml",
        'view/menu.xml',
        'view/information_ir_ui_view.xml',
        'view/information_ir_ui_menu.xml',
        'view/information_ir_model_data.xml',
        'view/duplicate_model_view.xml',
        'view/workflow_update_view.xml',
        "wizard/module_updater_view.xml",
        "wizard/downloadable_binary_view.xml",
        "wizard/database_information.xml",
        "wizard/change_loggers.xml",
        "wizard/export_all_language_files.xml",

    ],
    'qweb': [
        "static/src/xml/base.xml",
    ],

    "active": False,
    "installable": True,
}

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
