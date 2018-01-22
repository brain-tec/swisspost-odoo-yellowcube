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

import netsvc
from openerp.osv import osv, fields, orm
from openerp.tools.translate import _
import logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


class account_invoice_ext(osv.Model):
    _inherit = 'account.invoice'

    def write(self, cr, uid, ids, vals, context=None):
        if context is None:
            context = {}
        if not isinstance(ids, list):
            ids = [ids]

        ret = super(account_invoice_ext, self).write(
            cr, uid, ids, vals, context=None)

        if vals.get('state', '') == 'paid':
            # The following code is because, in the case a sale order
            # has invoice_policy == 'delivery', paying an invoice which is
            # not the first one won't trigger the workflow associated to
            # the sale.order. Thus, we ask the workflow to check if it has
            # to move to some state; in practice it'll check an advance
            # from the states 'wait_invoice' or 'wait_all_invoices_end'.
            wf_service = netsvc.LocalService('workflow')
            for invoice in self.browse(cr, uid, ids, context=context):
                for order in invoice.sale_ids:
                    if order.invoice_policy == 'delivery':
                        wf_service.trg_write(uid, 'sale.order', order.id, cr)

        return ret

    def copy_to_supplier_invoice(
            self, cr, uid, ids, context=None):
        """ Copies the contents of the customer invoice into the supplier
            invoice already created by the invoicing policy of the purchase
            created by the procurements, in a previous step of the Sale
            Order Automation.
        """
        if context is None:
            context = {}
        if type(ids) is not list:
            ids = [ids]

        purchase_obj = self.pool.get('purchase.order')
        purchase_line_obj = self.pool.get('purchase.order.line')
        order_line_obj = self.pool.get('sale.order.line')
        inv_line_obj = self.pool.get('account.invoice.line')
        proc_obj = self.pool.get('procurement.order')

        original_inv = self.browse(cr, uid, ids[0], context=context)

        # Determine the purchases that the sale order originated.
        sale_order_check_total = 0.0
        purchase_ids = []
        for sale_order in original_inv.sale_ids:
            sale_order_check_total += sale_order.amount_total
            for purchase_order in sale_order.purchase_dropship_ids:
                purchase_ids.append(purchase_order.id)
        if hasattr(sale_order, 'amount_discount'):
            # For the case in which we have installed our discount module...
            sale_order_check_total -= sale_order.amount_discount

        # Gets the already created supplier invoice, that we are going to
        # modify to mimic the supplier invoice. It does that by getting the
        # invoice created by the purchase order created after merging the
        # different purchases created by the different procurements.
        # The different procurements would have resulted in the same 'final'
        # purchase order.
        proc_ids = proc_obj.search(cr, uid, [
            ('purchase_id', 'in', purchase_ids),
        ], limit=1, context=context)
        procurement = proc_obj.browse(cr, uid, proc_ids[0], context=context)
        supp_inv_id = procurement.purchase_id.invoice_ids[0].id
        # supp_inv_id = \
        #     purchase_obj.action_invoice_create(cr, uid, purchase_ids, context)

        # The payment term may be different than the one set on the customer's
        # invoice, if a different payment term is set on the route.
        stock_type = original_inv.sale_ids and \
                     original_inv.sale_ids[0].stock_type_id
        if stock_type and stock_type.supplier_payment_term_id:
            supplier_payment_term_id = stock_type.supplier_payment_term_id.id
        else:
            supplier_payment_term_id = original_inv.payment_term.id

        # We modify some values of the invoice.
        supp_inv_vals = {
            'payment_term': supplier_payment_term_id,
            'origin': original_inv.origin,
            'user_id': original_inv.user_id.id,
            'date_invoice': original_inv.date_invoice,
            'check_total': sale_order_check_total,
            'comment': 'Supplier invoice for C+C',
            'shop_id': original_inv.shop_id.id,
            'carrier_id': original_inv.carrier_id.id,
        }
        if hasattr(original_inv, 'bvr_reference'):
            # Field bvr_reference depends on the module l10n_ch_payment_slip,
            # so this attribute may not be available, and checking for the
            # attribute is faster than checking for the module in the database.
            supp_inv_vals.update({'reference': original_inv.bvr_reference})

        self.write(cr, uid, supp_inv_id, supp_inv_vals, context=context)

        # We modify the price of the invoice's lines to take those of the
        # customer invoice.
        supplier_inv = self.browse(cr, uid, supp_inv_id, context=context)
        for supp_inv_line in supplier_inv.invoice_line:

            # Gets the purchase.order.line which generated this
            # supplier-invoice line. From there we go to the sale order line
            # which generated it.
            purchase_line_ids = purchase_line_obj.search(cr, uid, [
                ('invoice_lines', 'in', supp_inv_line.id),
            ], context=context)
            if not purchase_line_ids:
                raise osv.except_osv(
                    _('Error: No purchase line found.'),
                    _('No purchase line was found having as invoice '
                      'lines one with ID={0}').format(supp_inv_line.id))

            purchase_line = purchase_line_obj.browse(
                cr, uid, purchase_line_ids[0], context=context)
            sale_order_line = purchase_line.move_dest_id.sale_line_id
            if not sale_order_line:
                # If no sale order was found it must be because the line was
                # not in the picking, but it must be on the sale.order, thus
                # we search for it. This happens with products which are
                # services, and may happen in the future with other types.
                #
                # It can be that the unit of measure indicated in the
                # sale.order.line is not the one on the
                # purchase.order.line. On a purchase.order.line
                # the quantity is always indicated in the unit of measure
                # indicated on a product to be used on purchases. It would
                # be great if the fields product_uos and product_uos_qty
                # were filled in the sale.order.line so that we know
                # the equivalence without computing them, but that is not
                # the case. Even in that case, since the unit for sale
                # is different than the unit for the purchase it
                # wouldn't be of any help because we would need to do the
                # conversion anyway. Thus on the SOA we compute the
                # equivalent quantity to the purchase unit of measure
                # when validating the sale.order, and store it in the
                # new fields product_uop and product_uop_qty
                order_line_ids = order_line_obj.search(cr, uid, [
                    ('product_id', '=', purchase_line.product_id.id),
                    ('product_uop_qty', '=', purchase_line.product_qty),
                    ('product_uop', '=', purchase_line.product_uom.id),
                ], context=context)
                if order_line_ids:
                    sale_order_line = order_line_obj.browse(
                        cr, uid, order_line_ids[0], context=context)
                else:
                    raise osv.except_osv(
                        _('Error: No sale order line found.'),
                        _('No sale order line was found having the associated '
                          'purchase line one '
                          'with ID={0}').format(purchase_line.id))

            # Now we find the customer-invoice line that was originated by
            # the previous sale.order.line, which is the invoice line we
            # are looking for to match the current supplier-invoice line.
            original_line_ids = inv_line_obj.search(cr, uid, [
                ('orig_sale_order_line_id', '=', sale_order_line.id),
            ], context=context)
            if not original_line_ids:
                raise osv.except_osv(
                    _('Error: No equivalent invoice line was found'),
                    _('No equivalent invoice line was found for line with '
                      'ID={0} from invoice with ID={1}, on invoice with '
                      'ID={2}').format(supp_inv_line.id,
                                       supp_inv_id,
                                       original_inv.id))
            if len(original_line_ids) != 1:
                original_line_ids_str = ','.join(map(str, original_line_ids))
                raise osv.except_osv(
                    _('Error: Several equivalent invoice lines were found'),
                    _('More than one equivalent invoice lines were found '
                      'for invoice line with ID={0} from invoice with ID={1},'
                      'on invoice with ID={2}. Lines found={3}.').\
                        format(supp_inv_line.id, supp_inv_id,
                               original_inv.id, original_line_ids_str))

            original_line = inv_line_obj.browse(
                cr, uid, original_line_ids[0], context=context)

            # A product probably will have set the cost price to be different
            # than the price of sale, thus we have to take it from the customer
            # invoice. However, if the purchase used a different unit of
            # measure than that indicated in the sale order, then the unit
            # price set on the customer invoice will be computed according to
            # the unit of measure set on that customer invoice, which will be
            # different than the one set on the supplier invoice (becuase it
            # comes from the purchase order), thus we have to compute the
            # price for the supplier invoice taking into account the different
            # units of measure used (if that was the case).
            #
            # For example, if a product has a UOM Units, but as Purchase UOM
            # has Packs, and 1 Pack == 2 Units, and the price is set to be
            # 1 CHF, and on the sale order you have one line of this product
            # with 2 items, then the unit price is 1 CHF, thus total 2 CHF.
            # Now, when the purchase is generated because of the procurement,
            # you'll get a purchase with one line having that product in which
            # you'll have 1 pack of it (because remember that 1 pack are
            # 2 units). Then you have to take the unit price from the
            # supplier invoice but you can not copy it directly, because you
            # have to take into account the different units of measure, since
            # if you copied it directly you would have that the total amount
            # of the line is 1 CHF, while you expect 2 CHF. Thus the unit
            # price for this case has to be 2 CHF (because the unit price
            # is not the unitary price, but the price per one magnitude
            # of the UOM set).
            if original_line.uos_id.id == supp_inv_line.uos_id.id:
                price_unit = original_line.price_unit
            else:
                # UOMs are different, thus we have to compute the price
                # scaled taking account the different units of measure.
                ratio = 1.0 / supp_inv_line.uos_id.factor
                ratio = ratio * original_line.uos_id.factor
                price_unit = original_line.price_unit * ratio

            supp_inv_line.write(
                {'price_unit': price_unit,
                 'account_analytic_id': original_line.account_analytic_id.id,
                 'discount': original_line.discount,
                 })

        # We update the invoice since stage_discount
        # requires a 'manual' update.
        self.button_reset_taxes(cr, uid, [supp_inv_id], context)

        return supp_inv_id

    def create_invoice_from_picking(self, cr, uid, ids, picking, add_discount_lines_from_order, skip_service_lines, context=None):
        """ Creates the invoice from the picking. The picking must have a sale order associated.
        """
        if context is None:
            context = {}

        sale_order_obj = self.pool.get('sale.order')
        invoice_obj = self.pool.get('account.invoice')
        ir_module_module_obj = self.pool.get('ir.module.module')
        stock_picking_obj = self.pool.get('stock.picking')
        inv_line_obj = self.pool.get('account.invoice.line')

        # Do we have to re-use the draft- invoice already created?
        reuse_draft_invoice = context.get('reuse_draft_invoice', False)

        # Makes sure we have a sale order associated to this picking.
        sale_order = picking.sale_id
        if not sale_order:
            raise orm.except_orm(_("No Sale Order Found"),
                                 _("No sale order was found for the picking with ID={0}").format(picking.id))

        picking.write({'invoice_state': '2binvoiced'})
        invoice_journal_id = sale_order.payment_method_id and sale_order.payment_method_id.journal_id and sale_order.payment_method_id.journal_id.id or False

        if reuse_draft_invoice:
            draft_invoice_ids = invoice_obj.search(cr, uid, [
                ('state', '=', 'draft'),
                ('sale_ids', 'in', sale_order.id),
            ], context=context)
            if len(draft_invoice_ids) != 1:
                raise orm.except_orm(
                    _('Wrong Amount of Draft Invoices'),
                    _('Just one invoice in state draft were expected to be '
                      'found for sale.order with ID={0}, but {1} were found '
                      'instead').format(sale_order.id, len(draft_invoice_ids)))
            else:
                invoice_id = draft_invoice_ids[0]
        else:
            res = stock_picking_obj.action_invoice_create(cr, uid, [picking.id], journal_id=invoice_journal_id, context=context)
            invoice_id = res[picking.id]

        service_line_ids = []
        non_service_line_ids = []
        invoice = invoice_obj.browse(cr, uid, invoice_id, context=context)
        for invoice_line in invoice.invoice_line:
            if invoice_line.product_id.type == 'service':
                service_line_ids.append(invoice_line.id)
            else:
                non_service_line_ids.append(invoice_line.id)

        # If we re-use the invoice that is automatically created in state
        # 'draft', then we have to remove the invoice lines created, and
        # add the ones that would be created if the invoice had been
        # created using only the lines of the picking provided. But this is
        # only if the invoice is partial, i.e. if there are several pickings
        # for a sale.order and then each one has its own invoice, thus none of
        # them can have all the lines. In this case, also, the sequence of the
        # service line has to be changed so that it is kept at the end of the
        # lines.
        invoice_is_partial = len([p for p in sale_order.picking_ids]) != 1
        if reuse_draft_invoice and invoice_is_partial:
            inv_line_obj.unlink(cr, uid, non_service_line_ids, context=context)

            invoice_vals = stock_picking_obj._prepare_invoice(
                cr, uid, picking, sale_order.partner_invoice_id.id,
                'out_invoice', invoice_journal_id,
                context=context)

            num_invoice_lines = 0
            for move_line in picking.move_lines:
                if move_line.state == 'cancel':
                    continue
                if move_line.scrapped:
                    continue  # Do no invoice scrapped products
                group = False
                vals = stock_picking_obj._prepare_invoice_line(
                    cr, uid, group, picking, move_line, invoice_id,
                    invoice_vals, context=context)
                if vals:
                    num_invoice_lines += 1
                    vals['sequence'] = num_invoice_lines
                    invoice_line_id = inv_line_obj.create(cr, uid, vals,
                                                          context=context)
                    stock_picking_obj._invoice_line_hook(cr, uid, move_line,
                                                         invoice_line_id)

            # Updates the sequences of the service lines so that they are in
            # the end, as in the picking.
            for service_line_id in service_line_ids:
                num_invoice_lines += 1
                inv_line_obj.write(cr, uid, service_line_id,
                                   {'sequence': num_invoice_lines},
                                   context=context)


        # Stores on the invoice the picking it comes from.
        invoice_obj.write(cr, uid, invoice_id, {'picking_id': picking.id}, context=context)

        # Stores on the sale.order the new invoice created, and on the invoice the sale.order it relates to.
        sale_order_obj.write(cr, uid, picking.sale_id.id, {'invoice_ids': [(4, invoice_id)]}, context=context)
        invoice_obj.write(cr, uid, invoice_id, {'sale_ids': [(4, picking.sale_id.id)]}, context=context)

        # Removes the service lines if requested and if we have any.
        if skip_service_lines and service_line_ids:
            invoice_obj.write(cr, uid, invoice_id, {
                'invoice_line': [(2, x) for x in service_line_ids],
            }, context=context)

        # Adds the discount lines from stage_discount if requested.
        if add_discount_lines_from_order:
            stage_discount_is_installed = bool(ir_module_module_obj.search(
                cr, uid, [('name', '=', 'stage_discount'),
                          ('state', '=', 'installed'),
                          ], count=1, limit=1, context=context))
            if stage_discount_is_installed:
                # Before, this was
                # ```if add_discount_lines_ and stage_discount_is_installed:```
                # but now we avoid the search if not needed, thus we place
                # the nested ```if```.
                sd_dl_model = self.pool.get('stage_discount.discount_line')
                disc_line_ids = []
                for line in sale_order.discount_line_ids:
                    disc_line_ids.append(sd_dl_model.copy(
                        cr, uid, line.id, {'order_id': False},
                        context=context))
                if disc_line_ids:
                    invoice_obj.write(cr, uid, invoice_id, {
                        'discount_line_ids': [(4, x) for x in disc_line_ids],
                    }, context=context)

        return invoice_id

    def prepare_and_open_invoice(self, cr, uid, ids, context=None):
        """ Given an invoice in state draft, it rounds the invoice to the
            5-cents (if required) and resets its taxes (just in case),
            and validates it so that it moves to state 'open'.

            Also makes sure that the shop_id and the carrier_id set on the
            sale.order is also set in the account.invoice.
        """
        if context is None:
            context = {}
        if type(ids) is not list:
            ids = [ids]

        wf_service = netsvc.LocalService('workflow')

        # Is the rounding to 5-cents active?
        round_invoices_to_5_cents = bool(self.pool['ir.model.fields'].search(cr, uid, [('model', '=', 'account.invoice'),
                                                                                       ('name', '=', 'round_inv_to_05'),
                                                                                       ], count=True, limit=1,
                                                                             context=context))

        draft_invoice_ids = self.search(cr, uid, [('id', 'in', ids), ('state', '=', 'draft')], context=context)
        for invoice in self.browse(cr, uid, draft_invoice_ids, context=context):
            if round_invoices_to_5_cents and invoice.requires_rounding():
                logger.debug("Call change_rounding() over invoice with ID={0}".format(invoice.id))
                invoice.change_rounding()

            # We update the invoice since stage_discount
            # requires a 'manual' update.
            invoice.button_reset_taxes()

            # Sets the carrier_id and shop_id from the sale.order the invoice
            # comes from.
            order = invoice.sale_ids[0]
            invoice.write({
                'carrier_id': order.carrier_id.id,
                'shop_id': order.shop_id.id,
            })

            # We validate the invoice so that it's opened.
            wf_service.trg_validate(uid, 'account.invoice', invoice.id, 'invoice_open', cr)

        return True

    def cron_send_invoices_to_doc_out(self, cr, uid, context=None):
        ''' Sends the invoices to the doc-out.
        '''
        if context is None:
            context = {}

        ir_attachment_obj = self.pool.get('ir.attachment')
        config_data = self.pool.get('configuration.data').get(cr, uid, None, context)

        # Common configuration to any option.
        file_type = 'invoice'
        sending_option = config_data.docout_invoice_sending_option

        # Do we want to send the files to an email address?
        if config_data.docout_invoice_activate_send_to_email:
            email_template_id = config_data.docout_invoice_email_template_to_docout_id
            email_address = config_data.docout_invoice_email_address
            attachment_ids = ir_attachment_obj.search(cr, uid, [('name', 'ilike', '%.pdf'),
                                                                ('docout_file_type', '=', file_type),
                                                                ('docout_state_email', '=', 'to_send'),
                                                                ], order='create_date DESC', context=context)
            if attachment_ids:
                ir_attachment_obj.send_pending_files_to_docout_email(cr, uid, attachment_ids, file_type, sending_option, email_template_id, email_address, context=context)

        # Do we want to send the files to a remote folder?
        if config_data.docout_invoice_activate_send_to_server:
            connect_transport = config_data.docout_invoice_connect_transport_id
            remote_folder = config_data.docout_invoice_folder
            attachment_ids = ir_attachment_obj.search(cr, uid, [('name', 'ilike', '%.pdf'),
                                                                ('docout_file_type', '=', file_type),
                                                                ('docout_state_remote_folder', '=', 'to_send'),
                                                                ], order='create_date DESC', context=context)
            if attachment_ids:
                ir_attachment_obj.send_pending_files_to_docout_folder(cr, uid, attachment_ids, file_type, sending_option, connect_transport, remote_folder, context=context)

        return True

    def store_backorder_products(self, cr, uid, ids, context=None):
        """ When executed, saves the products which are associated to any stock move which is in state
            waiting or confirmed, belonging to any picking which comes from any sale order associated
            to the invoice.
        """
        if context is None:
            context = {}
        if type(ids) is not list:
            ids = [ids]

        sale_order_obj = self.pool.get('sale.order')
        stock_move_obj = self.pool.get('stock.move')
        product_pending_obj = self.pool.get('pc_sale_order_automation.product_pending')

        for invoice in self.browse(cr, uid, ids, context=context):
            # Gets the sale orders associated to this invoice. Because of how the Sale Order Automation (SOA) works,
            # there should be just one.
            sale_order_ids = sale_order_obj.search(cr, uid, [('invoice_ids', 'in', invoice.id)], context=context)

            for sale_order in sale_order_obj.browse(cr, uid, sale_order_ids, context=context):
                product_pending_ids = []
                stock_move_ids = stock_move_obj.search(cr, uid, [('picking_id', 'in', [picking.id for picking in sale_order.picking_ids]),
                                                                 ('state', 'in', ('waiting', 'confirmed')),
                                                                 ], context=context)
                for stock_move in stock_move_obj.browse(cr, uid, stock_move_ids, context=context):
                    product_pending_new_id = product_pending_obj.create(cr, uid, {'product_id': stock_move.product_id.id,
                                                                                  'product_uom_qty': stock_move.product_qty,
                                                                                  'product_uom': stock_move.product_uom.id,
                                                                                  }, context=context)
                    product_pending_ids.append(product_pending_new_id)

            invoice.write({'backorder_items_for_invoice_ids': [(6, False, product_pending_ids)]})

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
