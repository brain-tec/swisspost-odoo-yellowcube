# b-*- encoding: utf-8 -*-
##############################################################################
#
#    Copyright (c) 2017 brain-tec AG (http://www.braintec-group.com)
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

from openerp.osv import osv, fields
from openerp.tools.translate import _


class configuration_data_ext(osv.Model):
    _inherit = 'configuration.data'

    _columns = {
        'aia_report_account_invoice': fields.many2one(
            'ir.actions.report.xml', "Account.Invoice Automation Report",
            domain=[('model', '=', 'account.invoice')]),

        'aia_route_email_template_id': fields.many2one(
            'email.template', 'Email Template for the Email Routing',
            domain=[('model', '=', 'account.invoice')],
            help="The email template which renders the email to send to the "
                 "partner of the invoice if it has set the routing 'email'."),
    }

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
