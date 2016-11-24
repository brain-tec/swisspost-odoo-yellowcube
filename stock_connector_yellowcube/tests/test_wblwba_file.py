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


class TestWblWbaFile(test_base.TestBase):

    def runTest(self):
        return super(TestWblWbaFile, self).runTest()

    def setUp(self):
        super(TestWblWbaFile, self).setUp()
        # First we set a supplier
        self.backend.yc_parameter_default_supplier_no = 'partner{id}'
        # self.backend.get_binding(supplier, 'yc_SupplierNo', '0000200020')
        # Then we create a picking, and confirm it
        self.picking = self.env['stock.picking'].sudo(self.user).create({
            'partner_id': self.partner_customer.id,
            'picking_type_id': self.ref('stock.picking_type_in'),
            'location_id': self.ref('stock.stock_location_suppliers'),
            'location_dest_id': self.ref('stock.stock_location_stock'),
            'move_lines': [
                (0, 0, {'name': 'product_product_7',
                        'product_id': self.ref('product.product_product_7'),
                        'product_uom_qty': 1,
                        'product_uom': self.ref('product.product_uom_unit'),
                        }),
                (0, 0, {'name': 'product_product_9',
                        'product_id': self.ref('product.product_product_9'),
                        'product_uom_qty': 1,
                        'product_uom': self.ref('product.product_uom_unit'),
                        }),
            ],
        })
        self.picking.action_confirm()
        self.picking.force_assign()

    def test_create_wbl_wba_files(self):
        _logger.info('Creating WBL file')
        # At beginning, it must be empty
        self.assertEqual(len(self.backend.file_ids), 0)
        proc = self.backend.get_processor()
        # We find the event
        event = self.env['stock_connector.event'].search([
            ('res_id', '=', self.picking.id),
            ('res_model', '=', 'stock.picking'),
            ('code', '=', 'stock.picking_state_assigned'),
        ], limit=1)
        self.assertEqual(len(event), 1)
        proc.yc_create_wbl_file(event)
        self.assertEqual(len(self.backend.file_ids), 1)
        self.assertEqual(self.backend.file_ids[0].transmit, 'out')

        # Now, we will create a wba file from the wbl file
        _logger.info('Creating WBA file')
        wbl_content = self.backend.file_ids[-1].content

        wba_content = self.create_wba_from_wbl(wbl_content)

        # Now, we save the file, and process it
        wba_file = self.env['stock_connector.file'].create({
            'name': 'file.xml',
            'backend_id': self.backend.id,
            'content': wba_content
        })
        proc.processors['WBA'](proc, wba_file)
        self.assertEquals(wba_file.state, 'done',
                          self.backend.output_for_debug)
        self.assertIn(self.picking.id,
                      [x.res_id
                       for x in wba_file.child_ids
                       if x.res_model == 'stock.picking'])
        self.assertEquals(self.picking.state, 'done')
        for move in self.picking.pack_operation_product_ids:
            self.assertEquals(move.state, 'done')

    def create_wba_from_wbl(self, wbl_content):
        processor = self.backend.get_processor()
        tools = xml_tools.XmlTools(_type='wba')
        create = tools.create_element
        path = tools.nspath
        wbl = tools.open_xml(wbl_content, _type='wbl')
        order_date = path(wbl, '//wbl:SupplierOrderDate')[0].text
        order_no = path(wbl, '//wbl:SupplierOrderNo')[0].text
        wba_root = create('WBA')
        wba_root.append(processor.yc_create_control_reference(tools,
                                                              'WBA',
                                                              '1.2'))
        path(wba_root, '//wba:Sender')[0].text = 'YELLOWCUBE'
        path(wba_root, '//wba:Receiver')[0].text = 'YCTest'
        wba_receipt = create('GoodsReceipt')
        wba_root.append(wba_receipt)
        wba_receipt_header = create('GoodsReceiptHeader')
        wba_receipt_header.append(create('BookingVoucherID'))
        wba_receipt_header.append(create('BookingVoucherYear', order_date[:4]))
        wba_receipt_header.append(create('SupplierNo', '6666666'))
        wba_receipt_header.append(create('SupplierOrderNo', order_no))
        wba_receipt.append(wba_receipt_header)
        wba_Supplier_list = create('GoodsReceiptList')
        wba_receipt.append(wba_Supplier_list)
        bvposno = 0
        for wbl_line in path(wbl, '//wbl:Position'):
            bvposno += 1
            wba_line = create('GoodsReceiptDetail')
            wba_Supplier_list.append(wba_line)
            wba_line.append(create('BVPosNo', bvposno))
            wba_line.append(create('SupplierOrderPosNo',
                                   path(wbl_line, 'wbl:PosNo')[0].text))
            wba_line.append(create('YCArticleNo',
                                   path(wbl_line, 'wbl:ArticleNo')[0].text))
            wba_line.append(create('Plant'))
            wba_line.append(create('StorageLocation', 'YAFS'))
            wba_line.append(create('TransactionType', '601'))
            wba_line.append(create('StockType', 'F'))
            wba_line.append(create('QuantityUOM',
                                   path(wbl_line, 'wbl:Quantity')[0].text,
                                   attrib={'QuantityISO': path(
                                       wbl_line, 'wbl:QuantityISO')[0].text}))
            wba_line.append(create('EndOfDeliveryFlag'))

        # We check that the XSD is OK
        self.assertEquals(tools.validate_xml(wba_root), None)
        wba_content = tools.xml_to_string(wba_root)
        return wba_content
