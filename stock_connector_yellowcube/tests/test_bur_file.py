# -*- coding: utf-8 -*-
##############################################################################
#
#    Copyright (c) 2016 brain-tec AG (http://www.braintec-group.com)
#    All Right Reserved
#
#    See LICENSE file for full licensing details.
##############################################################################
from . import test_base
from openerp.addons.stock_connector_yellowcube.models \
    import xml_tools
import logging
_logger = logging.getLogger(__name__)


class TestBurFile(test_base.TestBase):

    def runTest(self):
        return super(TestBurFile, self).runTest()

    def setUp(self):
        super(TestBurFile, self).setUp()
        get_binding = self.backend.get_binding
        get_binding(self.browse_ref('stock.stock_location_stock'),
                    'StorageLocation',
                    'destination.0')
        get_binding(self.browse_ref('stock.stock_location_company'),
                    'StorageLocation',
                    'YROD')

    def test_import_bur_file_without_lots(self):
        return self.test_import_bur_file(ignore_lots=True)

    def test_import_bur_file(self, ignore_lots=False):
        _logger.info('Creating BUR file')

        self.env['stock.config.settings'].create({
            'group_stock_production_lot': 0 if ignore_lots else 1
        }).execute()

        products = [
            # (product, bind_yc_ArtcileNo, lot)
            {
                'product': self.browse_ref('product.product_product_7'),
                'create_binding': True,
                'lot': 'lot123',
                'qty': 10,
            },
            {
                'product': self.browse_ref('product.product_product_9'),
                'create_binding': False,
                'lot': None,
                'qty': 10,
            },
        ]

        bur_content = self.create_bur_file(products)

        # Now, we save the file, and process it
        bur_file = self.env['stock_connector.file'].create({
            'name': 'file.xml',
            'backend_id': self.backend.id,
            'content': bur_content
        })
        # Here, we check the file is imported
        proc = self.backend.get_processor()
        proc.processors['BUR'](proc, bur_file)
        self.assertEquals(bur_file.state, 'done',
                          self.backend.output_for_debug)
        self.assertItemsEqual(
            map(lambda x: x['product'].id, products),
            bur_file.child_ids.filtered(
                lambda x: x.res_model == 'product.product'
            ).mapped('res_id')
            # 'All products have been used'
        )
        self.assertItemsEqual(
            map(lambda x: (
                x['product'].id,
                float(x['qty']),
                None if ignore_lots else x['lot'],
            ), products),
            bur_file.child_ids.filtered(
                lambda x: x.res_model == 'stock.move'
            ).mapped(
                lambda x: x.get_record()
            ).mapped(
                lambda x: (
                    x.product_id.id,
                    float(x.product_uom_qty),
                    x.restrict_lot_id.name if x.restrict_lot_id else None,
                )
            ),
            bur_file.info
            # 'All products have been processed'
        )

    def create_bur_file(self, products):
        processor = self.backend.get_processor()
        tools = xml_tools.XmlTools(_type='bur')
        create = tools.create_element
        get_binding = self.backend.get_binding
        bur_root = create('BUR')
        bur_root.append(processor.yc_create_control_reference(
            tools, 'BUR', '1.0'))
        tools.nspath(bur_root, '//bur:Sender')[0].text = 'YELLOWCUBE'
        tools.nspath(bur_root, '//bur:Receiver')[0].text = 'YCTest'
        bur_move = create('GoodsMovements')
        bur_root.append(bur_move)
        bur_header = create('GoodsMovementsHeader')
        bur_header.append(create('BookingVoucherID'))
        bur_header.append(create('BookingVoucherYear', '2016'))
        bur_header.append(create('DepositorNo', '0000010324'))
        bur_move.append(bur_header)
        bur_list = create('BookingList')
        bur_move.append(bur_list)
        idx = 0
        for line in products:
            product = line['product']
            bind_yc_article_no = line['create_binding']
            lot = line['lot']

            idx += 1
            if bind_yc_article_no:
                yc_article_no = get_binding(product,
                                            'YCArticleNo',
                                            product.default_code)
            else:
                yc_article_no = product.default_code
            bur_detail = create('BookingDetail')
            bur_detail.append(create('BVPosNo', idx))
            bur_detail.append(create('YCArticleNo', yc_article_no))
            if not bind_yc_article_no:
                bur_detail.append(create('ArticleNo', product.default_code))
            bur_detail.append(create('Plant'))
            bur_detail.append(create('StorageLocation',
                                     line.get('location', 'YROD')))
            if 'dest_location' in line:
                bur_detail.append(create('MoveStorageLocation',
                                         line['dest_location']))
            if lot:
                bur_detail.append(create('Lot', lot))
            bur_detail.append(create('TransactionType', 000))
            bur_detail.append(create('StockType'))
            bur_detail.append(create('QuantityUOM', line['qty'],
                                     {'QuantityISO': 'PCE'}))

            bur_list.append(bur_detail)

        # We check that the XSD is OK
        self.assertEquals(tools.validate_xml(bur_root), None)
        bur_content = tools.xml_to_string(bur_root)
        return bur_content
