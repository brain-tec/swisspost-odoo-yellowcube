# -*- coding: utf-8 -*-
##############################################################################
#
#    Copyright (c) 2016 brain-tec AG (http://www.braintec-group.com)
#    All Right Reserved
#
#    See LICENSE file for full licensing details.
##############################################################################
from openerp.tools.translate import _
from .file_processor import FileProcessor, WAB_WAR_ORDERNO_GROUP
from .xml_tools import Dict2Object
import logging
_logger = logging.getLogger(__name__)


class WarProcessor(FileProcessor):
    """
    This class reads a WAR file from Yellowcube

    Version: 1.4
    """
    def __init__(self, backend):
        super(WarProcessor, self).__init__(backend, 'war')

    def yc_read_war_file(self, war_file):
        war_file.info = ''
        self.log_message(
            'Reading WAR file {0}\n'.format(war_file.name),
            file_record=war_file,
            timestamp=True)
        if not self.validate_file(war_file):
            return

        errors = []
        related_ids = []
        all_war_ctx = []
        try:
            for war in self.path(self.tools.open_xml(war_file.content,
                                                     _type='war'),
                                 '//war:WAR'):
                # Context object
                war_ctx = Dict2Object()
                all_war_ctx.append(war_ctx)
                # Global File parameters
                war_ctx.errors = errors
                war_ctx.related_ids = related_ids
                war_ctx.file = war_file
                # Node specific parameters
                war_ctx.splits = []
                war_ctx.xml = war
                war_ctx.stop = False

                self._get_order(war_ctx)
                if war_ctx.stop:
                    continue

                war_header = self.path(war, '//war:CustomerOrderHeader')[0]
                _additionalServ = self.path(war_header,
                                            '//war:AdditionalServices')
                if _additionalServ:
                    _additionalServ = _additionalServ[0]
                    _bss = self.path(_additionalServ,
                                     '//war:BasicShippingServices')[0]
                    shipping_service_code = self.backend_record.get_binding(
                        war_ctx.picking.carrier_id, 'BasicShippingServices')
                    if _bss != shipping_service_code:
                        war_ctx.errors.append(
                            _('BasicShippingServices code on WAR file (%s) '
                              'differs from carrier value (%s).') %
                            (_bss, shipping_service_code)
                        )

                # OrderPositions
                for war_line in self.path(war, '//war:CustomerOrderDetail'):
                    self.yc_read_war_line(war_ctx, war_line)

        except Exception as e:
            # In this extension, nothing is created,
            # and then a rollback can be avoided
            error_text = self.tools.format_exception(e)
            errors.append(error_text)
            for error in errors:
                _logger.debug(error)

        if len(all_war_ctx) == 0:
            _logger.info('There are no pickings in this file, and it is ok: %s'
                         % war_file.name)

        if errors:
            war_file.state = 'error'
            self.log_message(
                'WAR file errors:\n{0}\n'.format('\n'.join(errors)),
                file_record=war_file)
        else:
            for war_ctx in all_war_ctx:
                self.yc_process_war_splits(war_ctx.picking,
                                           related_ids,
                                           war_ctx.splits)
                related = ('stock.picking', war_ctx.picking.id)
                if related not in related_ids:
                    related_ids.append(related)
            war_file.state = 'done'
            war_file.child_ids = [(0, 0, {'res_model': x[0], 'res_id': x[1]})
                                  for x in related_ids]
            self.log_message('WAR file processed\n', file_record=war_file)

    def _get_order(self, war_ctx):
        war = war_ctx.xml
        errors = war_ctx.errors

        # OrderNo
        orderno_node = self.path(war, '//war:CustomerOrderNo')
        war_ctx.order_no = orderno_node[0].text if orderno_node else None

        war_ctx.picking = self.\
            find_binding(war_ctx.order_no,
                         WAB_WAR_ORDERNO_GROUP).record
        if not war_ctx.picking:
            errors.append(_('Cannot find binding for order {0}')
                          .format(war_ctx.order_no))
            war_ctx.stop = True
            return
        # The picking to work with always must be ready
        if war_ctx.picking.state in ['done', 'cancel']:
            errors.append(_('Picking cannot be processed'))
            war_ctx.stop = True

    def yc_get_related_pickings_by_destination(
            self, original_picking, states=None):
        candidate_pickings = self.env['stock.picking'].search([
            ('group_id', '=', original_picking.group_id.id),
            ('state', 'in', states or ['assigned', 'waiting']),
            ('location_id', '=', original_picking.location_dest_id.id)
        ])
        return candidate_pickings

    def yc_process_war_splits(self, picking, related_ids, splits):
        """
        """

        for split in splits:
            operation = split['operation']
            related = ('stock.pack.operation', operation.id)
            if related not in related_ids:
                related_ids.append(related)
            operation.qty_done += split['qty']
        self.yc_confirm_picking(picking, related_ids)

    def yc_confirm_picking(self, picking, related_ids):
        picking.do_recompute_remaining_quantities()
        if all(picking.pack_operation_product_ids.mapped(
                lambda x: x.product_qty == x.qty_done
        )):
            picking.action_done()
        states = ['waiting', 'confirmed', 'partially_available']
        for related in self. \
                yc_get_related_pickings_by_destination(picking,
                                                       states=states):
            related.do_recompute_remaining_quantities()
            related.action_assign()
            related_ids.append(('stock.picking', related.id))

    def yc_read_war_line(self, war_ctx, war_line):
        # Variables to use from context
        order_no = war_ctx.order_no
        errors = war_ctx.errors

        pos_no = self.path(war_line, 'war:CustomerOrderPosNo')[0].text
        pos_no = int(pos_no)
        pack = self.find_binding(pos_no, 'CustomerOrderNo{0}'
                                 .format(order_no)).record

        if pack:
            product = pack.product_id
            qty_uom = self.path(war_line, 'war:QuantityUOM')[0]
            qty_todo = float(qty_uom.text or 0)
        else:
            errors.append(_('Cannot find binding for moves for operation {0}'
                            ' of order {1}').format(pos_no,
                                                    order_no))
            return []

        splits = self.yc_create_splits_for_product(war_ctx, pos_no,
                                                   product, qty_todo,
                                                   qty_uom)

        return splits

    def yc_create_splits_for_product(self, war_ctx, pos_no, product,
                                     qty_todo, qty_uom):
        # Variables to use from context
        picking = war_ctx.picking
        errors = war_ctx.errors
        splits = war_ctx.splits

        operations = picking.pack_operation_product_ids.filtered(
            lambda x: (
                x.product_id == product
            )
        )
        if len(operations) == 0 and qty_todo > 0:
            errors.append(_('There are not stock operations for product %s')
                          % product.default_code)
            return splits

        for operation in operations:
            if qty_todo == 0:
                break
            split = None
            for split2 in splits:
                if split2['operation'] == operation:
                    split = split2
                    break
            if split is None:
                split = {
                    'operation': operation,
                    'product': product,
                    'qty': 0
                }
                splits.append(split)
            qty = min(
                qty_todo,
                max(0, (operation.product_qty -
                        operation.qty_done -
                        split['qty']))
            )
            qty_todo -= qty
            split['qty'] += qty
            uom_code = operation.product_uom_id.iso_code
            if uom_code != qty_uom.get('QuantityISO'):
                errors.append(_('Move {0} differ'
                                'in ISO code'.format(pos_no)))
                splits = []
                break
        if qty_todo > 0:
            errors.append(_('File excesses qty on stock operations by %s'
                            ' for product %s') %
                          (qty_todo, product.default_code))
        return splits
