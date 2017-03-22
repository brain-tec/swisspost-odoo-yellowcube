# -*- coding: utf-8 -*-
##############################################################################
#
#    Copyright (c) 2016 brain-tec AG (http://www.braintec-group.com)
#    All Right Reserved
#
#    See LICENSE file for full licensing details.
##############################################################################
from .xml_tools import XmlTools
from datetime import datetime
import logging
logger = logging.getLogger(__name__)

WAB_WAR_ORDERNO_GROUP = 'WAB_WAR_ORDERNO_GROUP'
WBL_WBA_ORDERNO_GROUP = 'WBL_WBA_ORDERNO_GROUP'


class FileProcessor(object):
    _backend = None
    _xml_type = None

    def __init__(self, backend, _type=None):
        self._backend = backend
        if _type is not None:
            self._xml_type = _type
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

    def log_message(self, msg, event=None, file_record=None, timestamp=False):
        logger.debug(msg)
        if timestamp:
            msg = '%s %s' % (datetime.now(), msg)
        self.backend_record.output_for_debug += msg
        if event:
            if event.info:
                event.info += msg
            else:
                event.info = msg
        if file_record:
            file_record.info += msg

    def yc_create_longname_element(self, tools, node, record, tag='Name%s',
                                   limit=4, name_limit=35):
        name = record.name

        name_parts = [name]
        partner_name_limit = limit - 1
        if len(name) > name_limit:
            node.append(tools.create_comment(name))
            name_parts = self._yc_chop_long_name(tools, name, name_limit,
                                                 partner_name_limit)

        if record.street2:
            name_parts.extend(self._yc_chop_long_name(tools, record.street2))

        idx = 1
        for part in name_parts:
            node.append(tools.create_element(tag % idx, part))
            idx += 1
            if idx > limit:
                break

    def _yc_chop_long_name(self, tools, name, name_limit=35,
                           partner_name_limit=1):
        idx = 1
        name_parts2 = []
        last_part = None
        name_words = map(tools._str, name.split())
        for word in name_words:
            if idx > partner_name_limit:
                break
            if last_part is None:
                last_part = \
                    word if len(word) < name_limit else word[:name_limit]
            elif len(last_part) + len(word) >= name_limit:
                idx += 1
                name_parts2.append(last_part)
                last_part = word
            else:
                last_part = "%s %s" % (last_part, word)
        return name_parts2

    def validate_file(self, file_record):
        xml_root = self.tools.open_xml(file_record.content,
                                       _type=self._xml_type)
        error = self.tools.validate_xml(xml_root)
        if error:
            self.log_message(error, file_record=file_record, timestamp=True)
            file_record.state = 'error'
            return False
        return True
