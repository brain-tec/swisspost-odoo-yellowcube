# b-*- encoding: utf-8 -*-
##############################################################################
#
#    Copyright (c) 2017 brain-tec AG (http://www.braintec-group.com)
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


class test_yc_bar(yellowcube_testcase):

    def setUp(self):
        super(test_yc_bar, self).setUp()
        self.test_warehouse.stock_connect_id.write({'yc_enable_bar_file': True})

        self.product_3 = self.browse_ref('product.product_product_3')
        if 'action_validated' in self.product_3:
            self.product_3.action_validated()
            self.product_3.action_in_production()

        self.bar_file_name = 'BAR_{0}.xml'.format(time.time())

    def _get_bar(self):
        """ Gets the BAR that was just generated.
        """
        cr, uid, ctx = self.cr, self.uid, self.context

        # Gets the BUR that was generated.
        file_ids = self.stock_connect_file.search(
            cr, uid,[('id', '>', self._last_file_id),
                     ('warehouse_id', '=', self.test_warehouse.id),
                     ('type', '=', 'bar')],
            context=ctx)
        self.assertEqual(len(file_ids), 1,
                         'Only one BAR was expected to be found, but {0} '
                         'were found instead.'.format(len(file_ids)))

        bar_file = \
            self.stock_connect_file.browse(cr, uid, file_ids[0], context=ctx)
        return bar_file

    def _create_bar_file(self, ean=None):
        create_root = xml_tools.create_root
        create_element = xml_tools.create_element
        ns = xml_tools.schema_namespaces['bar']
        bar_root = create_root('{{{bar}}}BAR')

        control_reference = create_element('ControlReference', ns=ns)
        control_reference.append(create_element('Type', 'BAR', ns=ns))
        control_reference.append(create_element('Sender', 'YELLOWCUBE', ns=ns))
        control_reference.append(create_element('Receiver', 'YCTest', ns=ns))
        control_reference.append(create_element('Timestamp', '20150105101500', ns=ns))
        control_reference.append(create_element('OperatingMode', 'T', ns=ns))
        control_reference.append(create_element('Version', '1.0', ns=ns))
        bar_root.append(control_reference)

        article_list = create_element('ArticleList', ns=ns)
        article = create_element('Article', ns=ns)
        article.append(create_element('YCArticleNo', 'test_product_3', ns=ns))
        if ean:
            article.append(create_element('EAN', ean, ns=ns))
        article.append(create_element('ArticleNo', 'PCSC234', ns=ns))
        article.append(create_element('ArticleDescription', ns=ns))
        article.append(create_element('Plant', 'Y005', ns=ns))
        article.append(create_element('StorageLocation', 'YAFS', ns=ns))
        article.append(create_element('StockType', ' ', ns=ns))
        article.append(create_element('QuantityUOM', '77',
                                      {'QuantityISO': 'PCE'}, ns=ns))
        article_list.append(article)

        bar_root.append(article_list)

        vals = {
            'input': True,
            'content': xml_tools.xml_to_string(
                bar_root, encoding='unicode', xml_declaration=False),
            'name': self.bar_file_name,
            'stock_connect_id': self.test_warehouse.stock_connect_id.id,
            'type': 'bar',
            'warehouse_id': self.test_warehouse.id,
        }
        self.stock_connect_file.create(self.cr, self.uid, vals, self.context)

    @skipIf(UNDER_DEVELOPMENT, UNDER_DEVELOPMENT_TEXT)
    def test_bar_ean_activated_good_ean(self):
        """ The EANs are activated and we receive a BAR with a good EAN, thus
            the file is correctly processed and its changes apply.
        """
        cr, uid, ctx = self.cr, self.uid, self.context
        prodlots_obj = self.registry('stock.report.prodlots')
        location_obj = self.registry('stock.location')

        # Activates the EANs for the stock.connect.files.
        self.test_warehouse.stock_connect_id.write({'yc_ignore_ean': False})

        # Checks that we don't have yet a quantity on YAFS.
        prod_ids = self.product_obj.search(
            cr, uid, [('default_code', '=', 'PCSC234')], context=ctx)
        prod = self.product_obj.browse(cr, uid, prod_ids[0], context=ctx)
        yafs_ids = location_obj.search(
            cr, uid, [('name', '=', 'YAFS')], context=ctx)
        yafs = location_obj.browse(cr, uid, yafs_ids[0], context=ctx)
        prodlots_ids = prodlots_obj.search(
            cr, uid, [('product_id', '=', prod.id),
                      ('location_id', '=', yafs.id),
                      ], context=ctx)
        self.assertFalse(prodlots_ids)

        # Creates the BAR, with the product having an EAN number.
        ean = '7611330002706'
        self.product_obj.write(cr, uid, self.product_3.id,
                               {'ean13': ean}, context=ctx)
        self._create_bar_file(ean=ean)

        # Processes the BAR file.
        self.assertEqual(self._yc_files(_type=None), [self.bar_file_name],
                         'BAR file is not processed')
        self.test_warehouse.stock_connect_id.connection_process_files()

        # Checks that the BAR was processed without errors.
        bar_file = self._get_bar()
        self.assertFalse(bar_file.error)
        self.assertEqual(bar_file.state, 'done')

        # Checks that the product has the new qty set by the BAR on the YAFS.
        prod_ids = self.product_obj.search(
            cr, uid, [('default_code', '=', 'PCSC234')], context=ctx)
        prod = self.product_obj.browse(cr, uid, prod_ids[0], context=ctx)
        yafs_ids = location_obj.search(
            cr, uid, [('name', '=', 'YAFS')], context=ctx)
        yafs = location_obj.browse(cr, uid, yafs_ids[0], context=ctx)
        prodlots_ids = prodlots_obj.search(
            cr, uid, [('product_id', '=', prod.id),
                      ('location_id', '=', yafs.id),
                      ], context=ctx)
        prodlot = prodlots_obj.browse(
            cr, uid, prodlots_ids[0], context=ctx)
        self.assertEqual(prodlot.qty, 77)

    @skipIf(UNDER_DEVELOPMENT, UNDER_DEVELOPMENT_TEXT)
    def test_bar_ean_activated_wrong_ean(self):
        """ The EANs are activated and we receive a BAR with a wrong EAN, thus
            the file results in an error when processed, and as a result its
            changes do not apply.
        """
        cr, uid, ctx = self.cr, self.uid, self.context
        prodlots_obj = self.registry('stock.report.prodlots')
        location_obj = self.registry('stock.location')

        # Activates the EANs for the stock.connect.files.
        self.test_warehouse.stock_connect_id.write({'yc_ignore_ean': False})

        # Checks that we don't have yet a quantity on YAFS.
        prod_ids = self.product_obj.search(
            cr, uid, [('default_code', '=', 'PCSC234')], context=ctx)
        prod = self.product_obj.browse(cr, uid, prod_ids[0], context=ctx)
        yafs_ids = location_obj.search(
            cr, uid, [('name', '=', 'YAFS')], context=ctx)
        yafs = location_obj.browse(cr, uid, yafs_ids[0], context=ctx)
        prodlots_ids = prodlots_obj.search(
            cr, uid, [('product_id', '=', prod.id),
                      ('location_id', '=', yafs.id),
                      ], context=ctx)
        self.assertFalse(prodlots_ids)

        # Checks that the quantity is different than the one that will be
        # set up by the BAR.
        prod_ids = self.product_obj.search(
            cr, uid, [('default_code', '=', 'PCSC234')], context=ctx)
        self.assertEqual(
            len(prod_ids), 1,
            "We expected to find just one product with code "
            "PCSC234 but found {0} instead.".format(len(prod_ids)))
        prod = self.product_obj.browse(cr, uid, prod_ids[0], context=ctx)
        self.assertNotEqual(prod.qty_available, 77)

        # Creates the BAR, with the product having an EAN number.
        self.product_obj.write(cr, uid, self.product_3.id,
                               {'ean13': '7611330002706'}, context=ctx)
        self._create_bar_file(ean='76113300027xx')

        # Processes the BAR file.
        self.assertEqual(self._yc_files(_type=None), [self.bar_file_name],
                         'BAR file is not processed')
        self.test_warehouse.stock_connect_id.connection_process_files()

        # Checks that the BAR was processed with errors.
        bur_file = self._get_bar()
        self.assertTrue(bur_file.error)
        self.assertEqual(bur_file.state, 'draft')

        # Checks that the product has the not created a new entry
        # for the quantities.
        prodlots_ids = prodlots_obj.search(
            cr, uid, [('product_id', '=', prod.id),
                      ('location_id', '=', yafs.id),
                      ], context=ctx)
        self.assertFalse(prodlots_ids)

    @skipIf(UNDER_DEVELOPMENT, UNDER_DEVELOPMENT_TEXT)
    def test_bar_ean_deactivated_good_ean(self):
        """ We received a good EAN on the BAR, but we don't have a look at it.
            since the EANs are deactivated on the connection.
        """
        cr, uid, ctx = self.cr, self.uid, self.context
        prodlots_obj = self.registry('stock.report.prodlots')
        location_obj = self.registry('stock.location')

        # Deactivates the EANs for the stock.connect.files.
        self.test_warehouse.stock_connect_id.write({'yc_ignore_ean': True})

        # Checks that we don't have yet a quantity on YAFS.
        prod_ids = self.product_obj.search(
            cr, uid, [('default_code', '=', 'PCSC234')], context=ctx)
        prod = self.product_obj.browse(cr, uid, prod_ids[0], context=ctx)
        yafs_ids = location_obj.search(
            cr, uid, [('name', '=', 'YAFS')], context=ctx)
        yafs = location_obj.browse(cr, uid, yafs_ids[0], context=ctx)
        prodlots_ids = prodlots_obj.search(
            cr, uid, [('product_id', '=', prod.id),
                      ('location_id', '=', yafs.id),
                      ], context=ctx)
        self.assertFalse(prodlots_ids)

        # Creates the BAR, with the product having an EAN number.
        ean = '7611330002706'
        self.product_obj.write(cr, uid, self.product_3.id,
                               {'ean13': ean}, context=ctx)
        self._create_bar_file(ean=ean)

        # Processes the BAR file.
        self.assertEqual(self._yc_files(_type=None), [self.bar_file_name],
                         'BAR file is not processed')
        self.test_warehouse.stock_connect_id.connection_process_files()

        # Checks that the BAR was processed without errors.
        bar_file = self._get_bar()
        self.assertFalse(bar_file.error)
        self.assertEqual(bar_file.state, 'done')

        # Checks that the product has the new qty set by the BAR on the YAFS.
        prod_ids = self.product_obj.search(
            cr, uid, [('default_code', '=', 'PCSC234')], context=ctx)
        prod = self.product_obj.browse(cr, uid, prod_ids[0], context=ctx)
        yafs_ids = location_obj.search(
            cr, uid, [('name', '=', 'YAFS')], context=ctx)
        yafs = location_obj.browse(cr, uid, yafs_ids[0], context=ctx)
        prodlots_ids = prodlots_obj.search(
            cr, uid, [('product_id', '=', prod.id),
                      ('location_id', '=', yafs.id),
                      ], context=ctx)
        prodlot = prodlots_obj.browse(
            cr, uid, prodlots_ids[0], context=ctx)
        self.assertEqual(prodlot.qty, 77)

    @skipIf(UNDER_DEVELOPMENT, UNDER_DEVELOPMENT_TEXT)
    def test_bar_ean_deactivated_wrong_ean(self):
        """ We received a wrong EAN on the BAR, but we don't have a look at it
            since the EANs are deactivated on the connection.
        """
        cr, uid, ctx = self.cr, self.uid, self.context
        prodlots_obj = self.registry('stock.report.prodlots')
        location_obj = self.registry('stock.location')

        # Deactivates the EANs for the stock.connect.files.
        self.test_warehouse.stock_connect_id.write({'yc_ignore_ean': True})

        # Checks that we don't have yet a quantity on YAFS.
        prod_ids = self.product_obj.search(
            cr, uid, [('default_code', '=', 'PCSC234')], context=ctx)
        prod = self.product_obj.browse(cr, uid, prod_ids[0], context=ctx)
        yafs_ids = location_obj.search(
            cr, uid, [('name', '=', 'YAFS')], context=ctx)
        yafs = location_obj.browse(cr, uid, yafs_ids[0], context=ctx)
        prodlots_ids = prodlots_obj.search(
            cr, uid, [('product_id', '=', prod.id),
                      ('location_id', '=', yafs.id),
                      ], context=ctx)
        self.assertFalse(prodlots_ids)

        # Checks that the quantity is different than the one that will be
        # set up by the BAR.
        prod_ids = self.product_obj.search(
            cr, uid, [('default_code', '=', 'PCSC234')], context=ctx)
        self.assertEqual(
            len(prod_ids), 1,
            "We expected to find just one product with code "
            "PCSC234 but found {0} instead.".format(len(prod_ids)))
        prod = self.product_obj.browse(cr, uid, prod_ids[0], context=ctx)
        self.assertNotEqual(prod.qty_available, 77)

        # Creates the BAR, with the product having an EAN number.
        self.product_obj.write(cr, uid, self.product_3.id,
                               {'ean13': '7611330002706'}, context=ctx)
        self._create_bar_file(ean='76113300027xx')

        # Processes the BAR file.
        self.assertEqual(self._yc_files(_type=None), [self.bar_file_name],
                         'BAR file is not processed')
        self.test_warehouse.stock_connect_id.connection_process_files()

        # Checks that the BAR was processed without errors.
        bur_file = self._get_bar()
        self.assertFalse(bur_file.error)
        self.assertEqual(bur_file.state, 'done')

        # Checks that the product has the new qty set by the BAR on the YAFS.
        prod_ids = self.product_obj.search(
            cr, uid, [('default_code', '=', 'PCSC234')], context=ctx)
        prod = self.product_obj.browse(cr, uid, prod_ids[0], context=ctx)
        yafs_ids = location_obj.search(
            cr, uid, [('name', '=', 'YAFS')], context=ctx)
        yafs = location_obj.browse(cr, uid, yafs_ids[0], context=ctx)
        prodlots_ids = prodlots_obj.search(
            cr, uid, [('product_id', '=', prod.id),
                      ('location_id', '=', yafs.id),
                      ], context=ctx)
        prodlot = prodlots_obj.browse(
            cr, uid, prodlots_ids[0], context=ctx)
        self.assertEqual(prodlot.qty, 77)

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
