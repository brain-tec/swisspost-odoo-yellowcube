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
from yellowcube_testcase import yellowcube_testcase, subTest
from ..xml_abstract_factory import get_factory
from ..xsd.xml_tools import nspath, create_root, create_element, xml_to_string, schema_namespaces
import unittest2


@subTest('sale_process', 'base_test')
@subTest('sale_process', 'partial_delivery', skip_test="Not yet defined test", partial_delivery=True)
@subTest('sale_process', 'missing_wab_ret', missing_wab_ret=True)
@subTest('sale_process', 'strange_characters_partner', strange_characters_partner=True)
class test_yc_wab_war(yellowcube_testcase):

    def setUp(self):
        super(test_yc_wab_war, self).setUp()
        self.test_warehouse.stock_connect_id.write({'yc_enable_wab_file': True, 'yc_enable_war_file': True})

    def sale_process(self, missing_wab_ret=False, partial_delivery=False, strange_characters_partner=False):
        """
        This test, tests the workflow followed after a sale is closed
        """
        self._print_sale_pdfs()
        cr, uid, ctx = self.cr, self.uid, self.context
        ctx['show_errors'] = False
        wab_factory = get_factory(self.test_warehouse.env, "wab", context=ctx)

        if strange_characters_partner:
            partner = self.test_sale.partner_id
            partner.write({'street': 'strange 0ñ1ç2ü3ñ4~5--ème étage'})
        # First we check some pre-conditions
        self.assertGreater(len(self.test_sale.picking_ids), 0, 'The sale has some pickings')

        # Here we create a WAB file for an order
        wab_factory.generate_files([('sale_id', '=', self.test_sale.id)])
        pick_out_id = self.pick_obj.search(cr, uid, [('sale_id', '=', self.test_sale.id)], context=ctx)[0]
        pick_out = self.pick_obj.browse(cr, uid, pick_out_id, ctx)
        self.assertNotIn(pick_out.state, ['done'], 'The stock.picking is not closed, until everything is delivered')
        name = '.*_wab_{0}.*OUT.*\.xml'.format(self.test_sale.name)
        self.assert_(self._yc_files(name), 'A WAB file is created')
        # Now we check some fields
        result_wab_file = self._yc_files(name)[0]
        wab_node = self._get_file_node(result_wab_file)
        self._save_node(wab_node, 'wab', path='//CustomerOrderNo')
        self.assertEqual(len([x for x in self.test_sale.order_line if x.product_id.type != 'service']), len(nspath(wab_node, '//Position')), 'A position for each item in the SO')
        # Here we create the response WAR file, accepting everything
        war_node = self._create_mirror_war_from_wab(wab_node)
        self._save_node(war_node, 'war', path='//warr:CustomerOrderNo')
        war_factory = get_factory(self.test_warehouse.env, "war", context=ctx)
        war_factory.import_file(xml_to_string(war_node))
        # Now we check the stock.picking state
        pick_out = self.pick_obj.browse(cr, uid, pick_out_id, ctx)
        self.assertIn(pick_out.state, ['done'], 'The stock.picking is closed, once everything is delivered')

        # Now for the return of the goods
        if not missing_wab_ret:
            # Here we create a return for the order
            logger.debug("Creating WAB-RET")
            ctx['active_id'] = pick_out.id
            pick_ret_id = self.pick_ret_obj.create(cr, uid, {'yellowcube_return': True, 'yellowcube_return_reason': 'R03'}, context=ctx)
            pick_in_id = eval(self.pick_ret_obj.create_returns(cr, uid, [pick_ret_id], context=ctx)['domain'])[0][2][0]
            pick_in = self.pick_obj.browse(cr, uid, pick_in_id, ctx)
            pick_in.write({'yellowcube_return_reason': 'R01'})
            pick_in.action_confirm()
            self.assertNotIn(pick_in.state, ['done'], 'The stock.picking is not closed, until everything is delivered')
            wab_factory.generate_files([('id', '=', pick_in_id)])
            name = '.*_wab_{0}.*IN.*\.xml'.format(self.test_sale.name)
            self.assert_(self._yc_files(name), 'A WAB file is created')
            # Now we check some fields
            result_wab_file = self._yc_files(name)[0]
            wab_node = self._get_file_node(result_wab_file)
            self.assertEqual(len([x for x in self.test_sale.order_line if x.product_id.type != 'service']), len(nspath(wab_node, '//Position')), 'A position for each item in the SO')

        # Here we create the response WAR file, accepting everything
        war_node = self._create_mirror_war_from_wab(wab_node, returngoods=True)
        self._save_node(war_node, 'war', path='//warr:CustomerOrderNo')
        if not missing_wab_ret:
            war_factory.import_file(xml_to_string(war_node))
            # Now we check the stock.picking state
            pick_in = self.pick_obj.browse(cr, uid, pick_in_id, ctx)
            self.assertIn(pick_in.state, ['done'], 'The stock.picking is closed, once everything is delivered')
        else:
            with self.assertRaises(Warning):
                war_factory.import_file(xml_to_string(war_node))

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
