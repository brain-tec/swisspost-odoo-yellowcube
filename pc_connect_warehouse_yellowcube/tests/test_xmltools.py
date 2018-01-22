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
from openerp.tests import common
from ..xsd.xml_tools import XmlTools
from unittest2 import skipIf

UNDER_DEVELOPMENT = False
UNDER_DEVELOPMENT_TEXT = "Test was skipped because of being under development."


class test_xmltools(common.TransactionCase):

    @skipIf(UNDER_DEVELOPMENT, UNDER_DEVELOPMENT_TEXT)
    def test_xml_tools(self):
        """
        Test xml_tools: nspath, create_root, create_element
        """
        tools = XmlTools()
        # Nothing must fail in this code, straighforward testing
        root = tools.create_root('garden_of_eden')
        node_adan = tools.create_element('human', attrib={'name': 'adan'})
        node_tree_of_life = tools.create_element\
            ('tree', 'Ye tree that grants happines',
             attrib={'alignment': 'good'})
        node_tree_of_knowledge = tools.create_element(
            'tree', 'Ye tree that grants sorrow', attrib={'alignment': 'evil'})
        root.append(node_adan)
        root.append(node_tree_of_life)
        root.append(node_tree_of_knowledge)
        self.assertEqual(len(tools.nspath(root, '//tree')), 2,
                         "There are two trees in the garden.")
        self.assertEqual(len(tools.nspath(root, '//human')), 1,
                         "There is a sole human.")
        node_eva = tools.create_element('human', attrib={'name': 'eva'})
        root.append(node_eva)
        self.assertEqual(len(tools.nspath(root, '//human')), 2,
                         "Now there are two.")

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: