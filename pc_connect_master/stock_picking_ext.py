# b-*- encoding: utf-8 -*-
##############################################################################
#
#    Copyright (c) 2014 brain-tec AG (http://www.braintec-group.com)
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

import string
from openerp.osv import osv, fields, orm
from openerp.tools.translate import _
from openerp.tools import DEFAULT_SERVER_DATETIME_FORMAT
from datetime import datetime, timedelta


class stock_picking_ext(osv.Model):
    _inherit = 'stock.picking'

    def get_route(self, cr, uid, ids, context=None):
        """ Return the route associated to a picking. The route is indicated
            in the stock type associated to a sale order, thus the code
            goes into the sale order of the picking, then into the carrier
            defined in the sale order, which inside has the stock route, which
            has the route defined.
        """
        if context is None:
            context = {}
        if type(ids) is not list:
            ids = [ids]

        route = False
        picking = self.browse(cr, uid, ids[0], context=context)
        if picking.sale_id and picking.sale_id.stock_type_id:
            route = picking.sale_id.stock_type_id.route
        return route

    def is_first_delivery(self, cr, uid, ids, context=None):
        """ Returns whether this stock.picking.out is the first or
            only delivery for a given sale order.

            It will be the first if the Delivery Method (field move_type)
            is one (i.e. All at once), or if it is direct (i.e. Partial) but
            is not a backorder. That was before the picking split came into
            scene; so in addition to that, it checks whether the picking
            is the first one created 'in time'.
        """
        if context is None:
            context = {}
        if type(ids) is not list:
            ids = [ids]

        picking = self.browse(cr, uid, ids[0], context=context)

        is_first = picking.move_type == 'one' or \
            (picking.move_type == 'direct' and not picking.backorder_id)

        if is_first:
            oldest_picking_id = self.search(
                cr, uid, [
                    ('sale_id', '=', picking.sale_id.id),
                    ('state', '!=', 'cancel'),
                    ('backorder_id', '=', None),
                ], order='create_date asc', limit=1, context=context)
            if oldest_picking_id != [picking.id]:
                is_first = False

        return is_first

    def is_full_delivery(self, cr, uid, ids, context=None):
        """ It returns whether this picking is the only one associated to
            its sale order. It doesn't consider those pickings which are
            cancelled.

            If the picking has no sale.order associated, we consider that
            it is the only picking.

            This method MUST receive just an ID, or a list of just
            one ID, since otherwise just the first element will be used.
        """
        if context is None:
            context = {}
        if type(ids) is not list:
            ids = [ids]

        picking = self.browse(cr, uid, ids[0], context=context)

        is_full_delivery = True
        if picking.sale_id:
            picking_ids = [picking.id for picking in picking.sale_id.picking_ids]
            num_pickings = self.search(cr, uid, [('id', 'in', picking_ids),
                                                 ('state', '!=', 'cancel'),
                                                 ], context=context, count=True)
            is_full_delivery = (num_pickings == 1)
        return is_full_delivery

    def is_last_picking(self, cr, uid, ids, context=None):
        ''' Indicates whether a stock picking is the last one.
            This is the case if the picking is the states
            'assigned', 'done', 'cancel' and there is no other
            stock.picking which is its back-order.

            In the case we don't know for SURE that it's the last
            one, it returns False. Thus, it only returns True when
            we are 100% sure that it's the last one.

            This method MUST receive just an ID, or a list of just
            one ID, since otherwise just the first element will be used.
        '''
        if context is None:
            context = {}
        if type(ids) is not list:
            ids = [ids]

        picking = self.browse(cr, uid, ids[0], context=context)
        picking_in_target_state = picking.state in ('assigned', 'done', 'cancel')
        picking_has_backorder = bool(self.search(cr, uid, [('backorder_id', '=', picking.id),
                                                           ], context=context, count=True))
        return picking_in_target_state and (not picking_has_backorder)

    def set_stock_moves_done(self, cr, uid, ids, context=None):
        ''' Marks all the stock.moves as done.
        '''
        if context is None:
            context = {}
        picking_objs = self.pool.get('stock.picking').browse(cr, uid, ids, context=context)
        for picking_obj in picking_objs:
            stock_move_objs = picking_obj.move_lines
            for stock_move_obj in stock_move_objs:
                stock_move_obj.action_done()
        return True

    def get_file_name(self, cr, uid, ids, context=None):
        ''' Returns the file name for this stock.picking.
        '''
        if context is None:
            context = {}
        if type(ids) is not list:
            ids = [ids]
        stock_picking = self.browse(cr, uid, ids[0], context=context)
        file_name = 'delivery_order_{0}_spo{1}.pdf'.format(stock_picking.origin, stock_picking.id)
        return file_name

    def is_printed(self, cr, uid, ids, context=None):
        ''' Returns if we have printed the attachment for this picking.
        '''
        if context is None:
            context = {}
        if type(ids) is not list:
            ids = [ids]

        ir_attachment_obj = self.pool.get('ir.attachment')

        picking_id = ids[0]
        file_name = self.get_file_name(cr, uid, ids[0], context=context)

        attachment_count = ir_attachment_obj.search(cr, uid, [('res_model', 'in', ['stock.picking', 'stock.picking.in', 'stock.picking.out']),
                                                              ('res_id', '=', picking_id),
                                                              ('name', '=', file_name),
                                                              ], context=context, count=True)
        return (attachment_count > 0)

    def get_ready_for_export(self, cr, uid, ids, name, args, context=None):
        """ A stock.picking is ready for export if its sale.orders have
            printed both its invoice and delivery slip.
        """
        if context is None:
            context = {}

        project_issue_obj = self.pool.get('project.issue')
        conf_data = self.pool.get('configuration.data').get(cr, uid, [], context=context)

        # If we received a flag on the context to indicate that we have to check the date in which
        # we first checked for the value of the field ready_for_export, we keep track of it.
        check_date_ready_for_export = ('check_date_ready_for_export' in context) and conf_data.ready_for_export_check_num_minutes
        now = datetime.now()

        res = {}
        for picking in self.browse(cr, uid, ids, context=context):

            # If we chose to override the ready-for-export using the manual flag, the we don't check for anything more.
            if picking.ready_for_export_manual:
                res[picking.id] = True

            else:
                picking_is_printed = picking.is_printed()

                # if Click & Reserve, then you don't check if the invoice is printed
                if picking.sale_id.carrier_id and picking.sale_id.carrier_id.stock_type_id \
                        and picking.sale_id.carrier_id.stock_type_id.route == 'c+r':
                    res[picking.id] = picking_is_printed
                else:
                    if picking.sale_id.invoice_policy == 'delivery':  # If we need an invoice per picking, we query it:
                        invoice_is_printed = bool(picking.invoice_id and picking.invoice_id.is_printed())
                    else:  # If we didn't want an invoice per picking, but just one.
                        if picking.backorder_id:  # In this case, if it's a back-order, we check if the first invoice is printed.
                            invoice_is_printed = bool(picking.sale_id.first_invoice_id and picking.sale_id.first_invoice_id.is_printed())
                        else:  # Otherwise, we get the invoice associated to the picking.
                            invoice_is_printed = bool(picking.invoice_id and picking.invoice_id.is_printed())
                    res[picking.id] = picking_is_printed and invoice_is_printed

                if (not res[picking.id]) and check_date_ready_for_export:
                    create_date = datetime.strptime(picking.create_date, DEFAULT_SERVER_DATETIME_FORMAT)
                    if now > create_date + timedelta(minutes=conf_data.ready_for_export_check_num_minutes):
                        alarm_message = _("Picking with ID={0} has had the flag 'ready_for_export' set to False many time.").format(picking.id)
                        project_issue_obj.create_issue(cr, uid, 'stock.picking.out', picking.id, alarm_message, context=context)

        return res

    def _fun_get_invoice(self, cr, uid, ids, field, arg=None, context=None):
        """ Gets the invoice associated to a picking. The most reliable way,
            and the way it's going to be used in the code, is that the Sale
            Order Automation sets the parameter 'picking_id' in an invoice
            when it's created; but, since the SOA is supposed to be optional,
            then we must find the way to return an invoice for a picking
            even if we don't have this field set, and that's why we may
            resort to the field 'first_invoice_id' of the sale.order
            associated to the picking.
        """
        if context is None:
            context = {}
        if type(ids) is not list:
            ids = [ids]

        account_invoice_obj = self.pool.get('account.invoice')
        stock_picking_obj = self.pool.get('stock.picking')

        res = {}
        for picking_id in ids:
            res[picking_id] = False

            invoice_ids = account_invoice_obj.search(
                cr, uid, [('picking_id', '=', picking_id)],
                order='create_date', context=context, limit=1)

            if invoice_ids:
                # The SOA has set the field 'picking_id', so we use it.
                res[picking_id] = invoice_ids[0]

            else:
                # The SOA has not set the field 'picking_id', so we avoid it.
                picking = stock_picking_obj.browse(cr, uid, picking_id,
                                                   context=context)
                if picking.sale_id and picking.sale_id.first_invoice_id:
                    res[picking_id] = picking.sale_id.first_invoice_id.id
        return res

    _columns = {
        'do_not_send_to_warehouse': fields.boolean('Do Not Send to Warehouse',
                                                   help='If checked, this picking will not be sent to the warehouse.'),

        #<MOVE> to pc_connect_warehouse? I think it's used only there.
        'carrier_tracking_ref': fields.char('Carrier Tracking Ref', size=256),  # Redefines the field.

        # TODO: Bulk-freight related logic (and this includes packaging) may be moved to pc_connect_master
        # even if it's going to be used only on the automation, since bulk freight in particular is used
        # outside the automation, so in the future packages may be needed outside it also.
        'uses_bulkfreight': fields.boolean('Picking Uses Bulk Freight?'),

        'ready_for_export': fields.function(get_ready_for_export,
                                            type='boolean',
                                            string='Ready for Export?',
                                            help='Indicates whether the stock.picking is ready for export to the warehouse.'),
        'ready_for_export_manual': fields.boolean('Manual Ready for Export?',
                                                  help="If checked, it overrides the field 'Ready for Export?' and marks the picking as being ready for export."),

        'create_date': fields.datetime('Create Date', help="Redefined just to be able to use it from the model."),

        'invoice_id': fields.function(
            _fun_get_invoice, string='Invoice', type='many2one',
            relation='account.invoice', store=False,
            help='Returns the invoice which was linked to this '
                 'stock.picking, if any.'),

        'backorder_items_for_pickings_ids': fields.many2many('pc_sale_order_automation.product_pending',
                                                             rel='backorder_items_for_pickings',
                                                             id1='picking_id', id2='product_pending_id'),

        'yc_mandatory_additional_shipping': fields.char(
            'Mandatory additional services',
            help='These mandatory additional service codes must '
                 'be added to the WAB when submitting it to YellowCube.'),
    }

    _defaults = {
        'uses_bulkfreight': False,
        'ready_for_export': False,
        'ready_for_export_manual': False,
    }

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
