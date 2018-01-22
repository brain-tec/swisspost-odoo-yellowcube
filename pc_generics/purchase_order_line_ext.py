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

from openerp.osv import osv, fields, orm
from openerp.tools.translate import _


class purchase_order_line_ext(osv.Model):
    _inherit = 'purchase.order.line'

    def get_total_amount_including_taxes(self, cr, uid, ids, context=None):
        """ Returns the total amount of the line, including taxes.
            This mainly depends on the tax which is used by the line
            (if it's inclusive or not). If a line does not have taxes, then
            they are not considered. Will only work well if there is just
            one tax on the line.
        """
        if context is None:
            context = {}
        if type(ids) is not list:
            ids = [ids]

        line = self.browse(cr, uid, ids[0], context=context)
        if len(line.taxes_id) != 1:
            raise orm.except_orm(
                _("Bad number of taxes."),
                _("Bad number of taxes in purchase.order.line with ID={0}: "
                  "{1} were found while 1 was expected.").\
                    format(line.id, len(line.taxes_id)))

        tax = len(line.taxes_id) and line.taxes_id[0]

        # We compute the amount assuming that we don't have a tax, or we have
        # it but it is already included in the price,
        total_amount_including_taxes = line.product_qty * line.price_unit

        # If the tax is not inclusive, then we must add the tax to the
        # price without taxes.
        if tax and not tax.price_include:
            total_amount_including_taxes *= (1.0 + tax.amount)

        return total_amount_including_taxes

    def get_amount_corresponding_to_taxes(self, cr, uid, ids, context=None):
        """ Returns the amount of the line corresponding to taxes.
            This depends on the price of the product and on the type of
            taxes (if they are inclusive or not). Will only work well if
            there is just one tax on the line.
        """
        if context is None:
            context = {}
        if type(ids) is not list:
            ids = [ids]

        line = self.browse(cr, uid, ids[0], context=context)
        if len(line.taxes_id) != 1:
            raise orm.except_orm(
                _("Bad number of taxes."),
                _("Bad number of taxes in purchase.order.line with ID={0}: "
                  "{1} were found while 1 was expected.").\
                    format(line.id, len(line.taxes_id)))

        tax = len(line.taxes_id) and line.taxes_id[0]

        amount_corresponding_to_taxes = 0
        if tax:
            amount_corresponding_to_taxes = line.product_qty * line.price_unit * tax.amount
            if tax.price_include:
                amount_corresponding_to_taxes /= (1 + tax.amount)

        return amount_corresponding_to_taxes

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
