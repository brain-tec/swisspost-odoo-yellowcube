# -*- coding: utf-8 -*-
##############################################################################
#
#    Copyright (c) 2016 brain-tec AG (http://www.braintec-group.com)
#    All Right Reserved
#
#    See LICENSE file for full licensing details.
##############################################################################
from . import test_base
from openerp.addons.stock_connector_yellowcube.models \
    import xml_tools
import logging
_logger = logging.getLogger(__name__)


class TestBarFile(test_base.TestBase):

    def runTest(self):
        return super(TestBarFile, self).runTest()

    def setUp(self):
        super(TestBarFile, self).setUp()
        get_binding = self.backend.get_binding
        get_binding(self.browse_ref('stock.stock_location_stock'),
                    'StorageLocation',
                    'YAFS')

    def test_import_bar_file(self):
        _logger.info('Creating BAR file')

        products = [
            # (product, create_binding, lot)
            {
                'product': self.browse_ref('product.product_product_7'),
                'create_binding': True,
                'lot': 'lot123',
                'qty': 10,
            },
            {
                'product': self.browse_ref('product.product_product_9'),
                'qty': 10,
            },
        ]

        bar_content = self.create_bar_file(products)

        # Now, we save the file, and process it
        bar_file = self.env['stock_connector.file'].create({
            'name': 'file.xml',
            'backend_id': self.backend.id,
            'content': bar_content
        })
        # Here, we check the file is imported
        proc = self.backend.get_processor()
        proc.processors['BAR'](proc, bar_file)
        self.assertEquals(bar_file.state, 'done',
                          self.backend.output_for_debug)
        self.assertItemsEqual(
            map(lambda x: x['product'].id, products),
            bar_file.child_ids.filtered(
                lambda x: x.res_model == 'product.product'
            ).mapped('res_id')
            # 'All products have been used'
        )

    def create_bar_file(self, products):
        proc = self.backend.get_processor()
        tools = xml_tools.XmlTools(_type='bar')
        create = tools.create_element
        get_binding = self.backend.get_binding
        bar_root = create('BAR')
        bar_root.append(proc.yc_create_control_reference(tools,
                                                         'BAR',
                                                         '1.0'))
        tools.nspath(bar_root, '//bar:Sender')[0].text = 'YELLOWCUBE'
        tools.nspath(bar_root, '//bar:Receiver')[0].text = 'YCTest'
        article_list = create('ArticleList')
        bar_root.append(article_list)
        for line in products:
            product = line['product']
            bind_yc_article_no = line.get('create_binding', False)
            lot = line.get('lot', False)

            article = create('Article')
            article_list.append(article)
            if bind_yc_article_no:
                yc_article_no = get_binding(product,
                                            'YCArticleNo',
                                            product.default_code)
            else:
                yc_article_no = product.default_code
            article.append(create('YCArticleNo',
                                  yc_article_no))
            if not bind_yc_article_no:
                article.append(create('ArticleNo', product.default_code))
            article.append(create('ArticleDescription', product.name))
            article.append(create('Plant'))
            article.append(create('StorageLocation', 'YAFS'))
            if lot:
                article.append(create('YCLot', lot))
                article.append(create('Lot', lot))
            article.append(create('StockType'))
            article.append(create('QuantityUOM', line['qty'],
                                  {'QuantityISO': 'PCE'}))

        # We check that the XSD is OK
        self.assertEquals(tools.validate_xml(bar_root), None)
        bar_content = tools.xml_to_string(bar_root)
        return bar_content
