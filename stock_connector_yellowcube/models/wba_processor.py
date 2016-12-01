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
        related_ids = []
        splits_to_do = []
        try:
            for wba in self.path(self.tools.open_xml(wba_file.content,
                                                     _type='wba'),
                                 '//wba:WBA'):
                splits = []
                order_no = self.path(wba, '//wba:SupplierOrderNo')[0].text
                picking = self.find_binding(order_no,
                                            WBL_WBA_ORDERNO_GROUP).record
                if not picking:
                    errors.append(_('Cannot find binding'
                                    'for order {0}').format(order_no))
                    continue
                splits_to_do.append((picking, splits))
                for wba_line in self.path(wba, '//wba:GoodsReceiptDetail'):
                    splits.extend(
                        self.yc_read_wba_line(errors, order_no, wba_line))
        except Exception as e:
            errors.append(self.tools.format_exception(e))

        if len(splits_to_do) == 0:
            errors.append(_('There are no moves in this file'))

        if errors:
            wba_file.state = 'error'
            self.log_message(
                'WBA file errors:\n{0}\n'.format('\n'.join(errors)),
                file_record=wba_file)
        else:
            for picking, splits in splits_to_do:
                self.yc_process_wba_split(picking, related_ids, splits)
                related = ('stock.picking', picking.id)
                if related not in related_ids:
                    related_ids.append(related)
            wba_file.state = 'done'
            wba_file.child_ids = [(0, 0, {'res_model': x[0], 'res_id': x[1]})
                                  for x in related_ids]
            self.log_message('WBA file processed\n', file_record=wba_file)

    def yc_process_wba_split(self, picking, related_ids, splits):
        """
        :param picking:
        :param list related_ids:
        :param dict splits:
        :return:
        """
        for split in splits:
            related = ('stock.move', split['move'].id)
            if related not in related_ids:
                related_ids.append(related)
            self.env['stock.move'].split(**split)
        picking.action_done()

    def yc_read_wba_line(self, errors, order_no, wba_line):
        """
        :param list errors:
        :param str order_no:
        :param lxml.etree._ElementTree._ElementTree wba_line:
        :return: list of split dict
        """
        pos_no = self.path(wba_line,
                           'wba:SupplierOrderPosNo')[0].text
        pack = self.find_binding(pos_no,
                                 'SupplierOrderNo{0}'.format(order_no)).record
        if pack:
            moves = pack.picking_id.move_lines.filtered(
                lambda x: (
                    x.product_id == pack.product_id and
                    x.state in ['confirmed', 'assigned']
                )
            )
        else:
            moves = None
        if not moves:
            errors.append(_('Cannot find binding for moves for operation {0}'
                            ' of order {1}').format(pos_no,
                                                    order_no))
            return []
        splits = []
        qty_uom = self.path(wba_line, 'wba:QuantityUOM')[0]
        qty_todo = float(qty_uom.text)
        for move in moves:
            if qty_todo == 0:
                break
            split = {
                'move': move,
            }
            splits.append(split)
            qty = min(qty_todo, move.product_uom_qty)
            qty_todo -= qty
            split['qty'] = qty
            uom_code = move.product_uom.iso_code
            if uom_code != qty_uom.get('QuantityISO'):
                errors.append(_('Move {0} differ'
                                'in ISO code'.format(pos_no)))
                return []
        if qty_todo > 0:
            errors.append(_('File excesses qty on stock moves by %s'
                            ' for product %s') % (
                qty_todo, pack.product_id.default_code))
        return splits
