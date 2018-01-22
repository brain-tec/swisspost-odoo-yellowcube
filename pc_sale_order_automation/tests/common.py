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


class CommonTestFunctionalitySOA(object):

    def _check_carrier_from_order_in_invoice(self, order_id, invoice_ids):
        """ Checks that the invoices have the same carrier_id than the one
            set on the order.
        """
        cr, uid, ctx = self.cr, self.uid, self.context
        order_obj = self.registry('sale.order')
        invoice_obj = self.registry('account.invoice')

        order = order_obj.browse(cr, uid, order_id, context=ctx)
        for inv in invoice_obj.browse(cr, uid, invoice_ids, context=ctx):
            self.assertEqual(order.carrier_id, inv.carrier_id,
                             "Carrier ID should be the same for order with "
                             "ID={0} and invoice with ID={1}".format(order_id,
                                                                     inv.id))

    def _check_shop_from_order_in_invoice(self, order_id, invoice_ids):
        """ Checks that the invoices have the same shop_id than the one
            set on the order.
        """
        cr, uid, ctx = self.cr, self.uid, self.context
        order_obj = self.registry('sale.order')
        invoice_obj = self.registry('account.invoice')

        order = order_obj.browse(cr, uid, order_id, context=ctx)
        for inv in invoice_obj.browse(cr, uid, invoice_ids, context=ctx):
            self.assertEqual(order.shop_id, inv.shop_id,
                             "Shop ID should be the same for order with "
                             "ID={0} and invoice with ID={1}".format(order_id,
                                                                     inv.id))

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
