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
from openerp.addons.pc_connect_master.utilities.others import format_exception
from lxml import etree
import os
from string import maketrans
import codecs
import logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


__realpath = os.path.realpath(os.path.join(os.getcwd(), os.path.dirname(__file__)))

SCHEMA_PATHS = {}
SCHEMA_PATHS['art'] = '{0}/YellowCube_ART_REQUEST_Artikelstamm.xsd'.format(__realpath)
SCHEMA_PATHS['bar'] = '{0}/YellowCube_BAR_RESPONSE_ArticleList.xsd'.format(__realpath)
# schema_paths['bur'] = '{0}/YellowCube_BUR_BookingVoucher.xsd'.format(os.path.realpath(os.path.join(os.getcwd(), os.path.dirname(__file__))))
SCHEMA_PATHS['bur'] = '{0}/YellowCube_BUR_RESPONSE_GoodsMovements.xsd'.format(__realpath)
SCHEMA_PATHS['wab'] = '{0}/YellowCube_WAB_REQUEST_Warenausgangsbestellung.xsd'.format(__realpath)
SCHEMA_PATHS['war'] = '{0}/YellowCube_WAR_RESPONSE_GoodsIssueReply.xsd'.format(__realpath)
SCHEMA_PATHS['warr'] = SCHEMA_PATHS['war']
SCHEMA_PATHS['wbl'] = '{0}/YellowCube_WBL_REQUEST_SupplierOrders.xsd'.format(__realpath)
SCHEMA_PATHS['wea'] = '{0}/YellowCube_WEA_Delivery.xsd'.format(__realpath)
SCHEMA_PATHS['wba'] = '{0}/YellowCube_WBA_RESPONSE_GoodsReceiptReply.xsd'.format(__realpath)
SCHEMA_PATHS['w3_xmldsig'] = '{0}/xmldsig-core-schema.xsd'.format(__realpath)
SCHEMA_PATHS['gen'] = '{0}/YellowCube_GEN_RESPONSE_General.xsd'.format(__realpath)
SCHEMA_PATHS['gen_req'] = '{0}/YellowCube_GEN_STATUS_REQUEST_General.xsd'.format(__realpath)
SCHEMAS = {}

SCHEMA_NAMESPACES = {}
SCHEMA_NAMESPACES['art'] = 'https://service.swisspost.ch/apache/yellowcube/YellowCube_ART_REQUEST_Artikelstamm.xsd'
SCHEMA_NAMESPACES['bar'] = 'https://service.swisspost.ch/apache/yellowcube/YellowCube_BAR_RESPONSE_ArticleList.xsd'
SCHEMA_NAMESPACES['bar_req'] = 'https://service.swisspost.ch/apache/yellowcube/YellowCube_BAR_REQUEST_ArticleList.xsd'
SCHEMA_NAMESPACES['bur'] = 'https://service.swisspost.ch/apache/yellowcube/YellowCube_BUR_RESPONSE_GoodsMovements.xsd'
SCHEMA_NAMESPACES['bur_req'] = 'https://service.swisspost.ch/apache/yellowcube/YellowCube_BUR_REQUEST_GoodsMovements.xsd'
SCHEMA_NAMESPACES['soapenv'] = 'http://schemas.xmlsoap.org/soap/envelope/'
SCHEMA_NAMESPACES['soapsec'] = 'http://schemas.xmlsoap.org/soap/security/2000-12'
SCHEMA_NAMESPACES['w3_xmldsig'] = 'http://www.w3.org/2000/09/xmldsig#'
SCHEMA_NAMESPACES['soap'] = 'http://schemas.xmlsoap.org/wsdl/soap/'
SCHEMA_NAMESPACES['wab'] = 'https://service.swisspost.ch/apache/yellowcube/YellowCube_WAB_REQUEST_Warenausgangsbestellung.xsd'
SCHEMA_NAMESPACES['wba'] = 'https://service.swisspost.ch/apache/yellowcube/YellowCube_WBA_RESPONSE_GoodsReceiptReply.xsd'
SCHEMA_NAMESPACES['wba_req'] = 'https://service.swisspost.ch/apache/yellowcube/YellowCube_WBA_REQUEST_GoodsReceiptReply.xsd'
SCHEMA_NAMESPACES['warr'] = 'https://service.swisspost.ch/apache/yellowcube/YellowCube_WAR_RESPONSE_GoodsIssueReply.xsd'
SCHEMA_NAMESPACES['war_req'] = 'https://service.swisspost.ch/apache/yellowcube/YellowCube_WAR_REQUEST_GoodsIssueReply.xsd'
SCHEMA_NAMESPACES['wbl'] = 'https://service.swisspost.ch/apache/yellowcube/YellowCube_WBL_REQUEST_SupplierOrders.xsd'
SCHEMA_NAMESPACES['gen_req'] = 'https://service.swisspost.ch/apache/yellowcube/YellowCube_GEN_STATUS_REQUEST_General.xsd'
SCHEMA_NAMESPACES['gen'] = 'https://service.swisspost.ch/apache/yellowcube/YellowCube_GEN_RESPONSE_General.xsd'
SCHEMA_NAMESPACES['wsse'] = 'http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-wssecurity-secext-1.0.xsd'
SCHEMA_NAMESPACES['w3_xmlexcc14n'] = 'http://www.w3.org/2001/10/xml-exc-c14n#'

for prefix in SCHEMA_NAMESPACES:
    etree.register_namespace(prefix, SCHEMA_NAMESPACES[prefix])

xml_export_filename_translation = maketrans('- /\\', '____')


class XmlTools:

    schemas = SCHEMAS
    schema_namespaces = SCHEMA_NAMESPACES
    schema_paths = SCHEMA_PATHS

    def __init__(self, copy=False):
        if copy:
            self.schemas = SCHEMAS.copy()
            self.schema_paths = SCHEMA_PATHS.copy()
            self.schema_namespaces = SCHEMA_NAMESPACES.copy()

    def open_xml(self, file_text,
                 _type=None, print_error=True, repair=True, parser=None):
        try:
            node = etree.XML(str(file_text), parser=parser)
        except Exception as e:
            raise Warning(format_exception(e))
        if repair:
            if _type is None:
                _type = (node.xpath("//*[local-name() = 'ControlReference']/*[local-name() = 'Type']")
                         or
                         node.xpath("//ControlReference/Type"))[0].text.lower()
            err = self.validate_xml(_type.lower(), node, print_error)
            if err:
                try:
                    node = self.repair_xml_file(node, _type.lower(),
                                                print_error=print_error)
                except Exception as e:
                    raise Warning('{0}: {1}'.format(err, format_exception(e)))
        return node

    def nspath(self, node, path):
        return node.xpath(path, namespaces=self.schema_namespaces)

    def export_filename(self, original, context=None):
        if context is None:
            context = {}

        # global xml_export_filename_translation
        return original.replace('/', '').replace('-', '')
        # return "{0}{1}".format(context.get('filename_prefix', ''), original).translate(xml_export_filename_translation)

    def _str(self, value):
        if type(value) is unicode:
            # If it's of type unicode, then str() will be in the range ord(character) < 128, thus will fail.
            return str(value.encode('utf-8')).decode('utf-8')
        else:
            return str(value).decode('UTF-8')

    def create_root(self, entity):
        return etree.Element(
            entity.format(**self.schema_namespaces),
            nsmap=self.schema_namespaces)

    def create_element(self, entity, text=None, attrib=None, ns=None):
        if ns is not None and ns not in entity:
            # We only add the namespace if it is said,
            #  and it is not already present
            entity = '{{{0}}}{1}'.format(ns, entity)
        _attrib = None
        if attrib is not None:
            _attrib = {}
            for key in attrib:
                if attrib[key] is not None:
                    _attrib[key] = self._str(attrib[key])
                else:
                    logger.warning("XML-Arguments cannot be NULL <{0}:{1}>"
                                   .format(entity, key))
        element = etree.Element(entity, attrib=_attrib,
                                nsmap=self.schema_namespaces)
        if text is not None:
            element.text = self._str(text)
        return element

    def _remove_ns(self, node):
        if node.tag == etree.Comment:
            ret = etree.Comment(node.text)
        else:
            ret = self.create_element(node.tag[node.tag.index('}') + 1:],
                                      text=node.text, attrib=node.attrib,
                                      ns=None)
            for child in node:
                ret.append(self._remove_ns(child))
        return ret

    def xml_to_string(self, xml_node, remove_ns=False, encoding='UTF-8',
                      xml_declaration=True, pretty_print=True, **kargs):
        if remove_ns:
            xml_node = self._remove_ns(xml_node)
        return etree.tostring(xml_node, xml_declaration=xml_declaration,
                              encoding=encoding, pretty_print=pretty_print,
                              **kargs)

    def _reformat_node(self, node, ns):
        if node.tag == etree.Comment:
            return etree.Comment(node.text)
        ret = self.create_element(node.tag, node.text, node.attrib, ns)
        for child in node:
            ret.append(self._reformat_node(child, ns))
        return ret

    def repair_xml_file(self, xml, ns_key, print_error=True):
        if ns_key == 'war':
            ns_key = 'warr'
        if ns_key not in self.schema_namespaces:
            return xml
        ns = self.schema_namespaces[ns_key]
        xml_root = self.create_element(xml.tag, ns=ns)

        for child in xml:
            xml_root.append(self._reformat_node(child, ns))

        result = self.validate_xml(ns_key, xml_root, print_error=print_error)
        if result is None:
            return xml_root
        else:
            raise Warning(result)

    def validate_xml(self, schema_name, xml_node, print_error=True):
        if not self.schemas.get(schema_name, False):
            try:
                with codecs.open(self.schema_paths[schema_name], 'r', 'UTF-8') as f:
                    self.schemas[schema_name] = etree.XMLSchema(etree.parse(f))
            except Exception as e:
                err = "Schema {0} not found:\n{1}".format(
                    schema_name, format_exception(e))
                if print_error:
                    logger.error(err)
                return err
        if not self.schemas[schema_name].validate(xml_node):
            if print_error:
                logger.error("[{0}] Error validating node: {1}".format(
                    schema_name,
                    self.schemas[schema_name].error_log.last_error))
                logger.error('-' * 15)
                logger.error(self.xml_to_string(xml_node))
                logger.error('-' * 15)
            return self.schemas[schema_name].error_log.last_error
        else:
            return None


# Read the following comment-block carefully before you have to create a new
# connector that tries to reuse portions of the original one.
#
# These are my findings on how to extend this code, which may prove wrong
# in the future, but for now they have worked.
#
#
#
# For some reason, in the past, instead of making each connection have its own
# set of XML tools, that would allow to have different XSDs and different
# procedures to validate them and so on, it was decided to create a global
# variable (the one below, called _XmlTools) that did this.
#
# This variable is used on the Yellowcube connector, and is stored in the
# variable self.xml_tools. This is done in the __init__() of the class
# xml_abstract_factory. So when you use self.xml_tools within the model, you
# are actually using the global variable defined below, _XmlTools. The problem
# is that almost all the code relies on this self.xml_tools (in other words:
# almost all the code relies on a global variable) so it has be handled with
# tons of care.
#
# In particular, this poses the problem that, if you want to change the XSD
# for a given type of file you can not do it.
#
# So the solution that was used in the past was using a global like _XmlTools
# per each tipe of connection.
#
# So, how to extend the code so that it uses a new XSD?
#
# Follow the next steps:
#
# 1. Create a new instance of the 'global', that has to be unique per each
#    connection. So (this is for the programmer to ensure) make sure there is
#    ***just one*** 'copy' of the original _XmlTools on each connector that
#    requires an extension to the original _XmlTools. This is done this way:
#
#   _NewXmlTools = xml_tools.XmlTools(copy=True)
#   _NewXmlTools.schema_paths['wab'] = '/home/xsd/NEW_WAB.xsd'
#   _NewXmlTools.schemas['wab'] = False
#
#   This will be the case for the first type of file you want to change the
#   XSD (in this example it was the WAB). For for the next times, you have to
#   re-use that copy of the variable that you created, this way:
#
#   from .yellowcube_wab_xml_factory_ext import _NewXmlTools
#   _NewXmlTools.schema_paths['wbl'] = '/home/xsd/NEW_WBL.xsd'
#   _NewXmlTools.schemas['wbl'] = False
#
#   You may be wondering why we use the parameter copy=True. It's because
#   otherwise, the constructor will load again the XSDs and namespaces defined
#   by default as, again, globals. So you want to make a 'real' copy of them
#   (I mean, using copy()) instead of just making an assignation, that would
#   be just a reference to them.
#
# 2. Since a connection is a char, and not a model, and thus it doesn't have
#    its own set of XML-tools, we have to know somehow which kind of XML-tools
#    from those that we have (either the original one, defined below in this
#    current file, or the one that was created as explained in the step 1) is
#    going to be used be used.
#
#    But with this you are going to face two kinds of problems:
#
#        1. Since all the classes for the Yellowcube files inherit from
#           xml_abstract_factory, in the end they all resort to using
#           self.xml_tools, which is actually, as said before, a reference to
#           the original _XmlTools (again: the one defined below in this
#           current file). So you have to make sure that when the code which
#           is up in the inheritance is executed, that self.xml_tools points
#           to the XmlTools that you want to use, in this particular example
#           _NewXmlTools.
#        2. Sometimes you don't have a clear way of knowing which kind of
#           XMLTools you need to use. For instance, you can check the type
#           of connection, but sometimes the connection is still Yellowcube
#           but you have to use a different set of XMLTools.
#
#    So for problem #1 you need to keep track of both the original XmlTools and
#    the new one, as is done in e.g.
#
#    def __init__(self, *args, **kwargs):
#        super(YellowcubeWblXmlFactoryExt, self).__init__(*args, **kwargs)
#        self._yc_xml_tools = self.xml_tools
#        self._new_xml_tools = _NewXmlTools
#
#    so _yc_xml_tools points to the original one (remember, self.xml_tools
#    is defined in the mother-class, and points to the original _XmlTools
#    defined below) and the new one defined.
#
#    And for problem #2 you need a way to know which set of XMLTools you are
#    going to use (in this particular example, whether to use _yc_xml_tools
#    of _new_xml_tools), which will be the one that you'll assign to
#    self.xml_tools when calling the methods (because remember: codes higher
#    in the inheritanca are going to use self.xml_tools). Once you have a way
#    of knowing which type of XMLTools to use, you set them e.g. as in:
#
#        if self._is_incoming_wbl():
#            self.xml_tools = self._new_xml_tools
#        else:
#            self.xml_tools = self._yc_xml_tools
#        return super(YellowcubeWblXmlFactoryExt, self).import_file(file_text)
#
#    and then call the code upper in the hierarchy as done, with super().
#
# All that was for extending the stock.connect.file. To extend the model
# stock.connect, it seems you have to pass the XMLTools to use as a flag in
# the context, this way:
#
#        ctx['xml_tools'] = _NewXmlTools
#


_XmlTools = XmlTools()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
