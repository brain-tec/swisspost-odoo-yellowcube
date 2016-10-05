# -*- coding: utf-8 -*-
##############################################################################
#
#    Copyright (c) 2016 brain-tec AG (http://www.braintec-group.com)
#    All Right Reserved
#
#    See LICENSE file for full licensing details.
##############################################################################
from . import test_base
from openerp.addons.stock_connector_yellowcube.models\
    import xml_tools
import logging
_logger = logging.getLogger(__name__)


class TestWabWarFile(test_base.TestBase):

    def runTest(self):
        return super(TestWabWarFile, self).runTest()

    def setUp(self):
        super(TestWabWarFile, self).setUp()
        # First we create a picking, and confirm it
        self.picking = self.env['stock.picking'].create({
            'partner_id': self.ref('base.res_partner_address_4'),
            'picking_type_id': self.ref('stock.picking_type_out'),
            'location_id': self.ref('stock.stock_location_stock'),
            'location_dest_id': self.ref('stock.stock_location_customers'),
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

    def test_create_wab_and_war_files(self):
        _logger.info('Creating WAB file')

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
        proc.yc_create_wab_file(event)
        self.assertEqual(len(self.backend.file_ids), 1)
        self.assertEqual(self.backend.file_ids[0].transmit, 'out')

        # Now, we will create a war file from the wab file
        _logger.info('Creating WAR file')
        wab_content = self.backend.file_ids[-1].content
        war_content = self.create_war_from_wab(wab_content)

        # Now, we save the file, and process it
        war_file = self.env['stock_connector.file'].create({
            'name': 'file.xml',
            'backend_id': self.backend.id,
            'content': war_content
        })
        proc.processors['WAR'](proc, war_file)
        self.assertEquals(war_file.state, 'done',
                          self.backend.output_for_debug)
        self.assertIn(self.picking.id,
                      [x.res_id
                       for x in war_file.child_ids
                       if x.res_model == 'stock.picking'])
        self.assertEquals(self.picking.state, 'done')
        for move in self.picking.pack_operation_product_ids:
            self.assertEquals(move.state, 'done')

    def create_war_from_wab(self, wab_content):
        processor = self.backend.get_processor()
        tools = xml_tools.XmlTools(_type='war')
        create = tools.create_element
        path = tools.nspath
        wab = tools.open_xml(wab_content, _type='wab')
        order_date = path(wab, '//wab:CustomerOrderDate')[0].text
        order_no = path(wab, '//wab:CustomerOrderNo')[0].text
        war_root = create('WAR')
        war_root.append(processor.yc_create_control_reference(tools,
                                                              'WAR',
                                                              '1.2'))
        path(war_root, '//war:Sender')[0].text = 'YELLOWCUBE'
        path(war_root, '//war:Receiver')[0].text = 'YCTest'
        war_issue = create('GoodsIssue')
        war_root.append(war_issue)
        war_issue_header = create('GoodsIssueHeader')
        war_issue_header.append(create('BookingVoucherID'))
        war_issue_header.append(create('BookingVoucherYear', order_date[:4]))
        war_issue_header.append(create('DepositorNo', '6666666'))
        war_issue.append(war_issue_header)
        war_customer_header = create('CustomerOrderHeader')
        war_customer_header.append(create('YCDeliveryNo', order_no))
        war_customer_header.append(create('YCDeliveryDate', order_date))
        war_customer_header.append(create('CustomerOrderNo', order_no))
        war_customer_header.append(create('CustomerOrderDate', order_date))
        war_customer_header.append(create('PostalShipmentNo'))
        war_issue.append(war_customer_header)
        war_customer_list = create('CustomerOrderList')
        war_issue.append(war_customer_list)
        bvposno = 0
        for wab_line in path(wab, '//wab:Position'):
            bvposno += 1
            war_line = create('CustomerOrderDetail')
            war_customer_list.append(war_line)
            war_line.append(create('BVPosNo', bvposno))
            war_line.append(create('CustomerOrderPosNo',
                                   path(wab_line, 'wab:PosNo')[0].text))
            war_line.append(create('YCArticleNo',
                                   path(wab_line, 'wab:ArticleNo')[0].text))
            war_line.append(create('Plant'))
            war_line.append(create('StorageLocation', 'YAFS'))
            war_line.append(create('TransactionType', '601'))
            war_line.append(create('StockType', 'F'))
            war_line.append(create('QuantityUOM',
                                   path(wab_line, 'wab:Quantity')[0].text,
                                   attrib={
                                       'QuantityISO': path(
                                           wab_line,
                                           'wab:QuantityISO')[0].text}))

        # We check that the XSD is OK
        self.assertEquals(tools.validate_xml(war_root), None)
        war_content = tools.xml_to_string(war_root)
        return war_content
