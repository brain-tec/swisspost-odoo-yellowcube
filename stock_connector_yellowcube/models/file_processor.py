# -*- coding: utf-8 -*-
##############################################################################
#
#    Copyright (c) 2016 brain-tec AG (http://www.braintec-group.com)
#    All Right Reserved
#
#    See LICENSE file for full licensing details.
##############################################################################
from .xml_tools import XmlTools

WAB_WAR_ORDERNO_GROUP = 'WAB_WAR_ORDERNO_GROUP'
WBL_WBA_ORDERNO_GROUP = 'WBL_WBA_ORDERNO_GROUP'


class FileProcessor(object):
    _backend = None

    def __init__(self, backend, _type=None):
        self._backend = backend
        if _type is not None:
            self.tools = XmlTools(_type=_type)

    def __getattr__(self, attr):
        if attr not in self.__dict__:
            return getattr(self._backend, attr)
        else:
            return getattr(self, attr)

    def path(self, node, path):
        """
        :rtype: lxml.etree._ElementTree._ElementTree
        """
        return self.tools.nspath(node, path)

    def get_binding(self, *args):
        return self.backend_record.get_binding(*args)

    def find_binding(self, *args):
        return self.backend_record.find_binding(*args)
