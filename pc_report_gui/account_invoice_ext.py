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

from openerp.osv import osv, fields
from openerp.tools.translate import _


class account_invoice_ext(osv.Model):
    _inherit = 'account.invoice'

    def _fun_payment_date(self, cr, uid, ids, payment_date, arg, context=None):
        ''' Computes the payment date. This is the most recent date of the payment associated to this invoice,
            that is of its account.move.lines. If there are no payments associated to this invoice, then
            payment_date is set to False.
        '''
        if context is None:
            context = {}
        res = {}

        for invoice in self.browse(cr, uid, ids, context=context):
            res[invoice.id] = False
            for payment in invoice.payment_ids:
                if (res[invoice.id] is False) or (res[invoice.id] < payment.date):
                    res[invoice.id] = payment.date

        return res

    def _fun_discount(self, cr, uid, ids, discount, arg, context=None):
        ''' Computes the total amount corresponding to discounts on the invoice.
        '''
        if context is None:
            context = {}
        res = {}

        for invoice in self.browse(cr, uid, ids, context=context):
            res[invoice.id] = 0.0

            # Sums up the discounts applied to every line.
            for invoice_line in invoice.invoice_line:
                if invoice_line.discount:
                    res[invoice.id] += (invoice_line.price_total - invoice_line.price_total_less_disc)

        return res

    def _sto_payment_date(self, cr, uid, account_move_line_ids, context=None):
        ''' Returns the IDs of the invoices having those moves.
        '''
        if context is None:
            context = {}

        invoice_ids = set()
        for account_move_line in self.pool.get('account.move.line').browse(cr, uid, account_move_line_ids, context=context):
            if account_move_line.invoice:
                invoice_ids.add(account_move_line.invoice.id)
        return list(invoice_ids)

    def _fun_partner_main_category_id(self, cr, uid, ids, field, arg, context=None):
        """ Stores the main tag of the invoice's partner into the invoice's
            main tag, just in case we change it when the invoices has already
            been created.
        """
        if context is None:
            context = {}
        res = {}
        for invoice in self.browse(cr, uid, ids, context=context):
            res[invoice.id] = invoice.partner_id.main_category_id.id
        return res

    def _sto_partner_main_category_id_partner(self, cr, uid, res_partner_ids, context=None):
        """ Returns the invoices which have these partners as their customers.
        """
        if context is None:
            context = {}
        return self.pool.get('account.invoice').search(cr, uid, [
            ('partner_id', 'in', res_partner_ids),
        ], context=context)

    def _sto_partner_main_category_id_invoice(self, cr, uid, ids, context=None):
        """ Returns the invoices which have as partners the same partner
            than the invoices received.
        """
        if context is None:
            context = {}
        partner_read = self.read(cr, uid, ids, ['partner_id'], context=context)
        partner_ids = [partner['partner_id'][0] for partner in partner_read]
        return self.search(cr, uid, [
            ('partner_id', 'in', partner_ids),
        ], context=context)

    _columns = {
        'payment_date': fields.function(_fun_payment_date, string='Payment Date', type='date', readonly=True,
                                        help='Stores the most recent date of the payment associated to this invoice, that is of its account.move.lines.',
                                        store={'account.move.line': (_sto_payment_date, [], 10)}),

        'partner_main_category_id': fields.function(
            _fun_partner_main_category_id, relation='res.partner.category',
            string='Main Category of the Partner', type='many2one',
            readonly=True, help='Stores the main tag of the partner.',
            store={
                'res.partner':
                    (_sto_partner_main_category_id_partner, ['main_category_id'], 10),
                'account.invoice':
                    (_sto_partner_main_category_id_invoice, ['partner_id'], 20),
            }),

        'discount': fields.function(_fun_discount, string='Total Discount', type='float', readonly=True,
                                    help='Computes the total amount discounted on the invoice.',
                                    store=False),

        # Functional fields used to allow a direct search from the search-box.
        'date_invoice_from': fields.function(lambda *a, **k: {}, method=True, type='date', string='Invoice Date from'),
        'date_invoice_to': fields.function(lambda *a, **k: {}, method=True, type='date', string='Invoice Date to'),
        'payment_date_from': fields.function(lambda *a, **k: {}, method=True, type='date', string='Payment Date from'),
        'payment_date_to': fields.function(lambda *a, **k: {}, method=True, type='date', string='Payment Date to'),
    }

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
