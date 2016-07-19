# b-*- encoding: utf-8 -*-
##############################################################################
#
#    Copyright (c) ${year} brain-tec AG (http://www.brain-tec.ch)
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
from openerp.osv import orm
import unittest2
import logging
logger = logging.getLogger(__name__)


class test_ch_zip(common.TransactionCase):

    def setUp(self):
        super(test_ch_zip, self).setUp()

        self.context = {}

        self.res_partner = self.registry('res.partner')

    def tearDown(self):
        super(test_ch_zip, self).tearDown()

    def test_create_partner_zip_1000(self):
        """
        Create a partner from Switzerland with Zip Code equal to 1000.
        """

        partner_id = self.res_partner.create(self.cr, self.uid, {'name': 'test 1000', 'lastname': 'test zip 1000',
                                                                 'country_id': 44, 'zip': '1000',
                                                                 'firstname': 'test zip 1000'},
                                             context=self.context)

        partner = self.res_partner.browse(self.cr, self.uid, partner_id, context=self.context)

        self.assertEqual(partner.zip, '1000', "the ZIP value is : '1000'")

    def test_create_partner_zip_9999(self):
        """
        Create a partner from Switzerland with Zip Code equal to 9999.
        """

        partner_id = self.res_partner.create(self.cr, self.uid, {'name': 'test 9999', 'lastname': 'test zip 9999',
                                                                 'country_id': 44, 'zip': '9999',
                                                                 'firstname': 'test zip 1000'},
                                             context=self.context)

        partner = self.res_partner.browse(self.cr, self.uid, partner_id, context=self.context)

        self.assertEqual(partner.zip, '9999', "the ZIP value is : '9999'")

    def test_create_partner_zip_from_1000_to_9999(self):
        """
        The zip fiels has to be a value between 1000 and 9999.
        Also it is tested if the Zip has whitespaces (' XXXX', 'XXXX ', ' XXXX ')
        """

        for case in ['{0}', ' {0}', '{0} ', ' {0} ']:
            for i in ['1000', '1001', '9998', '9999']:
                values = {}
                values['name'] = 'test {0}'.format(i)
                values['country_id'] = 44
                values['zip'] = case.format(i)
                values['firstname'] = 'test {0}'.format(i)
                values['lastname'] = 'test {0}'.format(i)
                try:
                    partner_id = self.res_partner.create(self.cr, self.uid,
                                                         values, context=self.context)
                    partner = self.res_partner.browse(self.cr, self.uid, partner_id, context=self.context)
                except:
                    logger.error(" the invalid zip is '{0}'".format(values['zip']))
                    raise

                self.assertEqual(partner.zip, str(i), "the ZIP value is : '{0}'".format(values['zip']))

    def test_create_partner_zip_999(self):
        """
        The zip field has to be greater than 999
        """

        for case in ['999', '0999']:
            with self.assertRaises(orm.except_orm) as cm:
                self.res_partner.create(self.cr, self.uid, {'name': 'test 999', 'lastname': 'test zip 999',
                                                            'country_id': 44, 'zip': case,
                                                            'firstname': 'test zip 999'},
                                        context=self.context)
            the_exception = cm.exception
            self.assertEqual(the_exception[0], 'ValidateError')

    def test_create_partner_zip_10000(self):
        """
        the zip field has to be less than 10000 and no more than 4 character
        """
        for case in ['010000', '10000']:
            with self.assertRaises(orm.except_orm) as cm:
                self.res_partner.create(self.cr, self.uid, {'name': 'test 10000', 'lastname': 'test zip 10000',
                                                            'country_id': 44, 'zip': case,
                                                            'firstname': 'test zip 10000'},
                                        context=self.context)
            the_exception = cm.exception
            self.assertEqual(the_exception[0], 'ValidateError')

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
