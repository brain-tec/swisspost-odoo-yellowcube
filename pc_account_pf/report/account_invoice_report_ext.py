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

import os.path
from openerp.addons.pc_connect_master.utilities.reports import \
    delete_report_from_db
from openerp.addons.pc_account.report.account_invoice_report_ext import \
    account_invoice_report_ext
from openerp.addons.report_webkit import report_sxw_ext
from openerp.tools.translate import _


class account_invoice_report_ext(account_invoice_report_ext):
    def __init__(self, cr, uid, name, context):
        super(account_invoice_report_ext, self).__init__(cr, uid, name, context=context)
        self.localcontext.update({
            # Nothing new for the moment.
        })


mako_path = os.path.abspath(os.path.join(os.path.dirname(__file__), 'account_invoice.mako'))
delete_report_from_db('pc_invoice_report_pf')
report_sxw_ext.report_sxw_ext('report.pc_invoice_report_pf',
                              'account.invoice',
                              mako_path,
                              parser=account_invoice_report_ext)

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
