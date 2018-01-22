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
from yellowcube_testcase import yellowcube_testcase
from ..xsd.xml_tools import _XmlTools as xml_tools
import time
from unittest2 import skipIf

UNDER_DEVELOPMENT = False
UNDER_DEVELOPMENT_TEXT = "Test was skipped because of being under development."


class test_yc_bur(yellowcube_testcase):

    def setUp(self):
        super(test_yc_bur, self).setUp()
        self.test_warehouse.stock_connect_id.write({'yc_enable_bur_file': True})

        self.product_3 = self.browse_ref('product.product_product_3')
        if 'action_validated' in self.product_3:
            self.product_3.action_validated()
            self.product_3.action_in_production()

        self.bur_file_name = 'BUR_{0}.xml'.format(time.time())

    def _get_bur(self):
        """ Gets the BUR that was just generated.
        """
        cr, uid, ctx = self.cr, self.uid, self.context

        # Gets the BUR that was generated.
        file_ids = self.stock_connect_file.search(
            cr, uid,[('id', '>', self._last_file_id),
                     ('warehouse_id', '=', self.test_warehouse.id),
                     ('type', '=', 'bur')],
            context=ctx)
        self.assertEqual(len(file_ids), 1,
                         'Only one BUR was expected to be found, but {0} '
                         'were found instead.'.format(len(file_ids)))

        bur_file = \
            self.stock_connect_file.browse(cr, uid, file_ids[0], context=ctx)
        return bur_file

    def _create_bur_file(self, ean=None):
        create_root = xml_tools.create_root
        create_element = xml_tools.create_element
        ns = xml_tools.schema_namespaces['bur']
        bur_root = create_root('{{{bur}}}BUR')

        control_reference = create_element('ControlReference', ns=ns)
        control_reference.append(create_element('Type', 'BUR', ns=ns))
        control_reference.append(create_element('Sender', 'YELLOWCUBE', ns=ns))
        control_reference.append(create_element('Receiver', 'YCTest', ns=ns))
        control_reference.append(create_element('Timestamp', '20150105101500', ns=ns))
        control_reference.append(create_element('OperatingMode', 'T', ns=ns))
        control_reference.append(create_element('Version', '1.0', ns=ns))
        bur_root.append(control_reference)

        movements = create_element('GoodsMovements', ns=ns)
        movements_header = create_element('GoodsMovementsHeader', ns=ns)
        movements_header.append(create_element('BookingVoucherID', '', ns=ns))
        movements_header.append(create_element('BookingVoucherYear', '2015', ns=ns))
        movements_header.append(create_element('DepositorNo', self.test_warehouse.stock_connect_id.yc_depositor_no, ns=ns))
        movements.append(movements_header)

        booking_list = create_element('BookingList', ns=ns)
        booking_detail = create_element('BookingDetail', ns=ns)
        booking_detail.append(create_element('BVPosNo', '000001', ns=ns))
        booking_detail.append(create_element('YCArticleNo', 'test_product_3', ns=ns))
        booking_detail.append(create_element('ArticleNo', 'PCSC234', ns=ns))
        if ean:
            booking_detail.append(create_element('EAN', ean, ns=ns))
        booking_detail.append(create_element('Plant', 'Y005', ns=ns))
        booking_detail.append(create_element('StorageLocation', 'YROD', ns=ns))
        booking_detail.append(create_element('MoveStorageLocation', 'YAFS', ns=ns))
        booking_detail.append(create_element('YCLot', 'PCSC234_AA', ns=ns))
        booking_detail.append(create_element('Lot', 'PCSC234_AAA001', ns=ns))
        booking_detail.append(create_element('BestBeforeDate', '20550101', ns=ns))
        booking_detail.append(create_element('TransactionType', '0', ns=ns))
        booking_detail.append(create_element('StockType', '', ns=ns))
        booking_detail.append(create_element('QuantityUOM', '10', {'QuantityISO': 'PCE'}, ns=ns))
#        booking_detail.append(create_element('MovePlant', 'Y005'))

        booking_list.append(booking_detail)
        movements.append(booking_list)

        bur_root.append(movements)

        vals = {
            'input': True,
            'content': xml_tools.xml_to_string(bur_root, encoding='unicode', xml_declaration=False),
            'name': self.bur_file_name,
            'stock_connect_id': self.test_warehouse.stock_connect_id.id,
            'type': 'bur',
            'warehouse_id': self.test_warehouse.id,
        }
        self.stock_connect_file.create(self.cr, self.uid, vals, self.context)

    @skipIf(UNDER_DEVELOPMENT, UNDER_DEVELOPMENT_TEXT)
    def test_stock_picking_change(self):
        """
        This test tests the creation of BUR files

        Pre: This test requires that there are products ready for export
        """
        cr, uid, ctx = self.cr, self.uid, self.context
        self._create_bur_file()

        self.assertEqual(self._yc_files(_type=None), [self.bur_file_name], 'BUR file is not processed')

        self.test_warehouse.stock_connect_id.connection_process_files()

        self.assertEqual(self._yc_files(_type='bur'), [self.bur_file_name], 'BUR file is processed')

    @skipIf(UNDER_DEVELOPMENT, UNDER_DEVELOPMENT_TEXT)
    def test_bur_with_ean_activated_good_ean(self):
        """ Tests a BUR having an EAN number which is the one for the product.
        """
        cr, uid, ctx = self.cr, self.uid, self.context

        # Activates the EANs for the stock.connect.files.
        self.test_warehouse.stock_connect_id.write({'yc_ignore_ean': False})

        # Creates the BUR, with the product having an EAN number.
        ean = '7611330002706'
        self.product_obj.write(cr, uid, self.product_3.id,
                               {'ean13': ean}, context=ctx)
        self._create_bur_file(ean=ean)

        # Processes the BUR file.
        self.assertEqual(self._yc_files(_type=None), [self.bur_file_name],
                         'BUR file is not processed')
        self.test_warehouse.stock_connect_id.connection_process_files()

        # Checks that the BUR was processed without errors.
        bur_file = self._get_bur()
        self.assertFalse(bur_file.error)
        self.assertFalse(bur_file.info)
        self.assertEqual(bur_file.state, 'done')

    @skipIf(UNDER_DEVELOPMENT, UNDER_DEVELOPMENT_TEXT)
    def test_bur_with_ean_activated_wrong_ean(self):
        """ Tests a BUR having an EAN number which is the wrong one for the
            product. Thus since the EANs are active, it must set the
            stock.connect.file as errored."""
        cr, uid, ctx = self.cr, self.uid, self.context

        # Activates the EANs for the stock.connect.files.
        self.test_warehouse.stock_connect_id.write({'yc_ignore_ean': False})

        # Creates the BUR, with the product having an EAN number.
        self.product_obj.write(cr, uid, self.product_3.id,
                               {'ean13': '7611330002706'}, context=ctx)
        self._create_bur_file(ean='76113300027xx')

        # Processes the BUR file.
        self.assertEqual(self._yc_files(_type=None), [self.bur_file_name],
                         'BUR file is not processed')
        self.test_warehouse.stock_connect_id.connection_process_files()

        # Checks that the BUR was processed without errors.
        bur_file = self._get_bur()
        self.assertTrue(bur_file.error)
        self.assertTrue(bur_file.info)
        self.assertEqual(bur_file.state, 'draft')

    @skipIf(UNDER_DEVELOPMENT, UNDER_DEVELOPMENT_TEXT)
    def test_bur_with_ean_deactivated_wrong_ean(self):
        """ Test a BUR having an EAN number which is the wrong one for the
            product. But since the EAN are inactive, the stock.connect.file
            will be processed OK, since the check will be skipped.
        """
        cr, uid, ctx = self.cr, self.uid, self.context

        # Deactivates the EANs for the stock.connect.files.
        self.test_warehouse.stock_connect_id.write({'yc_ignore_ean': True})

        # Creates the BUR, with the product having an EAN number.
        self.product_obj.write(cr, uid, self.product_3.id,
                               {'ean13': '7611330002706'}, context=ctx)
        self._create_bur_file(ean='76113300027xx')

        # Processes the BUR file.
        self.assertEqual(self._yc_files(_type=None), [self.bur_file_name],
                         'BUR file is not processed')
        self.test_warehouse.stock_connect_id.connection_process_files()

        # Checks that the BUR was processed without errors.
        bur_file = self._get_bur()
        self.assertFalse(bur_file.error)
        self.assertFalse(bur_file.info)
        self.assertEqual(bur_file.state, 'done')

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
