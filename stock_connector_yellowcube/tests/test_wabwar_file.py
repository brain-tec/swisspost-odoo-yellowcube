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
        # First, we set-up the different records
        self.backend.get_binding(
            self.browse_ref('delivery.delivery_carrier'),
            'BasicShippingServices',
            'PRI',
        )
        return_location = self.browse_ref('stock.stock_location_stock').copy({
            'name': 'Returned Stock',
            'return_location': True,
        })
        picking_type = self.browse_ref('stock.picking_type_out')
        picking_ret_type = picking_type.return_picking_type_id.copy({
            'name': 'Return of goods',
            'default_location_dest_id': return_location.id,
        })
        picking_type.return_picking_type_id = picking_ret_type
        picking_type.return_type_id = self\
            .ref('stock_connector_yellowcube.yc_stock_picking_return_type_r01')
        # Now we create a picking, and confirm it
        self._change_product_qty(self.ref('product.product_product_7'),
                                 100, check=False)
        self._change_product_qty(self.ref('product.product_product_9'),
                                 100, check=False)
        self.sale = self.env['sale.order'].sudo(self.user).create({
            'partner_id': self.partner_customer.id,
            'order_line': [
                (0, 0, {'name': 'product_product_7',
                        'product_id': self.ref('product.product_product_7'),
                        'product_uom_qty': 100,
                        'product_uom': self.ref('product.product_uom_unit'),
                        }),
                (0, 0, {'name': 'product_product_9',
                        'product_id': self.ref('product.product_product_9'),
                        'product_uom_qty': 100,
                        'product_uom': self.ref('product.product_uom_unit'),
                        }),
            ],
        })
        self.sale.action_confirm()
        self.picking = self.sale.picking_ids[0]
        self.picking.write({
            'picking_type_id': picking_type.id,
            'location_id': self.ref('stock.stock_location_stock'),
            'location_dest_id': self.ref('stock.stock_location_customers'),
            'carrier_id': self.ref('delivery.delivery_carrier')
        })
        self.picking.action_confirm()
        self.picking.sudo().action_assign()

    def test_create_wab_and_war_files_by_sale_corfirmation(self):
        self.test_create_wab_and_war_files(True)

    def test_create_wab_and_war_files(self, confirm_sale=False):
        _logger.info('Creating WAB file')

        # At beginning, it must be empty
        self.assertEqual(len(self.backend.file_ids), 0)

        # We find the event
        picking_to_process = self.picking
        if confirm_sale:
            self.assertEqual(len(self.backend.file_ids), 0)
            self.backend.yc_parameter_autoprocess_picking_events = True
            self.assertEqual(len(self.backend.file_ids), 0)
            self.assertNotEquals(self.sale.state, 'done')
            self.sale.action_done()
            self.assertEqual(self.sale.state, 'done')
        else:
            _logger.debug('Processing picking')
            self.create_wab_from_picking(picking_to_process)
        self.assertEqual(len(self.backend.file_ids), 1,
                         self.backend.output_for_debug)
        wab_file = self.backend.file_ids[-1]
        self.assertEqual(wab_file.transmit, 'out')
        self.assertIn(picking_to_process.id,
                      [x.res_id
                       for x in wab_file.child_ids
                       if x.res_model == 'stock.picking'])

        # Now, we will create a war file from the wab file
        _logger.info('Creating WAR file')
        wab_content = wab_file.content
        war_content = self.create_war_from_wab(wab_content)

        # Now, we save the file, and process it
        war_file = self.env['stock_connector.file'].create({
            'name': 'file.xml',
            'backend_id': self.backend.id,
            'content': war_content
        })
        proc = self.backend.get_processor()
        proc.processors['WAR'](proc, war_file)
        self.assertEquals(war_file.state, 'done',
                          self.backend.output_for_debug)
        self.assertIn(picking_to_process.id,
                      [x.res_id
                       for x in war_file.child_ids
                       if x.res_model == 'stock.picking'],
                      self.backend.output_for_debug)
        self.assertEquals(picking_to_process.state, 'done',
                          self.backend.output_for_debug)
        for move in picking_to_process.pack_operation_product_ids:
            self.assertEquals(move.state, 'done')

        # After the picking is processed, we check a return can be made
        return_obj = self.env['stock.return.picking'].sudo(self.user)
        return_vals = return_obj.with_context(
            {'active_id': self.picking.id, }).default_get(
            ['product_return_moves'])
        return_wiz = return_obj.create(return_vals)
        return_pick_id, return_pick_type_id = \
            return_wiz.with_context({
                'active_id': self.picking.id,
            })._create_returns()
        return_pick = self.env['stock.picking'].sudo(self.user)\
            .browse(return_pick_id)
        return_pick.action_confirm()
        return_pick.force_assign()
        new_event = self.create_wab_from_picking(return_pick)
        self.assertEqual(new_event.state, 'done',
                         self.backend.output_for_debug)
        last_file = self.backend.file_ids[-1]
        self.assertEqual(last_file.transmit, 'out')
        self.assertIn('ReturnReason>R01<', last_file.content)

    def create_wab_from_picking(self, picking_to_process):
        proc = self.backend.get_processor()
        self.assertNotEquals(picking_to_process.state, 'draft')
        event = self.env['stock_connector.event'].search([
            ('res_id', '=', picking_to_process.id),
            ('res_model', '=', 'stock.picking'),
            ('code', '=', 'stock.picking_state_assigned'),
        ], limit=1)
        self.assertEqual(len(event), 1)
        if event.state != 'done':
            proc.yc_create_wab_file(event)
        return event

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
            posno = path(wab_line, 'wab:PosNo')[0].text
            war_line.append(create('CustomerOrderPosNo',
                                   '%06d' % int(posno)))
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

    def _change_product_qty(self, product_id, qty, check=True,
                            location_id=None):
        if location_id is None:
            location_id = self.ref('stock.stock_location_stock')
        self.env['stock.change.product.qty'].create({
            'product_id': product_id,
            'new_quantity': qty,
            'location_id': location_id
        }).change_product_qty()
        if check:
            product = self.env['product.product'].with_context(
                {'location': location_id})\
                .browse(product_id)
            self.assertEquals(
                qty,
                product._product_available()[product_id]['qty_available'],
                product.default_code
            )
