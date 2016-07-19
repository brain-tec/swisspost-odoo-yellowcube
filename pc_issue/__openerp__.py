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
    "name": "SwissPost YellowCube Odoo / Issue tracking",

    "version": "1.0",

    "description": """
    PC module for issue tracking and management of the PostCommerce customization.

    Depends on the following modules from OCA:
    - connector (from repository connector: https://github.com/OCA/connector)
    - sale_exceptions (from repository sale-workflow: https://github.com/OCA/sale-workflow)
    """,

    "author": "Brain-tec",

    "category": "Connector",

    'depends': ['base',
                'project',
                'sale',
                'stock',
                'project_issue',
                'connector',
                'sale_exceptions',
                ],

    "data": ["views/project_issue_ext.xml",
             "views/project_task_ext.xml",
             "views/project_project_ext.xml",
             "views/project_category_ext.xml",
             "views/sale_order.xml",
             "wizard/open_issue.xml",
             "views/queue_job_view.xml",

             "data/issue_tracking.xml",
             "security/ir_rule.xml",
             "security/ir.model.access.csv",

             ],

    "demo": ['demo/test_sale_exception.xml',
             ],

    "installable": True,

    # We don't want this module to be automatically installed when all its dependencies are loaded,
    # but we want us to install it under our control.
    "auto_install": False,
}

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
