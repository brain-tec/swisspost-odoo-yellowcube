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
import unittest2
from yellowcube_testcase import yellowcube_testcase
from ..xml_abstract_factory import get_factory
from unittest2 import skipIf

UNDER_DEVELOPMENT = False
UNDER_DEVELOPMENT_TEXT = "Test was skipped because of being under development."


class test_yc_art(yellowcube_testcase):

    def setUp(self):
        super(test_yc_art, self).setUp()
        self.test_warehouse.stock_connect_id.write({'yc_enable_art_file': True, 'yc_enable_art_multifile': False})

        self.product_3 = self.browse_ref('product.product_product_3')
        if 'action_validated' in self.product_3:
            self.product_3.action_validated()
            self.product_3.action_in_production()

    def _get_art(self):
        """ Gets the ART that was just generated.
        """
        cr, uid, ctx = self.cr, self.uid, self.context

        # Generates the ART file.
        art_factory = get_factory(
            [self.test_warehouse.pool, cr, uid], "art", context=ctx)
        art_factory.generate_files([('id', '=', self.test_warehouse.id)],
                                   force_product_ids=[self.product_3.id])

        # Gets the ART that was generated.
        file_ids = self.stock_connect_file.search(
            cr, uid,[('id', '>', self._last_file_id),
                     ('warehouse_id', '=', self.test_warehouse.id),
                     ('error', '!=', True),
                     ('type', '=', 'art')],
            context=ctx)
        self.assertEqual(len(file_ids), 1,
                         'Only one ART was expected to be found, but {0} '
                         'were found instead.'.format(len(file_ids)))

        art_file = \
            self.stock_connect_file.browse(cr, uid, file_ids[0], context=ctx)
        return art_file

    @skipIf(UNDER_DEVELOPMENT, UNDER_DEVELOPMENT_TEXT)
    def test_art_generates_no_response_for_yellowcube(self):
        """ The ART file generates no RESPONSE file for pure-Yellowcube.
        """
        cr, uid, ctx = self.cr, self.uid, self.context
        self.prepare_test_fds_server()

        connect_obj = self.registry('stock.connect')
        connect_file_obj = self.registry('stock.connect.file')

        # Generates the ART file.
        env = [self.test_warehouse.pool, cr, uid]
        art_factory = get_factory(env, "art", context=ctx)
        art_factory.generate_files([('id', '=', self.test_warehouse.id)],
                                   force_product_ids=[self.product_3.id])

        # Sends the ART file.
        connection_id = self.ref(
            'pc_connect_warehouse_yellowcube.demo_connection_yc')
        connect_obj.connection_send_files(cr, uid, connection_id, context=ctx)

        # Checks that there is an ART which was sent generated and no RESPONSE.
        file_ids = connect_file_obj.search(cr, uid, [
            ('stock_connect_id', '=', connection_id),
            ('error', '!=', True),
        ], context=ctx)
        self.assertEqual(len(file_ids), 1,
                         "I expected to find just one stock.connect.file, "
                         "but found {0} instead.".format(len(file_ids)))
        connect_file = connect_file_obj.browse(cr, uid, file_ids[0], ctx)
        self.assertEqual(connect_file.type, 'art',
                         "The only file was expected to be an ART, "
                         "but was {0}".format(connect_file.type))
        self.assertEqual(connect_file.state, 'done',
                         "The only file was expected to be in state done, "
                         "but was in state {0}".format(connect_file.state))

    @skipIf(UNDER_DEVELOPMENT, UNDER_DEVELOPMENT_TEXT)
    def test_inventory(self):
        """
        This test tests the creation of ART files

        Pre: This test requires that there are products ready for export
        """
        cr, uid, ctx = self.cr, self.uid, self.context

        self.assertEqual(self._yc_files(), [], 'No export file exists')

        art_factory = get_factory([self.test_warehouse.pool, cr, uid], "art", context=ctx)
        art_factory.generate_files([('id', '=', self.test_warehouse.id)],
                                   force_product_ids=[self.product_3.id])

        self.assertEqual(len(self._yc_files(_type='art')), 1, 'ART file exists')

    @skipIf(UNDER_DEVELOPMENT, UNDER_DEVELOPMENT_TEXT)
    def test_ean_art8(self):
        """ Tests that the type for EAN of length 8 is set on the ART.
        """
        cr, uid, ctx = self.cr, self.uid, self.context
        prod_obj = self.registry('product.product')

        # Sets an EAN of lenght 8 to the product.
        product_id = self.ref('product.product_product_3')
        prod_obj.write(cr, uid, product_id, {'ean13': '12345678'},
                       context=ctx)

        # Checks that the ART generated has the correct type set for the ART.
        art_file = self._get_art()
        self.assertTrue(
            '<EAN EANType="HK">12345678</EAN>' in art_file.content,
            "Bad EAN found in the ART file generated.")

    @skipIf(UNDER_DEVELOPMENT, UNDER_DEVELOPMENT_TEXT)
    def test_ean_art12(self):
        """ Tests that the type for EAN of length 12 is set on the ART.
        """
        cr, uid, ctx = self.cr, self.uid, self.context
        prod_obj = self.registry('product.product')

        # Sets an EAN of lenght 8 to the product.
        product_id = self.ref('product.product_product_3')
        prod_obj.write(cr, uid, product_id, {'ean13': '123456789012'},
                       context=ctx)

        # Checks that the ART generated has the correct type set for the ART.
        art_file = self._get_art()
        self.assertTrue(
            '<EAN EANType="UC">123456789012</EAN>' in art_file.content,
            "Bad EAN found in the ART file generated.")

    @skipIf(UNDER_DEVELOPMENT, UNDER_DEVELOPMENT_TEXT)
    def test_ean_art13(self):
        """ Tests that the type for EAN of length 13 is set on the ART.
        """
        cr, uid, ctx = self.cr, self.uid, self.context
        prod_obj = self.registry('product.product')

        # Sets an EAN of lenght 8 to the product.
        product_id = self.ref('product.product_product_3')
        prod_obj.write(cr, uid, product_id, {'ean13': '7611330002935'},
                       context=ctx)

        # Checks that the ART generated has the correct type set for the ART.
        art_file = self._get_art()
        self.assertTrue(
            '<EAN EANType="HE">7611330002935</EAN>' in art_file.content,
            "Bad EAN found in the ART file generated.")

    @skipIf(UNDER_DEVELOPMENT, UNDER_DEVELOPMENT_TEXT)
    def test_ean_art14(self):
        """ Tests that the type for EAN of length 14 is set on the ART.
        """
        cr, uid, ctx = self.cr, self.uid, self.context
        prod_obj = self.registry('product.product')

        # Sets an EAN of lenght 8 to the product.
        product_id = self.ref('product.product_product_3')
        prod_obj.write(cr, uid, product_id, {'ean13': '12345678901234'},
                       context=ctx)

        # Checks that the ART generated has the correct type set for the ART.
        art_file = self._get_art()
        self.assertTrue(
            '<EAN EANType="UC">12345678901234</EAN>' in art_file.content,
            "Bad EAN found in the ART file generated.")

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
