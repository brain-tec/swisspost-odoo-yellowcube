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
        self.ugly_product = self.env['product.product'].create({
            'name': "qwertyuiop"
                    "asdfghjklñ"
                    "zxcvbnm,.-"
                    "äëïöüÄËÏÖÜ"
                    "long.-name"
                    "qwertyuiop"
                    "asdfghjklñ"
                    "zxcvbnm,.-"
                    "äëïöüÄËÏÖÜ"
                    "long.-name",
            'type': 'product',
            'default_code': 'ugly-product-with-ugliness',
        })

    def test_create_art_file(self):
        _logger.info('Creating ART file')
        # At beginning, it must be empty
        self.assertEqual(len(self.backend_files_for_test()), 0)
        proc = self.backend.get_processor()
        # No products Files are still 0
        proc.yc_create_art([])
        self.assertEqual(len(self.backend_files_for_test()), 0)
        # Only one file
        self.backend.yc_parameter_create_art_multifile = False
        products = [
            self.browse_ref('product.product_product_7'),
            self.browse_ref('product.product_product_9'),
            self.ugly_product,
        ]
        proc.yc_create_art(products)
        backend_files = self.backend_files_for_test()
        self.assertEqual(len(backend_files), 1, self.backend.output_for_debug)
        self.assertEqual(backend_files[0].transmit, 'out')
        old_names = backend_files.mapped('name')
        self.assertEquals(len(products), 3)
        proc.yc_create_art(products)
        self.assertEqual(self.backend_files_for_test().mapped('name'),
                         old_names,
                         'ART files are created only once when needed\n%s'
                         % self.backend.output_for_debug)
        # Now with multifile
        self.backend_files_for_test().unlink()
        self.backend.yc_parameter_create_art_multifile = True
        proc.yc_create_art(products)
        self.assertEqual(len(self.backend_files_for_test()), len(products),
                         self.backend.output_for_debug)

    def backend_files_for_test(self):
        return self.backend.file_ids.filtered(lambda x: x.state != 'cancel')
