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
from openerp.osv import osv, fields
from openerp.tools.translate import _
from openerp.addons.bt_helper.log_rotate import get_log
logger = get_log("DEBUG")
from openerp.tests import common


class fixed_percentage_discount(common.TransactionCase):

    def setUp(self):
        super(fixed_percentage_discount, self).setUp()

    def tearDown(self):
        super(fixed_percentage_discount, self).tearDown()

    def test(self):
        """
        Test discounts [FIXED+PERCENTAGE].
        Test a percentage and a fix price.
        a) I create an account invoice
        """
        cr, uid, ctx = self.cr, self.uid, {}
        invoice_obj = self.registry('account.invoice')
        stgdisc_lin_obj = self.registry('stage_discount.discount_line')

        vals = {
            'account_id': self.ref('account.a_recv'),
            'company_id': self.ref('base.main_company'),
            'currency_id': self.ref('base.EUR'),
            'invoice_line': [(0, 0, {
                'account_id': self.ref('account.a_sale'),
                'name': '[PCSC234] PC Assemble SC234',
                'price_unit': 450.0,
                'quantity': 1.0,
                'product_id': self.ref('product.product_product_3'),
                'uos_id': self.ref('product.product_uom_unit'),
                'invoice_line_tax_id': [(5)],
            })],
            'journal_id': self.ref('account.bank_journal'),
            'partner_id': self.ref('base.res_partner_12'),
            # 'reference_type': None,
        }
        invoice_id = invoice_obj.create(cr, uid, vals, ctx)
        invoice = invoice_obj.browse(cr, uid, invoice_id, ctx)
        self.assertEqual(invoice.state, 'draft', 'I check that Initially customer invoice state is "Draft"')
        # Create a discount invoice lines which value is percentage 10. sequence 1.
        vals = {
            'discount_type': 'fixed',
            'discount_value': 100,
            'sequence': 1,
            'description': 'Fixed',
            'invoice_id': invoice_id
        }
        stgdisc_lin_obj.create(cr, uid, vals, ctx)
        #   Create a discount invoice lines which value is percentage 10. sequence 2.
        vals = {
            'discount_type': 'percentage',
            'discount_value': 10,
            'sequence': 2,
            'description': 'Percentage',
            'invoice_id': invoice_id
        }
        stgdisc_lin_obj.create(cr, uid, vals, ctx)
        # Calculate the discount
        invoice_obj.button_reset_taxes(cr, uid, [invoice_id])
        invoice = invoice.browse(context=ctx)[0]
        """
        f) Check discount amount of 10% and 100 € over 450.
            450 - 100 - 10%
            450 - 100 - 45 = -145 discount
        """
        self.assertEqual(invoice.amount_discount, -145)
        self.assertEqual(invoice.amount_untaxed, 305)
        self.assertEqual(invoice.amount_tax, 0)
        self.assertEqual(invoice.amount_total, 305)

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: