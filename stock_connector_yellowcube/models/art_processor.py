# -*- coding: utf-8 -*-
##############################################################################
#
#    Copyright (c) 2016 brain-tec AG (http://www.braintec-group.com)
#    All Right Reserved
#
#    See LICENSE file for full licensing details.
##############################################################################
from .file_processor import FileProcessor


class ArtProcessor(FileProcessor):
    """
    This class creates the ART file for Yellowcube

    Version: 2.1
    """
    def __init__(self, backend):
        super(ArtProcessor, self).__init__(backend, 'art')

    def yc_create_art_file(self, products, add_suffix=False):
        """
        Creates the ART XML document

        @param products: list of products to be in this file
        @type products: RecordList of product.product
        """
        if self.yc_get_parameter('create_art_multifile') and len(products) > 1:
            for p in products:
                self.yc_create_art_file([p], add_suffix=True)
            return
        filerecord_obj = self.env['stock_connector.file.record']
        tools = self.tools
        root = tools.create_element('ART')
        root.append(self.yc_create_control_reference(tools, 'ART', '2.1'))
        article_list = tools.create_element('ArticleList')
        root.append(article_list)
        related_ids = []
        full_errors = []
        sent_products = []
        for product in products:
            product_errors = []
            change_flag = 'I'
            fr = filerecord_obj.search([
                ('res_model', '=', 'product.product'),
                ('res_id', '=', product.id),
                ('parent_id.state', '!=', 'cancel'),
                ('parent_id.type', '=', 'ART'),
                ('parent_id.backend_id', '=', self.backend_record.id)
            ], limit=1, order='create_date DESC')
            product_date = product.write_date
            if product.product_tmpl_id.write_date > product_date:
                product_date = product.product_tmpl_id.write_date
            if fr and fr.create_date > product_date:
                # The change was sent before
                continue
            elif fr:
                change_flag = 'U'
            article_list.append(tools.create_comment('product.product #{0}'
                                                     .format(product.id)))
            article = self.yc_create_art_article(tools, product,
                                                 product_errors, change_flag)
            errors = tools.validate_xml(article)
            if errors:
                product_errors.append(str(errors))
            if product_errors:
                full_errors.extend(product_errors)
                self.log_message(
                    'Error on product #{0}: {1}\n'.format(
                        product.id,
                        product.name
                    ), timestamp=True)
                for p in product_errors:
                    article_list.append(tools.create_comment(p))
            else:
                article_list.append(article)
                related_ids.append(('product.product', product.id))
                sent_products.append(product)

        if related_ids:
            errors = tools.validate_xml(root)
            if errors:
                self.log_message('ART file errors:\n{0}\n'.format(errors))

            else:
                suffix = products[0].id if add_suffix else None
                self.yc_save_file(root, related_ids, tools, 'ART',
                                  suffix=suffix, cancel_duplicates=True)
                self.log_message('ART file processed, '
                                 'with the next products: %s\n'
                                 % [x.default_code for x in sent_products])
        else:
            self.log_message('ART file skipped.\n')
            if full_errors:
                self.log_message('Full list of errors:\n%s\n'
                                 % '\n'.join(full_errors))

    def xml_tools_args(self):
        kwargs = {
            '_type': 'art',
        }
        return kwargs

    def yc_create_art_article(self, tools, product, product_errors, change):
        """
        Creates the Article element of the ART file

        @param tools: xml tools used for this file
        @type tools: XmlTools

        @param product: product related to this element
        @type product: BrowseRecord of product.product

        @param product_errors: list of errors of this product
        @type product_errors: [string*]

        @param change: ChangeFlag for the element
        @type change: string: 'I', 'U' or 'D'

        @return: Article element of the product
        @rtype: etree.Element
        """
        create = tools.create_element
        article = create('Article')
        article.append(create('ChangeFlag', change))
        article.append(create('DepositorNo',
                              self.yc_get_parameter('depositor_no')))
        article.append(create('PlantID', self.yc_get_parameter('plant_id')))
        article_no = product.default_code or ''
        if not article_no:
            if self.yc_get_parameter('on_art_set_missing_default_code'):
                article_no = product.default_code = str(product.id)
            else:
                product_errors.append('Missing default_code on Product {0}'
                                      .format(product.id))
        article.append(create('ArticleNo', article_no))
        iso_code = product.uom_id.iso_code
        if iso_code:
            article.append(create('BaseUOM', iso_code))
        else:
            product_errors.append('Missing ISO code for UOM: {0}'
                                  .format(product.uom_id.name))
        article.append(create('NetWeight', str(product.weight),
                              {'ISO': 'KGM'}))
        article.append(create('BatchMngtReq', '1' if product.tracking else 0))
        # Unimplemented element: MinRemLife
        # Unimplemented element: PeriodExpDateType
        article.append(create('SerialNoFlag', '0'))
        uom_node = create('UnitsOfMeasure')
        article.append(uom_node)
        uom_node.append(create('AlternateUnitISO', iso_code))
        desc_node = create('ArticleDescriptions')
        article.append(desc_node)
        lang_query = """
            SELECT value, lang
            FROM ir_translation
            WHERE lang in ('fr_CH', 'de_DE', 'it_CH')
                AND name = 'product.template,name'
                AND res_id = %s
        """
        self.env.cr.execute(lang_query, (product.product_tmpl_id.id, ))
        if len(product.name) > 40:
            _desc = tools._str(product.name)[40]
            desc_node.append(tools.create_comment(product.name))
        else:
            _desc = False
        desc_node.append(create('ArticleDescription', _desc or product.name,
                                {'ArticleDescriptionLC': 'en'}))
        for result in self.env.cr.fetchall():
            if len(result[0]) > 40:
                _desc = tools._str(result[0])[40]
                desc_node.append(tools.create_comment(result[0]))
            else:
                _desc = False
            desc_node.append(create('ArticleDescription', _desc or result[0],
                                    {'ArticleDescriptionLC': result[1][:2]}))

        return article
