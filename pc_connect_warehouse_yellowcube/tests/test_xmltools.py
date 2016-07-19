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
from openerp.tests import common
from ..xml_abstract_factory import get_factory
from datetime import datetime
from ..xsd.xml_tools import nspath, create_root, create_element, xml_to_string, schema_namespaces
import unittest2
import re
from lxml import etree
from urllib import urlopen


class test_xmltools(common.TransactionCase):

    def test_xml_tools(self):
        """
        Test xml_tools: nspath, create_root, create_element
        """
        # Nothing must fail in this code, straighforward testing
        root = create_root('garden_of_eden')
        node_adan = create_element('human', attrib={'name': 'adan'})
        node_tree_of_life = create_element('tree', 'Ye tree that grants happines', attrib={'alignment': 'good'})
        node_tree_of_knowledge = create_element('tree', 'Ye tree that grants sorrow', attrib={'alignment': 'evil'})
        root.append(node_adan)
        root.append(node_tree_of_life)
        root.append(node_tree_of_knowledge)
        self.assertEqual(len(nspath(root, '//tree')), 2, "There are two trees in the garden.")
        self.assertEqual(len(nspath(root, '//human')), 1, "There is a sole human.")
        node_eva = create_element('human', attrib={'name': 'eva'})
        root.append(node_eva)
        self.assertEqual(len(nspath(root, '//human')), 2, "Now there are two.")

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
