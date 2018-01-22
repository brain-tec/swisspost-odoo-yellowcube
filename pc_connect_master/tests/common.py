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

from openerp.tools import DEFAULT_SERVER_DATETIME_FORMAT
from openerp.osv import osv, fields
import netsvc
import time
from datetime import datetime, timedelta


class CommonTestFunctionality(object):

    def validate_invoice(self, delegate, invoice_id):
        """ Validates the invoice.
        """
        wf_service = netsvc.LocalService('workflow')
        wf_service.trg_validate(delegate.uid, 'account.invoice', invoice_id,
                                'invoice_open', delegate.cr)

    def create_sale_order(self, delegate, defaults=None):
        """ Creates a sale order with default values, that can be overridden
            with the values sent as the 'defaults' parameter.
        """
        if defaults is None:
            defaults = {}
        cr, uid, ctx = delegate.cr, delegate.uid, delegate.context
        order_obj = delegate.registry('sale.order')

        partner_id = delegate.ref('base.res_partner_2')
        vals = {
            'partner_id': partner_id,
            'partner_invoice_id': partner_id,
            'partner_shipping_id': partner_id,
            'date_order': fields.date.today(),
            'payment_method_id':
                delegate.ref('pc_connect_master.payment_method_epaid'),
            'carrier_id': delegate.ref('delivery.delivery_carrier'),
            'pricelist_id': delegate.ref('product.list0'),
        }
        vals.update(defaults)

        order_id = order_obj.create(cr, uid, vals, context=ctx)
        return order_id

    def create_sale_order_line(self, delegate, vals):
        """ Creates a sale order line with the values indicated in
            the parameter 'vals'.
        """
        cr, uid, ctx = delegate.cr, delegate.uid, delegate.context
        line_obj = delegate.registry('sale.order.line')

        uom_id = delegate.ref('product.product_uom_unit')
        create_vals = {
            'product_id': vals['product_id'],
            'name': vals.get('name', 'Default Name'),
            'product_uom_qty': vals['product_uom_qty'],
            'price_unit': vals.get('price_unit', 1),
            'order_id': vals['order_id'],
            'product_uom': vals.get('product_uom', uom_id),
        }

        order_line_id = line_obj.create(cr, uid, create_vals, context=ctx)
        return order_line_id

    def create_product(self, delegate, vals):
        """ Creates a not-lotted product. To make a product lotted, create
            a lot for it using create_lot().
        """
        cr, uid, ctx = delegate.cr, delegate.uid, delegate.context
        prod_obj = delegate.registry('product.product')

        uom_unit_id = delegate.ref('product.product_uom_unit')
        create_vals = {
            'uom_id': uom_unit_id,
            'uom_po_id': uom_unit_id,
            'sale_ok': True,
            'purchase_ok': True,

            'track_production': False,
            'track_incoming': False,
            'track_outgoing': False,
        }
        create_vals.update(vals)

        prod_id = prod_obj.create(cr, uid, create_vals, context=ctx)
        return prod_id

    def create_lot(self, delegate, lot_name, product_id, 
                   expiration_days_offset):
        """ Creates a lot for a product. Sets the product as lotted.
        """
        cr, uid, ctx = delegate.cr, delegate.uid, delegate.context
        lot_obj = delegate.registry('stock.production.lot')
        product_obj = delegate.registry('product.product')

        # Sets the product as stockable.
        product_obj.write(cr, uid, product_id, {
            'track_production': True,
            'track_incoming': True,
            'track_outgoing': True,
        }, context=ctx)

        now = datetime.now()
        lot_date = datetime.strftime(
            now + timedelta(expiration_days_offset),
            DEFAULT_SERVER_DATETIME_FORMAT
        )

        create_vals = {
            'name': lot_name,
            'product_id': product_id,
            'date': lot_date,
            'life_date': lot_date,
            'use_date': lot_date,
            'removal_date': lot_date,
            'alert_date': lot_date,
            'production_date': lot_date,
        }

        lot_id = lot_obj.create(cr, uid, create_vals, context=ctx)
        return lot_id

    def obtain_qty(self, delegate, product_id, qty, shop_id, lot_id=None):
        """ Orders the indicated quantity for the product (in units),
            and places it on the warehouse of the shop indicated.
        """
        cr, uid, ctx = delegate.cr, delegate.uid, delegate.context

        wf_service = netsvc.LocalService('workflow')

        purchase_obj = delegate.registry('purchase.order')
        purchase_line_obj = delegate.registry('purchase.order.line')
        product_obj = delegate.registry('product.product')
        picking_in_obj = delegate.registry('stock.picking.in')
        partial_picking_obj = delegate.registry('stock.partial.picking')
        partial_picking_line_obj = \
            delegate.registry('stock.partial.picking.line')
        move_obj = delegate.registry('stock.move')
        shop_obj = delegate.registry('sale.shop')

        uom_unit_id = delegate.ref('product.product_uom_unit')
        supplier_id = delegate.ref('base.res_partner_1')
        pricelist_id = delegate.ref('product.list0')

        product = product_obj.browse(cr, uid, product_id, context=ctx)
        shop = shop_obj.browse(cr, uid, shop_id, context=ctx)

        # Creates a purchase order with the product that we need.
        purchase_create_vals = {
            'name': 'PO - PROD {0} - {1} - QTY {2} - {3}'.format(
                product_id, shop.name, qty, time.time()),
            'partner_id': supplier_id,
            'date_order': fields.date.today(),
            'warehouse_id': shop.warehouse_id.id,
            'location_id': shop.warehouse_id.lot_stock_id.id,
            'pricelist_id': pricelist_id,
            'invoice_method': 'picking',
        }
        purchase_id = purchase_obj.create(cr, uid, purchase_create_vals, ctx)

        purchase_line_create_vals = {
            'product_id': product_id,
            'name': product.name,
            'date_planned': fields.date.today(),
            'product_qty': qty,
            'product_uom': uom_unit_id,
            'price_unit': 1,
            'order_id': purchase_id,
        }
        purchase_line_obj.create(cr, uid, purchase_line_create_vals, ctx)

        # Validates the purchase so that it creates the picking.in
        wf_service.trg_validate(
            uid, 'purchase.order', purchase_id, 'purchase_confirm', cr)

        # Gets the ID of the picking.in created.
        picking_in_ids = picking_in_obj.search(
            cr, uid, [('purchase_id', '=', purchase_id)], context=ctx)
        picking_in_id = picking_in_ids[0]

        # Sets the lot on the line if it has one.
        if lot_id:
            move_ids = move_obj.search(cr, uid, [
                ('picking_id', '=', picking_in_id),
            ], context=ctx)
            move_obj.write(cr, uid, move_ids, {'prodlot_id': lot_id},
                           context=ctx)

        # Validates & receives the picking.
        picking = picking_in_obj.browse(cr, uid, picking_in_id, context=ctx)
        picking_in_obj.draft_force_assign(cr, uid, [picking_in_id])

        move = picking.move_lines[0]
        partial_picking_id = partial_picking_obj.create(cr, uid, {
            'date': fields.date.today(),
            'picking_id': picking_in_id,
        }, context=ctx)
        partial_picking_line_obj.create(cr, uid, {
            'product_id': move.product_id.id,
            'quantity': qty,
            'yc_qty_done': qty,  # This is in pc_connect_warehouse_yellowcube.
            'product_uom': move.product_uom.id,
            'prodlot_id': move.prodlot_id.id,
            'wizard_id': partial_picking_id,
            'location_id': move.location_id.id,
            'location_dest_id': move.location_dest_id.id,
            'move_id': move.id,
        }, context=ctx)
        partial_picking_obj.do_partial(
            cr, uid, [partial_picking_id], context=ctx)

        return True

    def consume_qty(self, delegate, product_id, qty, shop_id,
                    defaults_sale_order=None):
        """ Orders the indicated quantity for the product (in units),
            and places it on the warehouse of the shop indicated.
        """
        if defaults_sale_order is None:
            defaults_sale_order = {}
        cr, uid, ctx = delegate.cr, delegate.uid, delegate.context

        order_obj = delegate.registry('sale.order')
        line_obj = delegate.registry('sale.order.line')
        shop_obj = delegate.registry('sale.shop')
        product_obj = delegate.registry('product.product')

        product = product_obj.browse(cr, uid, product_id, context=ctx)
        shop = shop_obj.browse(cr, uid, shop_id, context=ctx)

        partner_id = delegate.ref('base.res_partner_2')
        payment_epaid_id = \
            delegate.ref('pc_connect_master.payment_method_epaid')
        pricelist_id = delegate.ref('product.list0')
        carrier_id = delegate.ref('delivery.delivery_carrier')
        uom_unit_id = delegate.ref('product.product_uom_unit')

        # Creates the sale order.
        order_vals = {
            'name': 'SO - PROD {0} - {1} - QTY {2} - {3}'.format(
                product_id, shop.name, qty, time.time()),
            'partner_id': partner_id,
            'partner_invoice_id': partner_id,
            'partner_shipping_id': partner_id,
            'date_order': fields.date.today(),
            'payment_method_id': payment_epaid_id,
            'carrier_id': carrier_id,
            'pricelist_id': pricelist_id,
            'shop_id': shop.id,
        }
        order_vals.update(defaults_sale_order)
        order_id = order_obj.create(cr, uid, order_vals, context=ctx)

        # Adds the line to the sale order.
        order_line_vals = {
            'product_id': product.id,
            'name': product.name,
            'product_uom_qty': qty,
            'price_unit': 1,
            'order_id': order_id,
            'product_uom': uom_unit_id,
        }
        line_obj.create(cr, uid, order_line_vals, context=ctx)

        return order_id

    def validate_order(self, delegate, sale_id):
        """ Validates the given sale order.
        """
        cr, uid, ctx = delegate.cr, delegate.uid, delegate.context
        order_obj = delegate.registry('sale.order')
        order_obj.action_button_confirm(cr, uid, [sale_id], ctx)

    def assign_picking_from_order(self, delegate, sale_id):
        """ Assigns the picking.out from a sale order.
        """
        cr, uid, ctx = delegate.cr, delegate.uid, delegate.context
        order_obj = delegate.registry('sale.order')
        picking_out_obj = delegate.registry('stock.picking.out')
        order = order_obj.browse(cr, uid, sale_id, context=ctx)

        picking_ids = []

        for picking in order.picking_ids:
            picking_ids.append(picking.id)
            picking_out_obj.action_assign(cr, uid, [picking.id], ctx)

        return picking_ids

    def deliver_assigned_picking(self, delegate, picking_ids, lot_id=None):
        """ Delivers the picking.outs.
        """
        cr, uid, ctx = delegate.cr, delegate.uid, delegate.context

        move_obj = delegate.registry('stock.move')
        partial_picking_obj = delegate.registry('stock.partial.picking')
        partial_picking_line_obj = \
            delegate.registry('stock.partial.picking.line')
        picking_obj = delegate.registry('stock.picking')

        delivered_pickings = []
        for picking in picking_obj.browse(cr, uid, picking_ids, context=ctx):
            delivered_pickings.append(picking.id)

            partial_picking_id = partial_picking_obj.create(cr, uid, {
                'date': fields.date.today(),
                'picking_id': picking.id,
            }, context=ctx)

            for move in picking.move_lines:

                # Sets the lot on the line if it has one.
                if lot_id:
                    move_ids = move_obj.search(cr, uid, [
                        ('picking_id', '=', picking.id),
                    ], context=ctx)
                    move_obj.write(cr, uid, move_ids, {'prodlot_id': lot_id},
                                   context=ctx)

                partial_picking_line_obj.create(cr, uid, {
                    'product_id': move.product_id.id,
                    'quantity': move.product_qty,
                    'yc_qty_done': move.product_qty,  # On pc_connect_warehouse_yellowcube.
                    'product_uom': move.product_uom.id,
                    'prodlot_id': move.prodlot_id.id,
                    'wizard_id': partial_picking_id,
                    'location_id': move.location_id.id,
                    'location_dest_id': move.location_dest_id.id,
                    'move_id': move.id,
                }, context=ctx)

            partial_picking_obj.do_partial(
                cr, uid, [partial_picking_id], context=ctx)

        return delivered_pickings

    def get_states(self, delegate, res_id, res_type):
        """ Gets the state of the model, as tuple containing:
            (order's state, set([workflow's state 1, workflow's state 2, ...]) )
            Notice that one workflow can have more than one state, and this
            is OK.
        """
        cr, uid, ctx = delegate.cr, delegate.uid, delegate.context

        table_name = res_type.replace('.', '_')
        cr.execute("SELECT state "
                   "FROM {table} "
                   "WHERE id = {res_id}".format(table=table_name,
                                                res_id=res_id))
        rows = cr.fetchall()
        state_order = rows[0][0]

        cr.execute("SELECT name "
                   "FROM wkf_activity "
                   "WHERE id in ( "
                   "   SELECT act_id "
                   "   FROM wkf_workitem "
                   "   WHERE inst_id = ("
                   "      SELECT id "
                   "      FROM wkf_instance "
                   "      WHERE res_id={0} AND res_type='{1}' "
                   "   ) "
                   ")".format(res_id, res_type))
        rows = cr.fetchall()
        state_workflow = set([row[0] for row in rows])

        return state_order, state_workflow

    def set_config(self, delegate, key, value):
        """ Auxiliary method to set a value on the configuration.
        """
        cr, uid, context = delegate.cr, delegate.uid, delegate.context

        conf_id = delegate.ref('pc_config.default_configuration_data')
        conf_obj = delegate.registry('configuration.data')
        conf_obj.write(cr, uid, conf_id, {key: value}, context=context)

    def pay_invoice(self, delegate, invoice_id, amount=None):
        """ Pays the invoice.
        """
        cr, uid, ctx = delegate.cr, delegate.uid, delegate.context

        invoice_obj = self.registry('account.invoice')

        journal_id = self.ref('account.bank_journal')
        pay_account_id = self.ref('account.cash')
        period_id = self.ref('account.period_10')

        invoice = invoice_obj.browse(cr, uid, invoice_id, context=ctx)

        # The amount paid is by default the original for the invoice, but
        # can be different if indicated.
        pay_amount = invoice.amount_total
        if amount is not None:
            pay_amount = amount

        invoice_obj.pay_and_reconcile(
            cr, uid, [invoice_id],
            pay_amount=pay_amount,
            pay_account_id=pay_account_id,
            period_id=period_id,
            pay_journal_id=journal_id,
            writeoff_acc_id=pay_account_id,
            writeoff_period_id=period_id,
            writeoff_journal_id=journal_id,
            name="Payment for invoice with ID={0}".format(invoice_id),
            context=ctx)

    def get_pickings_for_sale_order(self, delegate, order_id):
        cr, uid, ctx = delegate.cr, delegate.uid, delegate.context
        picking_ids = self.registry('stock.picking').search(cr, uid, [
            ('sale_id', '=', order_id),
        ], context=ctx)
        return picking_ids

    def get_invoices_for_sale_order(self, delegate, order_id):
        cr, uid, ctx = delegate.cr, delegate.uid, delegate.context
        invoice_ids = self.registry('account.invoice').search(cr, uid, [
            ('sale_ids', 'in', order_id),
        ], context=ctx)
        return invoice_ids

    def check_num_and_get_invoices(self, delegate, order_id, num):
        invoice_ids = self.get_invoices_for_sale_order(delegate, order_id)
        delegate.assertEqual(num, len(invoice_ids))
        return invoice_ids

    def check_num_and_get_pickings(self, delegate, order_id, num):
        picking_ids = self.get_pickings_for_sale_order(delegate, order_id)
        delegate.assertEqual(num, len(picking_ids))
        return picking_ids

    def find_backorder(self, delegate, picking_ids):
        """ Receives a list of picking's IDs and returns a tuple of the
            - ID of the picking which has the pending quantities (that we call
              --wrongly-- 'the backorder')
            - LIST of IDs of the other pickings.
        """
        cr, uid, ctx = delegate.cr, delegate.uid, delegate.context
        picking_obj = self.registry('stock.picking')

        pending_ids = []
        non_pending_ids = []

        for picking_id in picking_ids:
            if picking_obj.search(cr, uid, [
                ('backorder_id', '=', picking_id),
                ('id', 'in', picking_ids),
            ], count=True, limit=1, context=ctx):
                non_pending_ids.append(picking_id)
            else:
                pending_ids.append(picking_id)

        self.assertEqual(len(pending_ids), 1, "Just one pending picking is expected")
        pending_id = pending_ids[0]

        return pending_id, non_pending_ids

    def check_invoice_has_service_line(self, delegate, invoice_id,
                                       must_have_service_line):
        """ Checks that the invoice has a service line, and in the case of
            having one, make sure they are the last ones on the invoice.
        """
        cr, uid, ctx = delegate.cr, delegate.uid, delegate.context
        invoice_obj = self.registry('account.invoice')

        service_line_found = False
        invoice = invoice_obj.browse(cr, uid, invoice_id, context=ctx)
        for inv_line in invoice.invoice_line:
            if inv_line.product_id.type == 'service':
                service_line_found = True
                if not must_have_service_line:
                    self.assertTrue(False, "Invoice {0} must not have a "
                                           "service line.".format(invoice_id))
            else:
                if service_line_found:
                    self.assertTrue(False, "Invoice {0} has a service line "
                                           "but is not the last "
                                           "line.".format(invoice_id))

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
