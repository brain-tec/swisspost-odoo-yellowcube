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

from openerp.osv import fields, osv
from openerp.tools.translate import _


class account_voucher_line_ext(osv.osv):
    _inherit = 'account.voucher.line'

    def get_amount(self, cr, uid, ids, context=None):
        """ Given a list of ids for voucher lines, it returns the amount
            paid by them, taking into account if the line was for credit
            or debit.
        """
        if not isinstance(ids, list):
            ids = [ids]
        if context is None:
            context = {}

        total_amount_paid = 0.0

        for voucher_line in self.browse(cr, uid, ids, context=context):
            if voucher_line.type == 'cr':
                total_amount_paid += voucher_line.amount
            elif voucher_line.type == 'dr':
                total_amount_paid -= voucher_line.amount

        return total_amount_paid

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
