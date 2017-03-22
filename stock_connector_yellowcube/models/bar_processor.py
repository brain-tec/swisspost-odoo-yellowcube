# -*- coding: utf-8 -*-
##############################################################################
#
#    Copyright (c) 2016 brain-tec AG (http://www.braintec-group.com)
#    All Right Reserved
#
#    See LICENSE file for full licensing details.
##############################################################################
from openerp.tools.translate import _
from .file_processor import FileProcessor


class BarProcessor(FileProcessor):
    """
    This class reads a bar file from Yellowcube

    Version: 1.0
    """

    def __init__(self, backend):
        super(BarProcessor, self).__init__(backend, 'bar')

    def yc_read_bar_file(self, bar_file):
        """
        :param openerp.osv.orm.browse_record bar_file:
        """
        bar_file.info = ''
        self.log_message(
            'Reading BAR file {0}\n'.format(bar_file.name),
            file_record=bar_file,
            timestamp=True)
        if not self.validate_file(bar_file):
            return

        errors = []
        related_ids = []
        products_to_do = []
        bindings_to_do = {}
        try:
            for bar_article in self.path(self.tools.open_xml(bar_file.content,
                                                             _type='bar'),
                                         '//bar:Article'):
                product_to_do = self.yc_read_bar_line(bar_article,
                                                      bindings_to_do, errors)

                if product_to_do:
                    products_to_do.append(product_to_do)
                    related_key = ('product.product',
                                   product_to_do['product_id'])
                    if related_key not in related_ids:
                        related_ids.append(related_key)

        except Exception as e:
            errors.append(self.tools.format_exception(e))

        if len(products_to_do) == 0:
            errors.append(_('There are no articles in this file'))

        if errors:
            bar_file.state = 'error'
            self.log_message(
                'BAR file errors:\n{0}\n'.format('\n'.join(errors)),
                file_record=bar_file)
        else:
            for key in bindings_to_do:
                self.get_binding(bindings_to_do[key], 'YCArticleNo', key)
            for product_to_do in products_to_do:
                self.yc_process_bar_line(product_to_do)
            bar_file.state = 'done'
            bar_file.write({'child_ids': [
                (0, 0, {'res_model': x, 'res_id': y}) for x, y in related_ids
            ]})
            self.log_message('BAR file processed\n', file_record=bar_file)

    def yc_read_bar_line(self, bar_article, bindings_to_do, errors):
        """
        :param lxml.etree._ElementTree._ElementTree bar_article:
        :param dict bindings_to_do:
        :param list errors:
        :return: Dict
        """
        product_to_do = {}

        yc_article_no = self.path(bar_article, 'bar:YCArticleNo')[0].text
        product_binding = self.find_binding(yc_article_no, 'YCArticleNo')
        # Check the product is registered on the system
        if product_binding:
            product = product_binding.record
        else:
            article_no = self.path(bar_article, 'bar:ArticleNo')
            if not article_no:
                errors.append(_('Impossible to find product binding '
                                '{0}').format(yc_article_no))
                return None
            product = self.env['product.product'].search(
                [('default_code', '=', article_no[0].text)],
                limit=1
            )
            if not product:
                errors.append(_('Impossible to find product code '
                                '{0}').format(yc_article_no))
                return None
            if bindings_to_do.get(yc_article_no, product) != product:
                errors.append(_('Binding {0} is duplicated')
                              .format(yc_article_no))
                return None
            bindings_to_do[yc_article_no] = product
        product_to_do['product_id'] = product.id
        # Find the location to use
        location = self.path(bar_article, 'bar:StorageLocation')[0].text
        yc_stocktype = self.path(bar_article, 'bar:StockType')[0].text
        if (yc_stocktype or '0') not in ('0', 'F', ' '):
            location = 'YBLK'
        if location:
            location_binding = self.find_binding(location, 'StorageLocation')
            if not location_binding:
                errors.append(_('Unknown location {0}')
                              .format(location))
                return None
            product_to_do['location_id'] = location_binding.res_id
        quantity = self.path(bar_article, 'bar:QuantityUOM')[0]
        product_to_do['new_quantity'] = float(quantity.text or 0)
        if product.uom_id.iso_code != quantity.get('QuantityISO'):
            errors.append(_('Distinct UOM for {0}')
                          .format(yc_article_no))
            return None
        lot = self.path(bar_article, 'bar:Lot')
        yc_lot = self.path(bar_article, 'bar:YCLot')
        if yc_lot:
            yc_lot = yc_lot[0].text
        if lot:
            lot = lot[0].text
        else:
            lot = yc_lot
        if lot:
            product_to_do['lot_id'] = lot
        return product_to_do

    def yc_process_bar_line(self, product_to_do):
        """
        :param dict product_to_do: Product to process
        """
        if 'lot_id' in product_to_do:
            lot = self.env['stock.production.lot'].search([
                ('name', '=', product_to_do['lot_id']),
                ('product_id', '=', product_to_do['product_id'])
            ], limit=1)
            if not lot:
                lot = self.env['stock.production.lot'].create({
                    'name': product_to_do['lot_id'],
                    'product_id': product_to_do['product_id'],
                })
            product_to_do['lot_id'] = lot.id
        self.env["stock.change.product.qty"] \
            .create(product_to_do).change_product_qty()
