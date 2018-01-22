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


class account_move_line_ext(osv.Model):
    _inherit = 'account.move.line'

    def get_debit_move_line_name(self, cr, uid, ids, context=None):
        """ Gets the mirror debit line from a credit account.move.line.
            This is used in the gift-cards, to get the name of the gift-card
            which originated the payment from the sale.order.
        """
        if context is None:
            context = {}
        if type(ids) is not list:
            ids = [ids]

        move_line_obj = self.pool.get('account.move.line')

        credit_move_line = self.browse(cr, uid, ids[0], context=context)

        debit_move_line_ids = move_line_obj.search(
            cr, uid, [('credit', '=', 0.0),
                      ('move_id', '=', credit_move_line.move_id.id),
                      ('ref', '=', credit_move_line.ref),
                      ], context=context)

        if debit_move_line_ids:
            debit_move_line = move_line_obj.browse(
                cr, uid, debit_move_line_ids[0], context=context)
            name = debit_move_line.name
        else:
            name = ''
        return name

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
