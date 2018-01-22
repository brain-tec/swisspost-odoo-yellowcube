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

import decimal_precision as dp
from osv import fields, osv
from tools.translate import _
from generic import one2many_line_ext


class account_invoice_ext(osv.osv):

    _inherit = "account.invoice"

    _columns = {   
                'invoice_line': one2many_line_ext('account.invoice.line', 'invoice_id', 'Invoice Lines', readonly=True, states={'draft': [('readonly', False)]}),
                }
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
