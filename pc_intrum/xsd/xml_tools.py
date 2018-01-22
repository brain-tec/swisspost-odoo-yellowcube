# b-*- encoding: utf-8 -*-
##############################################################################
#
#    Copyright (c) 2014 brain-tec AG (http://www.braintec-group.com)
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
from lxml import etree
import os
from string import maketrans
import codecs
import logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


intrum_schema_paths = {}
intrum_schema_paths['intrum_request'] = '{0}/CreditDecisionRequest142.xsd'.format(os.path.realpath(os.path.join(os.getcwd(), os.path.dirname(__file__))))
intrum_schema_paths['intrum_response'] = '{0}/CreditDecisionResponse142.xsd'.format(os.path.realpath(os.path.join(os.getcwd(), os.path.dirname(__file__))))
intrum_schemas = {}

xml_export_filename_translation = maketrans('- /\\', '____')


def _str(value):
    return str(value).decode('UTF-8')


def create_element(entity, text=None, attrib=None):
    _attrib = None
    if attrib is not None:
        _attrib = {}
        for key in attrib:
            if attrib[key] is not None:
                _attrib[key] = _str(attrib[key])
            else:
                logger.warning("XML-Arguments cannot be NULL <{0}:{1}>".format(entity, key))
    element = etree.Element(entity, attrib=attrib)
    if text is not None:
        element.text = _str(text)
    return element


def xml_to_string(xml_node):
    return etree.tostring(xml_node, xml_declaration=True, encoding='UTF-8', pretty_print=True)


def validate_xml(schema_name, xml_node):
    if schema_name not in intrum_schemas:
        try:
            with codecs.open(intrum_schema_paths[schema_name], 'r', 'UTF-8') as f:
                intrum_schemas[schema_name] = etree.XMLSchema(etree.parse(f))
        except:
            logger.error("Schema {0} not found".format(schema_name))
            return None
    if not intrum_schemas[schema_name].validate(xml_node):
        logger.error("[{0}] Error validating node: {1}".format(schema_name, intrum_schemas[schema_name].error_log.last_error))
        return intrum_schemas[schema_name].error_log.last_error
    else:
        return None

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
