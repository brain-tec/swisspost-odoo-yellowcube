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
import subprocess
from tempfile import mkstemp, mkdtemp
import os, time, socket
from unittest2 import skipIf

UNDER_DEVELOPMENT = False
UNDER_DEVELOPMENT_TEXT = "Test was skipped because of being under development."


class test_ean(yellowcube_testcase):

    def setUp(self):
        super(test_ean, self).setUp()
        self.context = {}

    def _create_product(self, defaults=None):
        if defaults is None:
            defaults = {}
        cr, uid, ctx = self.cr, self.uid, self.context
        prod_obj = self.registry('product.product')

        vals = {
            'name': 'Default Name',
            'sale_ok': True,
            'purchase_ok': True,
            'sale_delay': 0,
            'produce_delay': 0,
        }
        vals.update(defaults)
        product_id = prod_obj.create(cr, uid, vals, context=ctx)
        return product_id

    @skipIf(UNDER_DEVELOPMENT, UNDER_DEVELOPMENT_TEXT)
    def test_null_ean_type(self):
        cr, uid, ctx = self.cr, self.uid, self.context
        prod_obj = self.registry('product.product')

        prod_id = self._create_product({'ean13': ''})
        self.assertEqual('',
                         prod_obj.get_ean_type(cr, uid, prod_id, context=ctx))

    @skipIf(UNDER_DEVELOPMENT, UNDER_DEVELOPMENT_TEXT)
    def test_ean8_type(self):
        cr, uid, ctx = self.cr, self.uid, self.context
        prod_obj = self.registry('product.product')

        prod_id = self._create_product({'ean13': '12345678'})
        self.assertEqual('HK',
                         prod_obj.get_ean_type(cr, uid, prod_id, context=ctx))

    @skipIf(UNDER_DEVELOPMENT, UNDER_DEVELOPMENT_TEXT)
    def test_ean12_type(self):
        cr, uid, ctx = self.cr, self.uid, self.context
        prod_obj = self.registry('product.product')

        prod_id = self._create_product({'ean13': '123456789012'})
        self.assertEqual('UC',
                         prod_obj.get_ean_type(cr, uid, prod_id, context=ctx))

    @skipIf(UNDER_DEVELOPMENT, UNDER_DEVELOPMENT_TEXT)
    def test_ean13_type(self):
        cr, uid, ctx = self.cr, self.uid, self.context
        prod_obj = self.registry('product.product')

        prod_id = self._create_product({'ean13': '7611330002706'})
        self.assertEqual('HE',
                         prod_obj.get_ean_type(cr, uid, prod_id, context=ctx))

    @skipIf(UNDER_DEVELOPMENT, UNDER_DEVELOPMENT_TEXT)
    def test_ean14_type(self):
        cr, uid, ctx = self.cr, self.uid, self.context
        prod_obj = self.registry('product.product')

        prod_id = self._create_product({'ean13': '12345678901234'})
        self.assertEqual('UC',
                         prod_obj.get_ean_type(cr, uid, prod_id, context=ctx))

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
