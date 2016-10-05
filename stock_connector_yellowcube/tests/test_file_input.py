# -*- coding: utf-8 -*-
##############################################################################
#
#    Copyright (c) 2016 brain-tec AG (http://www.braintec-group.com)
#    All Right Reserved
#
#    See LICENSE file for full licensing details.
##############################################################################
from . import test_base
from openerp.addons.stock_connector_yellowcube.models\
    import xml_tools
import logging
_logger = logging.getLogger(__name__)


class TestFileInput(test_base.TestBase):

    def test_files_are_detected(self):
        proc = self.backend.get_processor()
        for _type, _version in [
            ('war', '1.2'),
            ('wba', '1.2'),
            ('bar', '1.0'),
            ('bur', '1.0'),
        ]:

            tools = xml_tools.XmlTools(_type=_type.lower())
            file_root = tools.create_element(_type.upper())
            file_root.append(proc.yc_create_control_reference(tools,
                                                              _type.upper(),
                                                              _version))
            input_file = self.env['stock_connector.file'].create({
                'name': 'file.xml',
                'backend_id': self.backend.id,
                'content': tools.xml_to_string(file_root),
                'transmit': 'in',
            })
            self.backend.synchronize_backend()
            self.assertEquals(input_file.type, _type.upper(),
                              self.backend.output_for_debug)
            self.assertEquals(input_file.state, 'error',
                              'File is empty, so it must be '
                              'detected as an error')
