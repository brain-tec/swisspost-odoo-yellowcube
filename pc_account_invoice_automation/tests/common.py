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


DEFAULT_PRICE_UNIT = 7
DEFAULT_PRODUCT_UOM_QTY = 17


class CommonTestFunctionalityAIA(object):

    def create_invoice(self, delegate, defaults=None):
        """ Creates an invoice.
        """
        if defaults is None:
            defaults = {}
        cr, uid, ctx = delegate.cr, delegate.uid, delegate.context

        journal_obj = delegate.registry('account.journal')
        account_obj = delegate.registry('account.account')
        invoice_obj = delegate.registry('account.invoice')

        partner_id = delegate.ref('base.res_partner_2')
        journal_id = journal_obj.search(
            cr, uid, [('type', '=', 'sale')], context=ctx)[0]
        account_id = account_obj.search(
            cr, uid, [('type', '=', 'receivable')], context=ctx)[0]

        values = {
            'partner_id': partner_id,
            'account_id': account_id,
            'journal_id': journal_id,
        }
        if defaults:
            values.update(defaults)

        inv_id = invoice_obj.create(cr, uid, values, context=ctx)
        return inv_id

    def create_invoice_line(self, delegate, invoice_id, defaults=None):
        """ Creates an invoice line and adds it to the invoice indicated.
        """
        if defaults is None:
            defaults = {}
        cr, uid, ctx = delegate.cr, delegate.uid, delegate.context

        invoice_obj = delegate.registry('account.invoice')
        invoice_line_obj = delegate.registry('account.invoice.line')

        test_product_id = delegate.ref('product.product_product_48')
        uom_unit_id = delegate.ref('product.product_uom_unit')

        values = {
            'name': "Test Product",
            'product_id': test_product_id,
            'quantity': DEFAULT_PRODUCT_UOM_QTY,
            'uos_id': uom_unit_id,
            'price_unit': DEFAULT_PRICE_UNIT,
            'invoice_id': invoice_id
        }
        values.update(defaults)

        inv_line_id = invoice_line_obj.create(cr, uid, values, context=ctx)
        invoice_obj.button_reset_taxes(cr, uid, [invoice_id], context=ctx)
        return inv_line_id

    def _automate_order(self, delegate, order_id, state_first, state_last, assignation, backorder_id=False):
        """ Automates a sale order from one state to the other one.
            It calls repeteadly the method to move the order through the
            sale order automation, and checks that the chain of states is
            done correctly, only that.
        """
        cr, uid, context = delegate.cr, delegate.uid, delegate.context
        sale_order_obj = delegate.registry('sale.order')

        order = sale_order_obj.browse(cr, uid, order_id, context=context)

        conf = delegate.browse_ref('pc_config.default_configuration_data')
        if order.do_credit_check():
            states_current_expected = [
                ('saleorder_check_inventory_for_quotation', 'saleorder_checkcredit'),
                ('saleorder_checkcredit', 'saleorder_draft'),
            ]
        else:
            states_current_expected = [
                ('saleorder_check_inventory_for_quotation', 'saleorder_draft'),
            ]

        states_current_expected.extend([
            ('saleorder_draft', 'saleorder_sent'),
            ('saleorder_sent', 'deliveryorder_assignation_{0}'.format(assignation)),
        ])

        if conf.packaging_enabled:
            states_current_expected.extend([
                ('deliveryorder_assignation_{0}'.format(assignation), 'do_multi_parcel_deliveries'),
                ('do_multi_parcel_deliveries', 'print_deliveryorder_in_local'),
            ])
        else:
            states_current_expected.extend([
                ('deliveryorder_assignation_{0}'.format(assignation), 'print_deliveryorder_in_local'),
            ])
        states_current_expected.extend([
            ('print_deliveryorder_in_local', 'invoice_open'),
            ('invoice_open', 'print_invoice_in_local'),
            ('print_invoice_in_local', False),
        ])

        automation_started = False
        for state_current, state_expected in states_current_expected:
            # Skips the states until we find the one we want to start with,
            # but only if we haven't started the automation yet (because
            # that means that we have already found the first state).
            if state_current != state_first and not automation_started:
                continue
            automation_started = True

            soa_info = sale_order_obj.automate_sale_order(
                cr, uid, order_id, state_current,
                False, backorder_id=backorder_id, context=context)

            delegate.assertEqual(soa_info.error, False,
                                 "On state {0}, error: {1}".format(
                                     state_current, soa_info.error))
            delegate.assertEqual(soa_info.delay, False,
                                 "On state {0}.".format(state_current))
            delegate.assertEqual(soa_info.next_state, state_expected,
                                 "On state {0}.".format(state_current))
            delegate.assertEqual(soa_info.next_state_time, False,
                                 "On state {0}.".format(state_current))

            # Once we have arrived to the end state and have processed it,
            # we end the 'automation'.
            if state_current == state_last:
                break

        return True

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
