# -*- coding: utf-8 -*-
##############################################################################
#
#    Copyright (c) 2016 brain-tec AG (http://www.braintec-group.com)
#    All Right Reserved
#
#    See LICENSE file for full licensing details.
##############################################################################
from openerp.tools.translate import _
from .file_processor import FileProcessor
from .xml_tools import Dict2Object


class BurProcessor(FileProcessor):
    """
    This class reads a bur file from Yellowcube

    Version: 1.0
    """

    def __init__(self, backend):
        super(BurProcessor, self).__init__(backend, 'bur')

    def yc_read_bur_file(self, bur_file):
        """
        :param openerp.osv.orm.browse_record bur_file:
        """
        bur_file.info = ''
        self.log_message(
            'Reading BUR file {0}\n'.format(bur_file.name),
            file_record=bur_file,
            timestamp=True)
        if not self.validate_file(bur_file):
            return

        errors = []
        info = []
        related_ids = []
        moves_to_do = []
        bindings_to_do = {}
        lot_map = {}
        ignore_lots = False
        if self.env['stock.config.settings'].default_get(
                ['group_stock_production_lot']
        )['group_stock_production_lot'] == 0:
            ignore_lots = True
        try:
            for bur_move in self.path(self.tools.open_xml(bur_file.content,
                                                          _type='bur'),
                                      '//bur:BookingDetail'):
                bur_ctx = Dict2Object()
                # Common values
                bur_ctx.errors = errors
                bur_ctx.info = info
                bur_ctx.related_ids = related_ids
                bur_ctx.moves_to_do = moves_to_do
                bur_ctx.bindings_to_do = bindings_to_do
                bur_ctx.lot_map = lot_map
                bur_ctx.file = bur_file
                bur_ctx.ignore_lots = ignore_lots
                # Node values
                bur_ctx.xml = bur_move

                move_to_do = self.yc_read_bur_move(bur_ctx)
                if move_to_do is None:
                    continue
                bur_ctx.moves_to_do.append(move_to_do)
                related_key = ('product.product', move_to_do['product_id'])
                if related_key not in bur_ctx.related_ids:
                    bur_ctx.related_ids.append(related_key)

        except Exception as e:
            errors.append(self.tools.format_exception(e))

        if len(moves_to_do) == 0:
            errors.append(_('There are no move in this file'))

        if errors:
            bur_file.state = 'error'
            self.log_message(
                'BUR file errors:\n{0}\n'.format('\n'.join(errors)),
                file_record=bur_file)
        else:
            for move_to_do in moves_to_do:
                self.yc_process_bur_move(lot_map, move_to_do, related_ids)
            bur_file.state = 'done'
            bur_file.write({'child_ids': [
                (0, 0, {'res_model': x, 'res_id': y}) for x, y in related_ids
            ]})
            for msg in info:
                self.log_message('%s\n' % msg, file_record=bur_file)
            self.log_message('BUR file processed\n', file_record=bur_file)

    def yc_process_bur_move(self, lot_map, move_to_do, related_ids):
        """
        Process a BUR move, and makes any change on the DB
        :param dict lot_map: lots that need to be found and/or created
        :param dict move_to_do: move that needs to be done
        :param dict related_ids: elements that are touched by this BUR
        """
        if 'restrict_lot_id' in move_to_do:
            lot_name = move_to_do['restrict_lot_id']
            if lot_map[lot_name] is None:
                lot = self.env['stock.production.lot'].search([
                    ('name', '=', lot_name),
                    ('product_id', '=', move_to_do['product_id'])
                ], limit=1)
                if not lot:
                    lot = self.env['stock.production.lot'].create({
                        'name': lot_name,
                        'product_id': move_to_do['product_id'],
                    })
                move_to_do['restrict_lot_id'] = lot_map[lot_name] = lot.id
            else:
                move_to_do['restrict_lot_id'] = lot_map[lot_name]
        move = self.env['stock.move'].create(move_to_do)
        move.action_done()
        related_ids.append(('stock.move', move.id))

    def yc_read_bur_move(self, bur_ctx):
        """
        Read a BUR node, and extract the information needed later for the move

        bindings_to_do: bindings that are missing for products
        bur_move: move to read
        errors: list of errors found
        lot_map: lots to be found and/or created later
        bur_file: Original BUR file record
        :return:
        """
        bur_move = bur_ctx.xml
        bur_file = bur_ctx.file
        errors = bur_ctx.errors
        bindings_to_do = bur_ctx.bindings_to_do
        lot_map = bur_ctx.lot_map

        move_to_do = {}
        bvposno = self.path(bur_move, 'bur:BVPosNo')[0].text
        move_to_do['name'] = '#'.join([
            bur_file.name,
            bvposno
        ])
        yc_article_no = self.path(bur_move, 'bur:YCArticleNo')[0].text
        product_binding = self.find_binding(yc_article_no, 'YCArticleNo')
        # Check the product is registered on the system
        if product_binding:
            product = product_binding.record
        else:
            article_no = self.path(bur_move, 'bur:ArticleNo')
            if not article_no:
                errors.append(_('Impossible to find product binding '
                                '{0}').format(yc_article_no))
                return None
            product = self.env['product.product'].search(
                [('default_code', '=', article_no[0].text)],
                limit=1
            )
            if not product:
                errors.append(_('Impossible to find product code '
                                '{0}').format(yc_article_no))
                return None
            if bindings_to_do.get(yc_article_no, product) != product:
                errors.append(_('Binding {0} is duplicated')
                              .format(yc_article_no))
                return None
            bindings_to_do[yc_article_no] = product
        move_to_do['product_id'] = product.id
        # Find the location to use
        yc_stocktype = self.path(bur_move, 'bur:StockType')[0].text
        if yc_stocktype is None:
            yc_stocktype = '0'
        yc_source_loc = self.path(bur_move, 'bur:StorageLocation')[0].text
        yc_destination_loc = self.path(bur_move, 'bur:MoveStorageLocation')
        if yc_destination_loc:
            yc_destination_loc = yc_destination_loc[0].text
        else:
            yc_destination_loc = 'destination.{0}' \
                .format(yc_stocktype)
        source_loc_binding = self.find_binding(yc_source_loc,
                                               'StorageLocation')
        if source_loc_binding is None:
            errors.append(_('Unknown location {0}')
                          .format(yc_source_loc))
            return None
        dest_loc_binding = self.find_binding(yc_destination_loc,
                                             'StorageLocation')
        if dest_loc_binding is None:
            errors.append(_('Unknown location {0}')
                          .format(yc_destination_loc))
            return None
        move_to_do['location_id'] = source_loc_binding.res_id
        move_to_do['location_dest_id'] = dest_loc_binding.res_id
        quantity = self.path(bur_move, 'bur:QuantityUOM')[0]
        move_to_do['product_uom_qty'] = float(quantity.text or 0)
        move_to_do['product_uom'] = product.uom_id.id
        if product.uom_id.iso_code != quantity.get('QuantityISO'):
            errors.append(_('Distinct UOM for {0}')
                          .format(yc_article_no))
            return None
        lot = self.path(bur_move, 'bur:Lot')
        if lot and not bur_ctx.ignore_lots:
            lot = lot[0].text
            move_to_do['restrict_lot_id'] = lot
            if lot not in lot_map:
                lot_map[lot] = None
        elif lot and bur_ctx.ignore_lots:
            bur_ctx.info.append('WARNING: Lots are ignored!')
        return move_to_do
