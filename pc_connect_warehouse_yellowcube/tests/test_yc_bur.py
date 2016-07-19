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
import logging
logger = logging.getLogger(__name__)
import unittest2
from yellowcube_testcase import yellowcube_testcase
from ..xml_abstract_factory import get_factory
from ..xsd.xml_tools import nspath, create_root, create_element, xml_to_string, schema_namespaces


class test_yc_bur(yellowcube_testcase):

    def setUp(self):
        super(test_yc_bur, self).setUp()
        self.test_warehouse.stock_connect_id.write({'yc_enable_bur_file': True})

        self.product_3 = self.browse_ref('product.product_product_3')
        if hasattr(self.product_3, 'action_validated'):
            self.product_3.action_validated()
            self.product_3.action_in_production()

    def _create_bur_file(self):
        ns = schema_namespaces['bur']
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
            'content': xml_to_string(bur_root, encoding='unicode', xml_declaration=False),
            'name': 'test_bur_file.xml',
            'stock_connect_id': self.test_warehouse.stock_connect_id.id,
        }
        return self.stock_connect_file.create(self.cr, self.uid, vals, self.context)

    def test_stock_picking_change(self):
        """
        This test tests the creation of BUR files

        Pre: This test requires that there are products ready for export
        """
        cr, uid, ctx = self.cr, self.uid, self.context
        file_id = self._create_bur_file()

        self.assertEqual(self._yc_files(_type=None), ['test_bur_file.xml'], 'BUR file is not processed')

        self.test_warehouse.stock_connect_id.connection_process_files()

        self.assertEqual(self._yc_files(_type='bur'), ['test_bur_file.xml'], 'BUR file is processed')
        file = self.stock_connect_file.browse(cr, uid, file_id, ctx)
        self.assertEqual(file.state, 'done', 'BUR file is 100% processed')

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
