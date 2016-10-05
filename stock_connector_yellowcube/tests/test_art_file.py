# -*- coding: utf-8 -*-
##############################################################################
#
#    Copyright (c) 2016 brain-tec AG (http://www.braintec-group.com)
#    All Right Reserved
#
#    See LICENSE file for full licensing details.
##############################################################################
from . import test_base
import logging
_logger = logging.getLogger(__name__)


class TestArtFile(test_base.TestBase):

    def setUp(self):
        super(TestArtFile, self).setUp()

    def test_create_art_file(self):
        _logger.info('Creating ART file')
        # At beginning, it must be empty
        self.assertEqual(len(self.backend.file_ids), 0)
        proc = self.backend.get_processor()
        # No products Files are still 0
        proc.yc_create_art([])
        self.assertEqual(len(self.backend.file_ids), 0)
        # Only one file
        self.backend.yc_parameter_create_art_multifile = False
        products = [
            self.browse_ref('product.product_product_7'),
            self.browse_ref('product.product_product_9'),
        ]
        proc.yc_create_art(products)
        self.assertEqual(len(self.backend.file_ids), 1)
        self.assertEqual(self.backend.file_ids[0].transmit, 'out')
        proc.yc_create_art(products)
        self.assertEqual(len(self.backend.file_ids), 1,
                         'ART files are created only once when needed')
        # Now with multifile
        self.backend.file_ids.unlink()
        self.backend.yc_parameter_create_art_multifile = True
        proc.yc_create_art(products)
        self.assertEqual(len(self.backend.file_ids), len(products))
