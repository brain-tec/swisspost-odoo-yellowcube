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

from openerp.osv import osv, fields
from openerp.tools.translate import _
from utilities.db import create_db_index


class account_invoice_line(osv.Model):
    _inherit = 'account.invoice.line'

    def init(self, cr):
        # Do we have the column is_discount?
        cr.execute("SELECT column_name FROM information_schema.columns WHERE table_name='account_invoice_line' AND column_name='is_discount'")
        if cr.fetchone():
            create_db_index(cr, 'account_invoice_line_is_discount_invoice_id_sequence_id_index', 'account_invoice_line', 'is_discount, invoice_id, sequence, id')
            create_db_index(cr, 'account_invoice_line_is_discount_index', 'account_invoice_line', 'is_discount')

    def _update_average_price_because_of_invoice(self, cr, uid, ids, context=None):
        """ Updates the standard_price of the product which is contained on this
            invoice line, provided that its cost method requires it, and that
            the invoice which contains the line is an incoming invoice.

            This code is inspired by _update_average_price() from addons/stock/stock.py.
        """
        if context is None:
            context = {}
        if type(ids) is not list:
            ids = [ids]

        product_uom_obj = self.pool.get('product.uom')
        res_currency_obj = self.pool.get('res.currency')
        product_product_obj = self.pool.get('product.product')
        product_price_type_obj = self.pool.get('product.price.type')
        res_user_obj = self.pool.get('res.users')
        standard_price_history_obj = self.pool.get('pc_connect_master.product_standard_price_history')

        company_currency = res_user_obj.browse(cr, uid, uid, context=context).company_id.currency_id.id

        for invoice_line in self.browse(cr, uid, ids, context=context):
            invoice = invoice_line.invoice_id
            product = invoice_line.product_id

            if invoice.type == 'in_invoice' and product.cost_method == 'average_invoice':

                product_qty = invoice_line.quantity
                product_uom = invoice_line.uos_id.id
                product_price = invoice_line.price_unit
                product_currency = invoice_line.invoice_id.currency_id.id
                product_qty_available = product.qty_available

                qty = product_uom_obj._compute_qty(cr, uid, product_uom, product_qty, product.uom_id.id)
                if qty > 0:
                    new_price = res_currency_obj.compute(cr, uid, product_currency, company_currency, product_price, round=False)
                    new_price = product_uom_obj._compute_price(cr, uid, product_uom, new_price, product.uom_id.id)
                    if product_qty_available <= 0:
                        new_std_price = new_price
                    else:
                        price_type_id = product_price_type_obj.search(cr, uid, [('field', '=', 'standard_price')], context=context)[0]
                        price_type_currency_id = product_price_type_obj.browse(cr, uid, price_type_id,
                                                                               context=context).currency_id.id
                        amount_unit = res_currency_obj.compute(cr, uid, price_type_currency_id,
                                                               product_currency,
                                                               product.standard_price, round=False,
                                                               context=context)

                        history_standard_price_count = standard_price_history_obj.search(cr, uid, [('product_id', '=', product.id),
                                                                                                   ], limit=1, count=True, context=context)
                        if history_standard_price_count == 0:
                            new_std_price = new_price
                        else:
                            new_std_price = (amount_unit * (product.qty_available - qty) + new_price * qty) / product_qty_available

                    product_product_obj.write(cr, uid, [product.id], {'standard_price': new_std_price})

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
