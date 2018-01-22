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

from openerp.addons.pc_connect_master.utilities.ean import check_ean
from openerp.tests import common
from unittest2 import skipIf

UNDER_DEVELOPMENT = False
UNDER_DEVELOPMENT_TEXT = "Test was skipped because of being under development."


class test_ean(common.TransactionCase):

    def setUp(self):
        super(test_ean, self).setUp()
        self.context = {}

    @skipIf(UNDER_DEVELOPMENT, UNDER_DEVELOPMENT_TEXT)
    def test_ean_empty(self):
        """ An empty EAN is a valid one.
        """
        self.assertTrue(check_ean(''))
        self.assertTrue(check_ean(False))

    @skipIf(UNDER_DEVELOPMENT, UNDER_DEVELOPMENT_TEXT)
    def test_ean8(self):
        """ Every EAN of length 8 is a valid one, unless is not a number.
        """
        self.assertTrue(check_ean("12345678"))
        self.assertFalse(check_ean("1234567x"))
        self.assertFalse(check_ean("abcdefgh"))

    @skipIf(UNDER_DEVELOPMENT, UNDER_DEVELOPMENT_TEXT)
    def test_ean12(self):
        """ Every EAN of length 12 is a valid one, unless is not a number.
        """
        self.assertTrue(check_ean("123456789012"))
        self.assertFalse(check_ean("12345678901x"))
        self.assertFalse(check_ean("abcdefghijkl"))
        self.assertFalse(check_ean("1234567890ab"))

    @skipIf(UNDER_DEVELOPMENT, UNDER_DEVELOPMENT_TEXT)
    def test_ean14(self):
        """ Every EAN of length 14 is a valid one, unless is not a number.
        """
        self.assertTrue(check_ean("12345678901234"))
        self.assertFalse(check_ean("1234567890123x"))
        self.assertFalse(check_ean("abcdefghijklmn"))
        self.assertFalse(check_ean("1234567890abcd"))

    @skipIf(UNDER_DEVELOPMENT, UNDER_DEVELOPMENT_TEXT)
    def test_ean13(self):
        """ Every EAN of length 13 has to go through the usual validation
            for EAN13, provided by Odoo.
        """
        self.assertTrue(check_ean("7611330002706"))
        self.assertFalse(check_ean("7611330002705"))
        self.assertFalse(check_ean("761133000270x"))

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
