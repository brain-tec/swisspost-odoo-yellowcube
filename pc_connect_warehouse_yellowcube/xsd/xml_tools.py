# b-*- encoding: utf-8 -*-
##############################################################################
#
#    Copyright (c) 2014 brain-tec AG (http://www.brain-tec.ch)
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
import logging
from openerp.addons.pc_connect_master.utilities.misc import format_exception
logger = logging.getLogger(__name__)
from lxml import etree
import os
from string import maketrans
import codecs

__realpath = os.path.realpath(os.path.join(os.getcwd(), os.path.dirname(__file__)))

schema_paths = {}
schema_paths['art'] = '{0}/YellowCube_ART_REQUEST_Artikelstamm.xsd'.format(__realpath)
schema_paths['bar'] = '{0}/YellowCube_BAR_RESPONSE_ArticleList.xsd'.format(__realpath)
# schema_paths['bur'] = '{0}/YellowCube_BUR_BookingVoucher.xsd'.format(os.path.realpath(os.path.join(os.getcwd(), os.path.dirname(__file__))))
schema_paths['bur'] = '{0}/YellowCube_BUR_RESPONSE_GoodsMovements.xsd'.format(__realpath)
schema_paths['wab'] = '{0}/YellowCube_WAB_REQUEST_Warenausgangsbestellung.xsd'.format(__realpath)
schema_paths['war'] = '{0}/YellowCube_WAR_RESPONSE_GoodsIssueReply.xsd'.format(__realpath)
schema_paths['warr'] = schema_paths['war']
schema_paths['wbl'] = '{0}/YellowCube_WBL_REQUEST_SupplierOrders.xsd'.format(__realpath)
schema_paths['wea'] = '{0}/YellowCube_WEA_Delivery.xsd'.format(__realpath)
schema_paths['wba'] = '{0}/YellowCube_WBA_RESPONSE_GoodsReceiptReply.xsd'.format(__realpath)
schema_paths['w3_xmldsig'] = '{0}/xmldsig-core-schema.xsd'.format(__realpath)
schema_paths['gen'] = '{0}/YellowCube_GEN_RESPONSE_General.xsd'.format(__realpath)
schema_paths['gen_req'] = '{0}/YellowCube_GEN_STATUS_REQUEST_General.xsd'.format(__realpath)
schemas = {}

schema_namespaces = {}
schema_namespaces['art'] = 'https://service.swisspost.ch/apache/yellowcube/YellowCube_ART_REQUEST_Artikelstamm.xsd'
schema_namespaces['bar'] = 'https://service.swisspost.ch/apache/yellowcube/YellowCube_BAR_RESPONSE_ArticleList.xsd'
schema_namespaces['bar_req'] = 'https://service.swisspost.ch/apache/yellowcube/YellowCube_BAR_REQUEST_ArticleList.xsd'
schema_namespaces['bur'] = 'https://service.swisspost.ch/apache/yellowcube/YellowCube_BUR_RESPONSE_GoodsMovements.xsd'
schema_namespaces['bur_req'] = 'https://service.swisspost.ch/apache/yellowcube/YellowCube_BUR_REQUEST_GoodsMovements.xsd'
schema_namespaces['soapenv'] = 'http://schemas.xmlsoap.org/soap/envelope/'
schema_namespaces['soapsec'] = 'http://schemas.xmlsoap.org/soap/security/2000-12'
schema_namespaces['w3_xmldsig'] = 'http://www.w3.org/2000/09/xmldsig#'
schema_namespaces['soap'] = 'http://schemas.xmlsoap.org/wsdl/soap/'
schema_namespaces['wab'] = 'https://service.swisspost.ch/apache/yellowcube/YellowCube_WAB_REQUEST_Warenausgangsbestellung.xsd'
schema_namespaces['wba'] = 'https://service.swisspost.ch/apache/yellowcube/YellowCube_WBA_RESPONSE_GoodsReceiptReply.xsd'
schema_namespaces['wba_req'] = 'https://service.swisspost.ch/apache/yellowcube/YellowCube_WBA_REQUEST_GoodsReceiptReply.xsd'
schema_namespaces['warr'] = 'https://service.swisspost.ch/apache/yellowcube/YellowCube_WAR_RESPONSE_GoodsIssueReply.xsd'
schema_namespaces['war_req'] = 'https://service.swisspost.ch/apache/yellowcube/YellowCube_WAR_REQUEST_GoodsIssueReply.xsd'
schema_namespaces['wbl'] = 'https://service.swisspost.ch/apache/yellowcube/YellowCube_WBL_REQUEST_SupplierOrders.xsd'
schema_namespaces['gen_req'] = 'https://service.swisspost.ch/apache/yellowcube/YellowCube_GEN_STATUS_REQUEST_General.xsd'
schema_namespaces['gen'] = 'https://service.swisspost.ch/apache/yellowcube/YellowCube_GEN_RESPONSE_General.xsd'
schema_namespaces['wsse'] = 'http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-wssecurity-secext-1.0.xsd'
schema_namespaces['w3_xmlexcc14n'] = 'http://www.w3.org/2001/10/xml-exc-c14n#'

for prefix in schema_namespaces:
    etree.register_namespace(prefix, schema_namespaces[prefix])

xml_export_filename_translation = maketrans('- /\\', '____')


def open_xml(file_text, _type=None, print_error=True, repair=True, parser=None):
    try:
        node = etree.XML(str(file_text), parser=parser)
    except Exception as e:
        raise Warning(format_exception(e))
    if repair:
        if _type is None:
            _type = (node.xpath("//*[local-name() = 'ControlReference']/*[local-name() = 'Type']")
                     or
                     node.xpath("//ControlReference/Type"))[0].text.lower()
        err = validate_xml(_type.lower(), node, print_error)
        if err:
            try:
                node = repair_xml_file(node, _type.lower(),
                                       print_error=print_error)
            except Exception as e:
                raise Warning('{0}: {1}'.format(err, format_exception(e)))
    return node


def nspath(node, path):
    return node.xpath(path, namespaces=schema_namespaces)


def export_filename(original, context=None):
    if context is None:
        context = {}

    # global xml_export_filename_translation
    return original.replace('/', '').replace('-', '')
    # return "{0}{1}".format(context.get('filename_prefix', ''), original).translate(xml_export_filename_translation)


def _str(value):
    if type(value) is unicode:
        # If it's of type unicode, then str() will be in the range ord(character) < 128, thus will fail.
        return str(value.encode('utf-8')).decode('utf-8')
    else:
        return str(value).decode('UTF-8')


def create_root(entity):
    return etree.Element(entity.format(**schema_namespaces), nsmap=schema_namespaces)


def create_element(entity, text=None, attrib=None, ns=None):
    if ns is not None and ns not in entity:
        # We only add the namespace if it is said, and it is not already present
        entity = '{{{0}}}{1}'.format(ns, entity)
    _attrib = None
    if attrib is not None:
        _attrib = {}
        for key in attrib:
            if attrib[key] is not None:
                _attrib[key] = _str(attrib[key])
            else:
                logger.warning("XML-Arguments cannot be NULL <{0}:{1}>".format(entity, key))
    element = etree.Element(entity, attrib=_attrib, nsmap=schema_namespaces)
    if text is not None:
        element.text = _str(text)
    return element


def xml_to_string(xml_node, remove_ns=False, encoding='UTF-8', xml_declaration=True, pretty_print=True, **kargs):
    if remove_ns:
        def _remove_ns(node):
            if node.tag == etree.Comment:
                ret = etree.Comment(node.text)
            else:
                ret = create_element(node.tag[node.tag.index('}') + 1:], text=node.text, attrib=node.attrib, ns=None)
                for child in node:
                    ret.append(_remove_ns(child))
            return ret
        xml_node = _remove_ns(xml_node)
    return etree.tostring(xml_node, xml_declaration=xml_declaration, encoding=encoding, pretty_print=pretty_print, **kargs)


def repair_xml_file(xml, ns_key, print_error=True):
    if ns_key == 'war':
        ns_key = 'warr'
    if ns_key not in schema_namespaces:
        return xml
    ns = schema_namespaces[ns_key]
    xml_root = create_element(xml.tag, ns=ns)

    def _reformat_node(node):
        if node.tag == etree.Comment:
            return etree.Comment(node.text)
        ret = create_element(node.tag, node.text, node.attrib, ns)
        for child in node:
            ret.append(_reformat_node(child))
        return ret

    for child in xml:
        xml_root.append(_reformat_node(child))

    result = validate_xml(ns_key, xml_root, print_error=print_error)
    if result is None:
        return xml_root
    else:
        raise Warning(result)


def validate_xml(schema_name, xml_node, print_error=True):
    global schemas
    if schema_name not in schemas:
        try:
            with codecs.open(schema_paths[schema_name], 'r', 'UTF-8') as f:
                schemas[schema_name] = etree.XMLSchema(etree.parse(f))
        except Exception as e:
            err = "Schema {0} not found:\n{1}".format(schema_name, format_exception(e))
            if print_error:
                logger.error(err)
            return err
    if not schemas[schema_name].validate(xml_node):
        if print_error:
            logger.error("[{0}] Error validating node: {1}".format(schema_name, schemas[schema_name].error_log.last_error))
            logger.error('-' * 15)
            logger.error(xml_to_string(xml_node))
            logger.error('-' * 15)
        return schemas[schema_name].error_log.last_error
    else:
        return None

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
