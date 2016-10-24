# b-*- encoding: utf-8 -*-
##############################################################################
#
#    Copyright (c) 2015 brain-tec AG (http://www.brain-tec.ch)
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
from openerp.osv import osv, fields
from openerp.tools.translate import _
from openerp.tests import common
from ..xml_abstract_factory import get_factory
from datetime import datetime
from ..xsd.xml_tools import nspath, create_root, create_element, xml_to_string, schema_namespaces, _str
import unittest2
import re
from lxml import etree
from urllib import urlopen
import os
from openerp.addons.report_webkit.webkit_report import WebKitParser
from openerp import SUPERUSER_ID
import base64
import traceback
import logging
logger = logging.getLogger(__name__)

_test_timestamp = datetime.today().strftime('%Y%m%d%H%M%S')


MINIMALIST_PDF = """%PDF-1.1
%¥±ë

1 0 obj
  << /Type /Catalog
     /Pages 2 0 R
  >>
endobj

2 0 obj
  << /Type /Pages
     /Kids [3 0 R]
     /Count 1
     /MediaBox [0 0 300 144]
  >>
endobj

3 0 obj
  <<  /Type /Page
      /Parent 2 0 R
      /Resources
       << /Font
           << /F1
               << /Type /Font
                  /Subtype /Type1
                  /BaseFont /Times-Roman
               >>
           >>
       >>
      /Contents 4 0 R
  >>
endobj

4 0 obj
  << /Length 55 >>
stream
  BT
    /F1 18 Tf
    0 0 Td
    ({0}) Tj
  ET
endstream
endobj

xref
0 5
0000000000 65535 f
0000000018 00000 n
0000000077 00000 n
0000000178 00000 n
0000000457 00000 n
trailer
  <<  /Root 1 0 R
      /Size 5
  >>
startxref
565
%%EOF"""


def subTest(name, subname, *args, **kargs):
    def __deco(c):
        def __f(self):
            params_str = ''
            for a in args:
                params_str = '{0}, {1}'.format(params_str, a) if params_str else a
            for k in kargs:
                a = kargs[k]
                params_str = '{0}, {1}={2}'.format(params_str, k, a) if params_str else '{0}={1}'.format(k, a)
            logger.debug("Invoking {0}({1})".format(name, params_str))
            return getattr(c, name)(self, params_str)
        skip_test = kargs.get('skip_test', False)
        if skip_test:
            setattr(c, 'test_{0}_{1}'.format(name, subname), unittest2.skip(skip_test)(__f))
        else:
            setattr(c, 'test_{0}_{1}'.format(name, subname), __f)
        return c
    return __deco


class yellowcube_testcase(common.TransactionCase):

    _last_file_id = 0

    def setUp(self):
        super(yellowcube_testcase, self).setUp()

        cr = self.cr
        uid = self.uid
        ctx = self.context = {
            'show_errors': True,
            'stock_connect_id': self.ref('pc_connect_warehouse_yellowcube.demo_connection_yc'),
            'warehouse_id': self.ref('pc_connect_warehouse_yellowcube.warehouse_YC'),
        }

        self.browse_ref('pc_connect_warehouse_yellowcube.demo_connection_yc').write({
            'type': 'yellowcube',
            'connect_transport_id': self.ref('pc_connect_warehouse_yellowcube.fds_dummy_connection'),
            'yc_enable_art_file': False,
            'yc_enable_art_multifile': False,
            'yc_attachments_from_invoice': 10,
            'yc_attachments_from_picking': 10,
        })

        self.output_dir = '/tmp/test_yc_{0}'.format(_test_timestamp)
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)
        if os.path.exists('/tmp/test_yc_last'):
            os.unlink('/tmp/test_yc_last')

        os.symlink(self.output_dir, '/tmp/test_yc_last')

        # Objects and references
        self.product_obj = self.registry('product.product')
        self.pick_obj = self.registry('stock.picking')
        self.pick_type_obj = self.registry('stock.picking.type')
        self.pick_ret_obj = self.registry('stock.return.picking')
        self.purchase_obj = self.registry('purchase.order')
        self.sale_obj = self.registry('sale.order')
        self.invoice_obj = self.registry('account.invoice')
        self.att_obj = self.registry('ir.attachment')
        self.stock_connect_file = self.registry('stock.connect.file')

        self.registry['ir.config_parameter']\
            .set_param(cr, SUPERUSER_ID, 'ir_attachment.location', 'file')
        self._last_file_id = (self.stock_connect_file.search(cr, uid, [], order='id DESC', limit=1) or [0])[0]

        self.configuration = self.registry('configuration.data').get(cr, uid, [], context=ctx)
        self.test_warehouse = self.browse_ref('pc_connect_warehouse_yellowcube.warehouse_YC')
        self.test_sale = self.browse_ref('pc_connect_warehouse_yellowcube.yc_sale_order_4')
        self.test_delivery_method = self.browse_ref('pc_connect_warehouse_yellowcube.yc_delivery_test')

        # sale.order
        # Now we change some data of the partner on purpose to check language
        partner_new_data = {
            'lastname': u'wëÏrd',
            'firstname': u'ñämëç',
            'city': u'WËïrdëst ÇïtY',
        }
        self.test_sale.partner_id.write(partner_new_data)
        self.test_sale.partner_invoice_id.write(partner_new_data)
        self.test_sale.partner_shipping_id.write(partner_new_data)
        # cr.execute('delete from wkf_instance where res_id=%s and res_type=%s', (self.test_sale.id, 'sale.order'))
        self.browse_ref('sale.trans_draft_sent').write({'condition': 'True'})
        self.browse_ref('sale.trans_draft_router').write({'condition': 'True'})
        self.test_sale.write({'carrier_id': self.test_delivery_method.id})
        self.test_sale.action_button_confirm()
        # Make the delivery use the YC test warehouse
        for pick in self.test_sale.picking_ids:
            for line in pick.move_lines:
                line.write({'location_id': self.test_warehouse.lot_stock_id.id})
            if pick.state == 'draft':
                pick.action_confirm()
                pick.force_assign()
            elif pick.state == 'waiting':
                pick.force_assign()
            self.att_obj.create(cr, uid, {
                'name': 'hello',
                'res_id': pick.id,
                'res_model': 'stock.picking',
                'datas': base64.b64encode(MINIMALIST_PDF.format('Hello world')),
            }, context=ctx)
            self.att_obj.create(cr, uid, {
                'name': 'other',
                'res_id': pick.id,
                'res_model': 'stock.picking',
                'datas': base64.b64encode(MINIMALIST_PDF
                                          .format('Other Attachment')),
            }, context=ctx)

        for invoice in self.test_sale.invoice_ids:
            self.att_obj.create(cr, uid, {
                'name': 'hello',
                'res_id': invoice.id,
                'res_model': 'account.invoice',
                'datas': base64.b64encode(MINIMALIST_PDF.format('Hello world')),
            }, context=ctx)
            self.att_obj.create(cr, uid, {
                'name': 'other',
                'res_id': invoice.id,
                'res_model': 'account.invoice',
                'datas': base64.b64encode(MINIMALIST_PDF
                                          .format('Other Attachment')),
            }, context=ctx)

        # product.product
        if hasattr(self.product_obj, 'action_validated'):
            product_ids = self.product_obj.search(cr, uid, [], context=ctx)
            self.product_obj.write(cr, uid, product_ids, {
                'product_state': 'draft',
                'webshop_state': False,
                'target_state': 'active',
            }, context=ctx)

        picking_type_ids = self.pick_type_obj.search(cr, uid, [], context=ctx)
        self.pick_type_obj.write(cr, uid, picking_type_ids, {
            'warehouse_id': self.test_warehouse.id,
        }, context=ctx)

        self.att_obj.force_storage(cr, uid, context=ctx)


    def _print_sale_pdfs(self):
        self.test_sale.manual_invoice()['res_id']
        # self.assertNotEqual(self.test_sale.invoice_ids, [], 'There must be some invoices')
        for invoice_id in self.test_sale.invoice_ids:
            invoice_id.invoice_validate()
        logger.warning("Skipping print of invoices, as there is an issue with webkit on testing")
        self.context['yc_ignore_wab_reports'] = True
        self.context['yc_min_number_attachments'] = 0
        # self.sale_obj._print_invoice_in_local(self.cr, self.uid, self.test_sale.id, self.context)
        # self.sale_obj._print_deliveryorder_in_local(self.cr, self.uid, self.test_sale.id, self.context)

    def tearDown(self):
        super(yellowcube_testcase, self).tearDown()

    def _yc_files(self, pattern=None, _type=None):
        cr, uid, ctx = self.cr, self.uid, self.context
        file_ids = self.stock_connect_file.search(cr,
                                                  uid,
                                                  [('id', '>', self._last_file_id),
                                                   ('warehouse_id', '=', self.test_warehouse.id),
                                                   ('error', '!=', True)],
                                                  context=ctx)
        if _type:
            file_ids = self.stock_connect_file.search(cr, uid, [('id', 'in', file_ids), ('type', '=', _type)], context=ctx)
        ret = [x['name'] for x in self.stock_connect_file.read(self.cr, self.uid, file_ids, ['name'], context=self.context)]
        logger.debug("Files on stock.connect for this test: {0}".format(ret))
        if not pattern:
            return ret
        ret2 = [x for x in ret if re.match(pattern, x)]
        if not ret2:
            logger.debug("Pattern '{0}' not present on {1}".format(pattern, ret))
        return ret2

    def _get_file_node(self, file_name):
        file_id = self.stock_connect_file.search(self.cr, self.uid, [('name', '=', file_name)], context=self.context)
        return etree.XML(_str(self.stock_connect_file.browse(self.cr, self.uid, file_id, context=self.context)[0].content))

    def _create_mirror_war_from_wab(self, wab_node, returngoods=False):
        ns = schema_namespaces['warr']
        war_root = create_element('WAR', ns=ns)
        # BigHeader
        big_header = create_element('ControlReference', ns=ns)
        big_header.append(create_element('Type', 'WAR', ns=ns))
        big_header.append(create_element('Sender', 'YELLOWCUBE', ns=ns))
        big_header.append(create_element('Receiver', 'YCTest', ns=ns))
        big_header.append(create_element('Timestamp', nspath(wab_node, '//Timestamp')[0].text, ns=ns))
        big_header.append(create_element('OperatingMode', 'T', ns=ns))
        big_header.append(create_element('Version', '1.0', ns=ns))
        war_root.append(big_header)
        # GoodsIssueHeader
        goods_issue = create_element('GoodsIssue', ns=ns)
        war_root.append(goods_issue)
        goods_header = create_element('GoodsIssueHeader', ns=ns)
        goods_header.append(create_element('BookingVoucherID', '4900109771', ns=ns))
        goods_header.append(create_element('BookingVoucherYear', '2015', ns=ns))
        goods_header.append(create_element('DepositorNo', '0000010518', ns=ns))
        goods_issue.append(goods_header)
        # CustomerOrderHeader
        order_header = create_element('CustomerOrderHeader', ns=ns)
        order_header.append(create_element('YCDeliveryNo', '0410001201', ns=ns))
        order_header.append(create_element('YCDeliveryDate', '20150101', ns=ns))
        order_header.append(create_element('CustomerOrderNo', nspath(wab_node, '//CustomerOrderNo')[0].text, ns=ns))
        order_header.append(create_element('CustomerOrderDate', '20150101', ns=ns))
        order_header.append(create_element('PostalShipmentNo', '990012345612345678;', ns=ns))
        goods_issue.append(order_header)
        # CustomerOrderList
        order_list = create_element('CustomerOrderList', ns=ns)
        for line in nspath(wab_node, '//Position'):
            order_line = create_element('CustomerOrderDetail', ns=ns)
            order_line.append(create_element('BVPosNo', nspath(line, 'PosNo')[0].text, ns=ns))
            order_line.append(create_element('CustomerOrderPosNo', nspath(line, 'PosNo')[0].text, ns=ns))
            order_line.append(create_element('YCArticleNo', 'YC{0}'.format(nspath(line, 'ArticleNo')[0].text), ns=ns))
            order_line.append(create_element('Plant', 'Y005', ns=ns))
            order_line.append(create_element('StorageLocation', 'YROD' if returngoods else 'YAFS', ns=ns))
            order_line.append(create_element('TransactionType', '601', ns=ns))
            order_line.append(create_element('StockType', 'F', ns=ns))
            order_line.append(create_element('QuantityUOM',
                                             nspath(line, 'Quantity')[0].text,
                                             attrib={'QuantityISO': nspath(line, 'QuantityISO')[0].text},
                                             ns=ns))
            order_list.append(order_line)
        goods_issue.append(order_list)

        return war_root

    def _create_mirror_wba_from_wbl(self, wbl_node, returngoods=False, partial=None, end='1'):
        ns = schema_namespaces['wba']
        wba_root = create_element('WBA', ns=ns)
        # BigHeader
        big_header = create_element('ControlReference', ns=ns)
        big_header.append(create_element('Type', 'WBA', ns=ns))
        big_header.append(create_element('Sender', 'YellowCube', ns=ns))
        big_header.append(create_element('Receiver', 'YCTest', ns=ns))
        big_header.append(create_element('Timestamp', nspath(wbl_node, '//Timestamp')[0].text, ns=ns))
        big_header.append(create_element('OperatingMode', 'T', ns=ns))
        big_header.append(create_element('Version', '1.0', ns=ns))
        wba_root.append(big_header)
        # GoodsIssueHeader
        goods_receipt = create_element('GoodsReceipt', ns=ns)
        wba_root.append(goods_receipt)
        voucher_header = create_element('GoodsReceiptHeader', ns=ns)
        voucher_header.append(create_element('BookingVoucherID', '1234567890', ns=ns))
        voucher_header.append(create_element('BookingVoucherYear', '2013', ns=ns))
        voucher_header.append(create_element('SupplierNo', '0000200015', ns=ns))
        voucher_header.append(create_element('SupplierOrderNo', nspath(wbl_node, '//SupplierOrderNo')[0].text, ns=ns))
        goods_receipt.append(voucher_header)
        # CustomerOrderList
        order_list = create_element('GoodsReceiptList', ns=ns)
        for line in nspath(wbl_node, '//Position'):
            if partial and partial != int(nspath(line, 'PosNo')[0].text):
                continue
            order_line = create_element('GoodsReceiptDetail', ns=ns)
            order_line.append(create_element('BVPosNo', nspath(line, 'PosNo')[0].text, ns=ns))
            order_line.append(create_element('SupplierOrderPosNo', nspath(line, 'PosNo')[0].text, ns=ns))
            order_line.append(create_element('YCArticleNo', 'YC{0}'.format(nspath(line, 'ArticleNo')[0].text), ns=ns))
            order_line.append(create_element('Plant', 'Y005', ns=ns))
            order_line.append(create_element('StorageLocation', 'YROD' if not returngoods else 'YAFS', ns=ns))
            order_line.append(create_element('QuantityUOM',
                                             nspath(line, 'Quantity')[0].text,
                                             attrib={'QuantityISO': nspath(line, 'QuantityISO')[0].text},
                                             ns=ns))
            order_line.append(create_element('EndOfDeliveryFlag', end, ns=ns))
            order_list.append(order_line)
        goods_receipt.append(order_list)

        return wba_root

    def _save_node(self, node, _type, path, extra=''):
        node_id = nspath(node, path)[0].text
        name = '{0}/{1}_{2}_{3}{4}.xml'.format(self.output_dir,
                                               self.test_warehouse.stock_connect_id.yc_sender,
                                               _type,
                                               node_id,
                                               extra)
        f = open(name, 'w')
        f.write(xml_to_string(node).encode('utf-8'))

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
