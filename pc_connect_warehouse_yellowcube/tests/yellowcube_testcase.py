# b-*- encoding: utf-8 -*-
##############################################################################
#
#    Copyright (c) 2015 brain-tec AG (http://www.braintec-group.com)
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
from datetime import datetime
from ..xsd.xml_tools import _XmlTools as xml_tools
import unittest2
import re
from lxml import etree
import subprocess
from tempfile import mkstemp, mkdtemp
import os, time, socket
import logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


MAX_LOT_NAME_LEN = 15  # Comes from the XSD.
_test_timestamp = datetime.today().strftime('%Y%m%d%H%M%S')


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
            # 'yc_min_number_attachments': 2,
        }

        self.output_dir = '/tmp/test_yc_{0}'.format(_test_timestamp)
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)
        if os.path.exists('/tmp/test_yc_last'):
            os.unlink('/tmp/test_yc_last')

        os.symlink(self.output_dir, '/tmp/test_yc_last')

        # Objects and references
        self.product_obj = self.registry('product.product')
        self.pick_obj = self.registry('stock.picking')
        self.pick_ret_obj = self.registry('stock.return.picking')
        self.purchase_obj = self.registry('purchase.order')
        self.purchase_line_obj = self.registry('purchase.order.line')
        self.sale_obj = self.registry('sale.order')
        self.move_obj = self.registry('stock.move')
        self.invoice_obj = self.registry('account.invoice')
        self.connect_obj = self.registry('stock.connect')
        self.carrier_obj = self.registry('delivery.carrier')
        self.conf_obj = self.registry('configuration.data')
        self.mail_obj = self.registry('mail.mail')
        self.message_obj = self.registry('mail.message')

        self.stock_connect_file = self.registry('stock.connect.file')
        self._last_file_id = (self.stock_connect_file.search(cr, uid, [], order='id DESC', limit=1) or [0])[0]

        self.configuration = self.conf_obj.get(cr, uid, [], context=ctx)
        self.test_warehouse = self.browse_ref('pc_connect_warehouse_yellowcube.warehouse_YC')
        self.test_sale = self.browse_ref('pc_connect_warehouse_yellowcube.yc_sale_order_4')
        self.test_delivery_method = self.browse_ref('pc_connect_warehouse_yellowcube.yc_delivery_test')

        self.war_postal_shippment_no = '990012345612345678;'

        vals = {
            'type': 'yellowcube',
            'name': 'Yellowcube Test',
            'connect_transport_id': self.ref('pc_connect_warehouse_yellowcube'
                                             '.fds_dummy_connection'),
        }
        for field_name in self.connect_obj._columns:
            if field_name.startswith('yc_enable'):
                vals[field_name] = False
        self.test_warehouse.stock_connect_id.write(vals)

        sale_excp_obj = self.registry('sale.exception')
        sale_excp_obj.write(cr, uid, sale_excp_obj.search(cr, uid, []), {'active': False})

        # sale.order
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

    def prepare_test_fds_server(self):
        cr, uid, ctx = self.cr, self.uid, self.context
        parameter_obj = self.registry('ir.config_parameter')
        param_value = parameter_obj.get_param(cr, uid, 'test_fds_config')
        self.vals = {}
        fd, self._sftp_key_file = mkstemp(suffix='.key', prefix='sftpserver_test_key', dir='/tmp')
        self.tempdir = [mkdtemp(), mkdtemp(), mkdtemp()]
        if param_value:
            self.vals = eval(param_value)
            if self.vals.get('ignore', False):
                logger.warning("Ignoring FDS tests")
                return
            with open(self._sftp_key_file, 'w') as f:
                f.write('Hello World')
        else:
            os.unlink(self._sftp_key_file)
            subprocess.Popen(["ssh-keygen", "-f", self._sftp_key_file, "-t", "rsa", '-N', ""], stdout=subprocess.PIPE).wait()
            s = socket.socket()
            s.bind(('', 0))
            port = s.getsockname()[1]
            s.close()
            self._sftp_process = subprocess.Popen([
                "sftpserver",
                "-k", self._sftp_key_file,
                '-p', str(port)], cwd=self.tempdir[0], stdout=subprocess.PIPE)
            time.sleep(1)
            self.vals = {
                'server_url': 'localhost:{0}'.format(port),
                'username': 'admin',
                'password': 'admin',
                'rsa_key': None,
            }
        con_obj = self.registry('stock.connect')
        copy_id = con_obj.copy(cr,
                               uid,
                               self.ref('pc_connect_warehouse.demo_connection_1'),
                               context=ctx,
                               default={'connect_transport_id': self.ref('pc_connect_warehouse_yellowcube.fds_dummy_connection')})
        self.stock_connect_id = con_obj.browse(cr, uid, copy_id, ctx)
        self.stock_connect_id.connect_transport_id.write(self.vals)
        self.stock_connect_id.write({
            'remote_input_dir': '.',
            'remote_output_dir': '.',
            'local_archive_input_dir': self.tempdir[1],
            'local_archive_input_dir_temporal': self.tempdir[2],
            'remote_file_template': '[a-zA-Z0-9].*',
            'promiscuous_file_import': False,
        })

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
            logger.error("Pattern '{0}' not present on {1}".format(pattern, ret))
        return ret2

    def _get_file_node(self, file_name):
        file_id = self.stock_connect_file.search(self.cr, self.uid, [('name', '=', file_name)], context=self.context)
        return etree.XML(str(self.stock_connect_file.browse(self.cr, self.uid, file_id, context=self.context)[0].content))

    def _create_mirror_war_from_wab(self, wab_node, returngoods=False,
                                    ean_copy_policy=False):
        ns = xml_tools.schema_namespaces['warr']
        war_root = xml_tools.create_element('WAR', ns=ns)
        # BigHeader
        big_header = xml_tools.create_element('ControlReference', ns=ns)
        big_header.append(xml_tools.create_element('Type', 'WAR', ns=ns))
        big_header.append(xml_tools.create_element(
            'Sender', 'YELLOWCUBE', ns=ns))
        big_header.append(xml_tools.create_element('Receiver', 'YCTest', ns=ns))
        big_header.append(xml_tools.create_element(
            'Timestamp',
            xml_tools.nspath(wab_node, '//Timestamp')[0].text, ns=ns))
        big_header.append(xml_tools.create_element('OperatingMode', 'T', ns=ns))
        big_header.append(xml_tools.create_element('Version', '1.0', ns=ns))
        war_root.append(big_header)
        # GoodsIssueHeader
        goods_issue = xml_tools.create_element('GoodsIssue', ns=ns)
        war_root.append(goods_issue)
        goods_header = xml_tools.create_element('GoodsIssueHeader', ns=ns)
        goods_header.append(xml_tools.create_element(
            'BookingVoucherID', '4900109771', ns=ns))
        goods_header.append(xml_tools.create_element(
            'BookingVoucherYear', '2015', ns=ns))
        goods_header.append(xml_tools.create_element(
            'DepositorNo', '0000010518', ns=ns))
        goods_issue.append(goods_header)
        # CustomerOrderHeader
        order_header = xml_tools.create_element('CustomerOrderHeader', ns=ns)
        order_header.append(xml_tools.create_element(
            'YCDeliveryNo', '0410001201', ns=ns))
        order_header.append(xml_tools.create_element(
            'YCDeliveryDate', '20150101', ns=ns))
        order_header.append(xml_tools.create_element(
            'CustomerOrderNo',
            xml_tools.nspath(wab_node, '//CustomerOrderNo')[0].text, ns=ns))
        order_header.append(
            xml_tools.create_element('CustomerOrderDate', '20150101', ns=ns))
        order_header.append(xml_tools.create_element(
            'PostalShipmentNo', self.war_postal_shippment_no, ns=ns))
        goods_issue.append(order_header)
        # CustomerOrderList
        order_list = xml_tools.create_element('CustomerOrderList', ns=ns)
        for line in xml_tools.nspath(wab_node, '//Position'):
            order_line = xml_tools.create_element('CustomerOrderDetail', ns=ns)
            order_line.append(xml_tools.create_element(
                'BVPosNo', xml_tools.nspath(line, 'PosNo')[0].text, ns=ns))
            order_line.append(xml_tools.create_element(
                'CustomerOrderPosNo',
                xml_tools.nspath(line, 'PosNo')[0].text, ns=ns))
            order_line.append(xml_tools.create_element(
                'YCArticleNo',
                'YC{0}'.format(xml_tools.nspath(line,
                                                'ArticleNo')[0].text), ns=ns))

            # This the optional part for the <EAN> code of the WAR.
            has_ean = bool(xml_tools.nspath(line, 'EAN'))
            if has_ean and ean_copy_policy == 'copy':
                order_line.append(xml_tools.create_element(
                    'EAN', xml_tools.nspath(line, 'EAN')[0].text, ns=ns))
            elif ean_copy_policy == 'error':
                # The EANs are copied but with an error.
                order_line.append(xml_tools.create_element(
                    'EAN', '12345', ns=ns))
            elif ean_copy_policy == 'new':
                # A new & correct EAN is set on the WAB.
                order_line.append(xml_tools.create_element(
                    'EAN', '7611330002881', ns=ns))
            elif ean_copy_policy == 'skip' or not ean_copy_policy:
                # In this case we generate the WAR without the EANs set.
                pass

            order_line.append(xml_tools.create_element('Plant', 'Y005', ns=ns))
            order_line.append(xml_tools.create_element(
                'StorageLocation', 'YROD' if returngoods else 'YAFS', ns=ns))
            order_line.append(xml_tools.create_element(
                'TransactionType', '601', ns=ns))
            order_line.append(xml_tools.create_element('StockType', 'F', ns=ns))
            order_line.append(xml_tools.create_element(
                'QuantityUOM',
                xml_tools.nspath(line, 'Quantity')[0].text,
                attrib={
                    'QuantityISO': xml_tools.nspath(line,
                                                    'QuantityISO')[0].text},
                ns=ns))
            order_list.append(order_line)
        goods_issue.append(order_list)

        return war_root

    def _create_mirror_wba_from_wbl(self, wbl_node, returngoods=False,
                                    partial=None, end='1', ean=False,
                                    qty=False, lot=False):
        ns = xml_tools.schema_namespaces['wba']
        wba_root = xml_tools.create_element('WBA', ns=ns)
        # BigHeader
        big_header = xml_tools.create_element('ControlReference', ns=ns)
        big_header.append(xml_tools.create_element('Type', 'WBA', ns=ns))
        big_header.append(xml_tools.create_element(
            'Sender', 'YellowCube', ns=ns))
        big_header.append(xml_tools.create_element('Receiver', 'YCTest', ns=ns))
        big_header.append(xml_tools.create_element(
            'Timestamp',
            xml_tools.nspath(wbl_node, '//Timestamp')[0].text, ns=ns))
        big_header.append(xml_tools.create_element('OperatingMode', 'T', ns=ns))
        big_header.append(xml_tools.create_element('Version', '1.0', ns=ns))
        wba_root.append(big_header)
        # GoodsIssueHeader
        goods_receipt = xml_tools.create_element('GoodsReceipt', ns=ns)
        wba_root.append(goods_receipt)
        voucher_header = xml_tools.create_element('GoodsReceiptHeader', ns=ns)
        voucher_header.append(xml_tools.create_element(
            'BookingVoucherID', '1234567890', ns=ns))
        voucher_header.append(xml_tools.create_element(
            'BookingVoucherYear', '2013', ns=ns))
        voucher_header.append(xml_tools.create_element(
            'SupplierNo', '0000200015', ns=ns))
        voucher_header.append(xml_tools.create_element(
            'SupplierOrderNo',
            xml_tools.nspath(wbl_node, '//SupplierOrderNo')[0].text, ns=ns))
        goods_receipt.append(voucher_header)
        # CustomerOrderList
        order_list = xml_tools.create_element('GoodsReceiptList', ns=ns)
        for line in xml_tools.nspath(wbl_node, '//Position'):
            if partial and partial != int(
                    xml_tools.nspath(line, 'PosNo')[0].text):
                continue
            order_line = xml_tools.create_element('GoodsReceiptDetail', ns=ns)
            order_line.append(xml_tools.create_element(
                'BVPosNo', xml_tools.nspath(line, 'PosNo')[0].text, ns=ns))
            order_line.append(xml_tools.create_element(
                'SupplierOrderPosNo', xml_tools.nspath(line, 'PosNo')[0].text, ns=ns))
            order_line.append(xml_tools.create_element(
                'YCArticleNo',
                'YC{0}'.format(xml_tools.nspath(line,
                                                'ArticleNo')[0].text), ns=ns))

            # This the optional part for the <EAN> code of the WBA.
            if ean:
                order_line.append(xml_tools.create_element('EAN', ean, ns=ns))

            # This the optional part for the <Lot> code of the WBA.
            if lot:
                order_line.append(
                    xml_tools.create_element('Lot', lot.name, ns=ns))

            order_line.append(xml_tools.create_element('Plant', 'Y005', ns=ns))
            order_line.append(xml_tools.create_element(
                'StorageLocation',
                'YROD' if not returngoods else 'YAFS', ns=ns))

            if not qty:
                qty = xml_tools.nspath(line, 'Quantity')[0].text

            order_line.append(xml_tools.create_element(
                'QuantityUOM',
                qty,
                attrib={'QuantityISO': xml_tools.nspath(line, 'QuantityISO')[0].text},
                ns=ns))
            order_line.append(xml_tools.create_element('EndOfDeliveryFlag', end, ns=ns))
            order_list.append(order_line)
        goods_receipt.append(order_list)

        return wba_root

    def create_lot(self, lot_name, product_id, product_qty):
        """ Returns a lot object, created over the product received.
        """
        lot_obj = self.registry('stock.production.lot')
        move_obj = self.registry('stock.move')

        # Creates the lot.
        lot_id = lot_obj.create(self.cr, self.uid, {
            'name': lot_name,
            'product_id': product_id,
            'date': fields.datetime.now(),
        }, self.context)

        # Fills it from products coming from the suppliers.
        move_id = move_obj.create(self.cr, self.uid, {
            'product_id': product_id,
            'product_qty': product_qty,
            'product_uom': self.ref('product.product_uom_unit'),
            'name': 'Product ID={0}'.format(product_id),
            'type': 'internal',
            'date_expected': fields.datetime.now(),
            'prodlot_id': lot_id,
            'location_id': self.ref('stock.stock_location_suppliers'),
            'location_dest_id': self.ref('pc_connect_warehouse_yellowcube.'
                                         'location_YC_YAFS'),
        }, self.context)
        move_obj.action_done(self.cr, self.uid, [move_id], context=self.context)

        lot = lot_obj.browse(self.cr, self.uid, lot_id, context=self.context)
        return lot

    def _save_node(self, node, _type, path, extra=''):
        node_id = xml_tools.nspath(node, path)[0].text
        name = '{0}/{1}_{2}_{3}{4}.xml'.format(self.output_dir,
                                               self.test_warehouse.stock_connect_id.yc_sender,
                                               _type,
                                               node_id,
                                               extra)
        f = open(name, 'w')
        f.write(xml_tools.xml_to_string(node))

    def _create_purchase(self, defaults=None):
        """ Creates a purchse to use in the WBA tests.
        """
        if defaults is None:
            defaults = {}
        cr, uid, ctx = self.cr, self.uid, self.context
        purchase_order_obj = self.registry('purchase.order')

        purchase_vals = {
            'name': 'IN_WBL_test',
            'partner_id': self.supplier_id,
            'warehouse_id': self.test_warehouse.id,
            'location_id': self.test_warehouse.lot_input_id.id,
            'pricelist_id': self.ref('purchase.list0'),
            'invoice_method': 'picking',
        }
        purchase_vals.update(defaults)
        purchase_id = purchase_order_obj.create(cr, uid, purchase_vals, ctx)
        return purchase_id

    def _add_purchase_line(self, purchase_id, defaults=None):
        """ Creates a purchase.order.line and links it to the purchase.
            The product_id and the product_qty are mandatory in the defaults.
        """
        if defaults is None:
            defaults = {}
        cr, uid, ctx = self.cr, self.uid, self.context
        purchase_order_line_obj = self.registry('purchase.order.line')

        self.assertTrue('product_id' in defaults,
                        "product_id must be in the defaults.")
        self.assertTrue('product_qty' in defaults,
                        "product_qty must be in the defaults.")

        purchase_lines_vals = {
            'order_id': purchase_id,
            'price_unit': 7.65,
            'name': 'Test purchase product',
            'date_planned': '2050-01-01',
        }
        purchase_lines_vals.update(defaults)
        line_id = \
            purchase_order_line_obj.create(cr, uid, purchase_lines_vals, ctx)
        return line_id

    def _validate_purchase(self, purchase_id):
        """ Validates the purchase and moves it to the state approved
            which its picking.in in state assigned (i.e. Ready to Receive).
        """
        cr, uid, ctx = self.cr, self.uid, self.context
        purchase_obj = self.registry('purchase.order')

        purchase = purchase_obj.browse(cr, uid, purchase_id, context=ctx)
        purchase.wkf_confirm_order()
        purchase.wkf_approve_order()
        purchase.action_picking_create()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
