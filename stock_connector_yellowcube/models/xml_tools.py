# -*- coding: utf-8 -*-
##############################################################################
#
#    Copyright (c) 2016 brain-tec AG (http://www.braintec-group.com)
#    All Right Reserved
#
#    See LICENSE file for full licensing details.
##############################################################################
import logging
from lxml import etree
import os
import codecs
from datetime import datetime
import traceback
import sys

logger = logging.getLogger(__name__)

__realpath = os.path.realpath(os.path.join(os.getcwd(),
                                           os.path.dirname(__file__)))

SCHEMA_PATHS = {}
SCHEMA_PATHS['art'] = '{0}/xsd/'\
    'YellowCube_ART_REQUEST_Artikelstamm.xsd'.format(__realpath)
SCHEMA_PATHS['bar'] = '{0}/xsd/'\
    'YellowCube_BAR_RESPONSE_ArticleList.xsd'.format(__realpath)
# SCHEMA_PATHS['bur'] =
#  '{0}/xsd/YellowCube_BUR_BookingVoucher.xsd'
#  .format(os.path.realpath(__realpath)
SCHEMA_PATHS['bur'] = '{0}/xsd/'\
    'YellowCube_BUR_RESPONSE_GoodsMovements.xsd'.format(__realpath)
SCHEMA_PATHS['wab'] = '{0}/xsd'\
    '/YellowCube_WAB_REQUEST_Warenausgangsbestellung.xsd'\
    .format(__realpath)
SCHEMA_PATHS['war'] = '{0}/xsd/'\
    'YellowCube_WAR_RESPONSE_GoodsIssueReply.xsd'.format(__realpath)
# SCHEMA_PATHS['warr'] = SCHEMA_PATHS['war']
SCHEMA_PATHS['wbl'] = '{0}/xsd/'\
    'YellowCube_WBL_REQUEST_SupplierOrders.xsd'.format(__realpath)
# SCHEMA_PATHS['wea'] =
#  '{0}/xsd/YellowCube_WEA_Delivery.xsd'.format(__realpath)
SCHEMA_PATHS['wba'] = '{0}/xsd/'\
    'YellowCube_WBA_RESPONSE_GoodsReceiptReply.xsd'.format(__realpath)
# SCHEMA_PATHS['w3_xmldsig'] =
#  '{0}/xsd/xmldsig-core-schema.xsd'.format(__realpath)
# SCHEMA_PATHS['gen'] =
#  '{0}/xsd/YellowCube_GEN_RESPONSE_General.xsd'.format(__realpath)
# SCHEMA_PATHS['gen_req'] =
#  '{0}/xsd/YellowCube_GEN_STATUS_REQUEST_General.xsd'.format(__realpath)

SCHEMA_NAMESPACES = {}
SCHEMA_NAMESPACES['art'] = 'https://service.swisspost.ch/apache/yellowcube/'\
    'YellowCube_ART_REQUEST_Artikelstamm.xsd'
SCHEMA_NAMESPACES['bar'] = 'https://service.swisspost.ch/apache/yellowcube/'\
    'YellowCube_BAR_RESPONSE_ArticleList.xsd'
SCHEMA_NAMESPACES['bar_req'] = 'https://service.swisspost.ch/apache/'\
    'yellowcube/YellowCube_BAR_REQUEST_ArticleList.xsd'
SCHEMA_NAMESPACES['bur'] = 'https://service.swisspost.ch/apache/yellowcube/'\
    'YellowCube_BUR_RESPONSE_GoodsMovements.xsd'
SCHEMA_NAMESPACES['bur_req'] = 'https://service.swisspost.ch/apache/'\
    'yellowcube/YellowCube_BUR_REQUEST_GoodsMovements.xsd'
SCHEMA_NAMESPACES['soapenv'] = 'http://schemas.xmlsoap.org/soap/envelope/'
SCHEMA_NAMESPACES['soapsec'] = 'http://schemas.xmlsoap.org/soap/security/'\
    '2000-12'
SCHEMA_NAMESPACES['w3_xmldsig'] = 'http://www.w3.org/2000/09/xmldsig#'
SCHEMA_NAMESPACES['soap'] = 'http://schemas.xmlsoap.org/wsdl/soap/'
SCHEMA_NAMESPACES['wab'] = 'https://service.swisspost.ch/apache/yellowcube/'\
    'YellowCube_WAB_REQUEST_Warenausgangsbestellung.xsd'
SCHEMA_NAMESPACES['wba'] = 'https://service.swisspost.ch/apache/yellowcube/'\
    'YellowCube_WBA_RESPONSE_GoodsReceiptReply.xsd'
SCHEMA_NAMESPACES['wba_req'] = 'https://service.swisspost.ch/apache/'\
    'yellowcube/YellowCube_WBA_REQUEST_GoodsReceiptReply.xsd'
SCHEMA_NAMESPACES['war'] = 'https://service.swisspost.ch/apache/yellowcube/'\
    'YellowCube_WAR_RESPONSE_GoodsIssueReply.xsd'
SCHEMA_NAMESPACES['war_req'] = 'https://service.swisspost.ch/apache/'\
    'yellowcube/YellowCube_WAR_REQUEST_GoodsIssueReply.xsd'
SCHEMA_NAMESPACES['wbl'] = 'https://service.swisspost.ch/apache/yellowcube/'\
    'YellowCube_WBL_REQUEST_SupplierOrders.xsd'
SCHEMA_NAMESPACES['gen_req'] = 'https://service.swisspost.ch/apache/'\
    'yellowcube/YellowCube_GEN_STATUS_REQUEST_General.xsd'
SCHEMA_NAMESPACES['gen'] = 'https://service.swisspost.ch/apache/yellowcube/'\
    'YellowCube_GEN_RESPONSE_General.xsd'
SCHEMA_NAMESPACES['wsse'] = 'http://docs.oasis-open.org/wss/2004/01/'\
    'oasis-200401-wss-wssecurity-secext-1.0.xsd'
SCHEMA_NAMESPACES['w3_xmlexcc14n'] = 'http://www.w3.org/2001/10/xml-exc-c14n#'

for prefix in SCHEMA_NAMESPACES:
    etree.register_namespace(prefix, SCHEMA_NAMESPACES[prefix])


class XmlTools:

    default_ns = None
    print_error = True
    repair = False
    timestamp = False

    def __init__(self, _type=None, default_ns=None,
                 print_error=True, repair=False,
                 schema_paths=None,
                 schema_namespaces=None):

        self.schemas = {}

        if schema_paths is not None:
            self.schema_paths = SCHEMA_PATHS.copy()
            self.schema_paths.update(schema_paths)
        else:
            self.schema_paths = SCHEMA_PATHS
        if schema_namespaces is not None:
            self.schema_namespaces = SCHEMA_NAMESPACES.copy()
            self.schema_namespaces.update(schema_namespaces)
        else:
            self.schema_namespaces = SCHEMA_NAMESPACES
        if _type:
            self._type = _type.lower()
        if default_ns:
            self.default_ns = default_ns
        elif self._type in self.schema_namespaces:
            self.default_ns = self.schema_namespaces[self._type]
        self.print_error = print_error
        self.repair = repair
        now = datetime.now()
        ts_args = [now.year, now.month, now.day,
                   now.hour, now.hour, now.minute]
        self.timestamp = ('{0:04d}{1:02d}{2:02d}'
                          '{3:02d}{4:02d}{5:02d}').format(*ts_args)

    def format_exception(self, e):
        _traceback = traceback.format_exc(limit=10)
        if isinstance(e, IOError):
            return "{0}\n{1}\n{2}\n{3}\n{4}".format(e,
                                                    e.errno or '',
                                                    e.strerror or '',
                                                    sys.exc_info()[0] or '',
                                                    _traceback)
        else:
            return "{0}\n{1}\n{2}".format(e,
                                          sys.exc_info()[0] or '',
                                          _traceback)

    def open_xml(self, file_text, _type=None, parser=False,
                 avoid_unicode_error=True):
        """
        :param file_text: content of the file
        :param _type: type to validate against using XSD
        :param parser: None is a valid value, so False as default means to use
            recommended parser
        :param avoid_unicode_error: Try to fix an error with unicode on XML
        :return:
        """
        if parser is False:
            parser = etree.XMLParser(recover=True)
        node = None
        try:
            node = etree.XML(file_text, parser=parser)
        except Exception as e:
            if avoid_unicode_error and 'Unicode strings with ' \
                                       'encoding declaration are ' \
                                       'not supported.' in str(e):
                try:
                    declaration_end = file_text.index('?>') + 2
                    node = etree.XML(file_text[declaration_end:],
                                     parser=parser)
                except Exception as e2:
                    logger.error(self.format_exception(e2))
                    node = None
            if node is None:
                raise Warning(self.format_exception(e))
        if self.repair:
            if _type is None:
                _type = (node.xpath("//*[local-name() = 'ControlReference']"
                         "/*[local-name() = 'Type']") or
                         node.xpath("//ControlReference/Type"))[0].text.lower()
            err = self.validate_xml(_type.lower(), node, self.print_error)
            if err:
                try:
                    node = self.repair_xml_file(node, _type.lower())
                except Exception as e:
                    raise Warning('{0}: {1}'.format(err,
                                                    self.format_exception(e)))
        return node

    def nspath(self, node, path):
        return node.xpath(path, namespaces=self.schema_namespaces)

    def _str(self, value):
        if isinstance(value, unicode):
            return str(value.encode('UTF-8')).decode('UTF-8')
        else:
            return str(value).decode('UTF-8',)

    def create_comment(self, text):
        return etree.Comment(text=text)

    def create_element(self, entity, text=None, attrib=None, ns=None):
        ns = ns or self.default_ns
        if ns is not None and ns not in entity:
            entity = '{{{0}}}{1}'.format(ns, entity)
        _attrib = None
        if attrib is not None:
            _attrib = {}
            for key in attrib:
                if attrib[key] is not None:
                    _attrib[key] = self._str(attrib[key])
                else:
                    logger.warning(
                        "XML-Arguments cannot be NULL <{0}:{1}>".format(entity,
                                                                        key)
                        )
        element = etree.Element(entity, attrib=_attrib,
                                nsmap=self.schema_namespaces)
        if text is not None:
            element.text = self._str(text)
        return element

    def xml_to_string(self, xml_node, remove_ns=False, encoding='unicode',
                      xml_declaration=True, pretty_print=True, **kargs):
        if remove_ns:
            def _remove_ns(node):
                if node.tag == etree.Comment:
                    ret = etree.Comment(node.text)
                else:
                    ret = self.create_element(node.tag[node.tag.index('}') + 1:
                                                       ],
                                              text=node.text,
                                              attrib=node.attrib,
                                              ns=None)
                    for child in node:
                        ret.append(_remove_ns(child))
                return ret
            xml_node = _remove_ns(xml_node)
        if encoding.lower() == 'unicode':
            xml_declaration = False
        return etree.tostring(xml_node, xml_declaration=xml_declaration,
                              encoding=encoding, pretty_print=pretty_print,
                              **kargs)

    def repair_xml_file(self, xml, ns_key):
        if ns_key == 'war':
            ns_key = 'warr'
        if ns_key not in self.schema_namespaces:
            return xml
        ns = self.schema_namespaces[ns_key]
        xml_root = self.create_element(xml.tag, ns=ns)

        def _reformat_node(node):
            if node.tag == etree.Comment:
                return etree.Comment(node.text)
            ret = self.create_element(node.tag, node.text, node.attrib, ns)
            for child in node:
                ret.append(_reformat_node(child))
            return ret

        for child in xml:
            xml_root.append(_reformat_node(child))

        result = self.validate_xml(ns_key, xml_root)
        if result is None:
            return xml_root
        else:
            raise Warning(result)

    def validate_xml(self, xml_node, schema_name=None):
        if not schema_name:
            schema_name = self._type
        if schema_name is None or schema_name not in self.schema_paths:
            return None
        if schema_name not in self.schemas:
            try:
                with codecs.open(self.schema_paths[schema_name],
                                 'r', 'UTF-8') as f:
                    self.schemas[schema_name] = etree.XMLSchema(etree.parse(f))
            except Exception as e:
                err = "Schema {0} not found:\n{1}".format(
                    schema_name,
                    self.format_exception(e))
                if self.print_error:
                    logger.error(err)
                return err
        if not self.schemas[schema_name].validate(xml_node):
            if self.print_error:
                logger.error(
                    "[{0}] Error validating node: {1}".format(
                        schema_name,
                        self.schemas[schema_name].error_log.last_error))
                logger.error('-' * 15)
                logger.error(self.xml_to_string(xml_node))
                logger.error('-' * 15)
            return self.schemas[schema_name].error_log.last_error
        else:
            return None
