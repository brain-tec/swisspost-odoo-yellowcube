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


class test_yc_art(yellowcube_testcase):

    def setUp(self):
        super(test_yc_art, self).setUp()
        self.test_warehouse.stock_connect_id.write({'yc_enable_art_file': True, 'yc_enable_art_multifile': False})

        self.product_3 = self.browse_ref('product.product_product_3')
        if hasattr(self.product_3, 'action_validated'):
            self.product_3.write({
                'product_state': 'draft',
                'webshop_state': False,
                'target_state': 'active',
            })
            self.product_3.action_validated()
            self.product_3.action_in_production()
        self.product_3.write({
            'uom_id': self.ref('product.product_uom_unit'),
        })

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

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
