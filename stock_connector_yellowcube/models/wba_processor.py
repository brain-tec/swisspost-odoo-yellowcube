# -*- coding: utf-8 -*-
##############################################################################
#
#    Copyright (c) 2016 brain-tec AG (http://www.braintec-group.com)
#    All Right Reserved
#
#    See LICENSE file for full licensing details.
##############################################################################
from openerp.tools.translate import _
from .file_processor import FileProcessor, WBL_WBA_ORDERNO_GROUP
from .xml_tools import Dict2Object


class WbaProcessor(FileProcessor):
    """
    This class reads a wba file from Yellowcube

    Version: 1.4
    """
    def __init__(self, backend):
        super(WbaProcessor, self).__init__(backend, 'wba')

    def yc_read_wba_file(self, wba_file):
        wba_file.info = ''
        self.log_message(
            'Reading WBA file {0}\n'.format(wba_file.name),
            file_record=wba_file,
            timestamp=True)

        errors = []
        all_wba_ctx = []
        try:
            for wba in self.path(self.tools.open_xml(wba_file.content,
                                                     _type='wba'),
                                 '//wba:WBA'):
                # Context object
                wba_ctx = Dict2Object()
                all_wba_ctx.append(wba_ctx)
                # Global File parameters
                wba_ctx.errors = errors
                wba_ctx.related_ids = []
                wba_ctx.file = wba_file
                # Node specific parameters
                wba_ctx.splits = []
                wba_ctx.xml = wba
                wba_ctx.ignore_posno = False
                wba_ctx.stop = False

                order_no = self.path(wba, '//wba:SupplierOrderNo')[0].text
                wba_ctx.order_no = order_no
                picking = self.find_binding(order_no,
                                            WBL_WBA_ORDERNO_GROUP).record
                if not picking:
                    errors.append(_('Cannot find binding'
                                    'for order {0}').format(order_no))
                    continue
                else:
                    wba_ctx.picking = picking

                for wba_line in self.path(wba, '//wba:GoodsReceiptDetail'):
                    self.yc_read_wba_line(wba_ctx, wba_line)
        except Exception as e:
            errors.append(self.tools.format_exception(e))

        if errors:
            wba_file.state = 'error'
            self.log_message(
                'WBA file errors:\n{0}\n'.format('\n'.join(errors)),
                file_record=wba_file)
        else:
            for wba_ctx in all_wba_ctx:
                self.yc_process_wba_split(
                    wba_ctx.picking,
                    wba_ctx.related_ids,
                    wba_ctx.splits)
                related = ('stock.picking', picking.id)
                if related not in wba_ctx.related_ids:
                    wba_ctx.related_ids.append(related)
            wba_file.state = 'done'
            wba_file.child_ids = [(0, 0, {'res_model': x[0], 'res_id': x[1]})
                                  for x in wba_ctx.related_ids]
            self.log_message('WBA file processed\n', file_record=wba_file)

    def yc_process_wba_split(self, picking, related_ids, splits):
        """
        :param picking:
        :param list related_ids:
        :param dict splits:
        :return:
        """
        for split in splits:
            operation = split['operation']
            related = ('stock.pack.operation', operation.id)
            if related not in related_ids:
                related_ids.append(related)
            operation.qty_done += split['qty']
        picking.do_recompute_remaining_quantities()
        if all(picking.pack_operation_product_ids.mapped(
            lambda x: x.product_qty == x.qty_done
        )):
            picking.action_done()

    def yc_read_wba_line(self, wba_ctx, wba_line):
        """
        :param lxml.etree._ElementTree._ElementTree wba_line:
        :return: list of split dict
        """
        errors = wba_ctx.errors
        order_no = wba_ctx.order_no

        pos_no = self.path(wba_line,
                           'wba:SupplierOrderPosNo')[0].text
        pack = self.find_binding(int(pos_no),
                                 'SupplierOrderNo{0}'.format(order_no)).record
        if pack:
            product = pack.product_id
            qty_uom = self.path(wba_line, 'wba:QuantityUOM')[0]
            qty_todo = float(qty_uom.text or 0)
        else:
            errors.append(_('Cannot find binding for moves for operation {0}'
                            ' of order {1}').format(pos_no,
                                                    order_no))
            return []

        return self.create_splits_from_line(wba_ctx, pos_no, product, qty_todo,
                                            qty_uom)

    def create_splits_from_line(self, wba_ctx, pos_no, product, qty_todo,
                                qty_uom):
        errors = wba_ctx.errors
        splits = wba_ctx.splits
        picking = wba_ctx.picking

        operations = picking.pack_operation_product_ids.filtered(
            lambda x: (
                x.product_id == product
            )
        )
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
                max(0, operation.product_qty - split['qty'])
            )
            qty_todo -= qty
            split['qty'] += qty
            uom_code = operation.product_uom_id.iso_code
            if uom_code != qty_uom.get('QuantityISO'):
                errors.append(_('Move {0} differ'
                                'in ISO code'.format(pos_no)))
                break
        if qty_todo > 0:
            errors.append(_('File excesses qty on stock moves by %s'
                            ' for product %s') %
                          (qty_todo, product.default_code))
        return splits
