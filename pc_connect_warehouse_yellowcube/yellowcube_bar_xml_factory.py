# b-*- encoding: utf-8 -*-
##############################################################################
#
#    Copyright (c) 2014 brain-tec AG (http://www.brain-tec.ch)
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
# from osv import osv, fields
# from tools.translate import _
import logging
import sys
logger = logging.getLogger(__name__)
from xml_abstract_factory import xml_factory_decorator, xml_abstract_factory
from openerp.addons.pc_connect_master.utilities.misc import format_exception
from lxml import etree
from openerp.tools.translate import _
import datetime
from xsd.xml_tools import nspath, validate_xml, open_xml
from openerp.release import version_info


@xml_factory_decorator("bar")
class yellowcube_bar_xml_factory(xml_abstract_factory):

    post_issue_tags = ['lot', 'bar-file']
    post_issue_thread = True
    success = True

    def __init__(self, *args, **kargs):
        logger.debug("BAR factory created")
        self.ignore_import_errors = False
        self.success = True
        self.errors_list = []  # Stores the errors found.

    def _check(self, obj, condition, message):
        if not condition:
            logger.debug("Unmet condition: {0}".format(message))
            self.success = False
            if obj:
                self.post_issue(obj, message)
            self.errors_list.append(message)
        return bool(condition)

    def import_file(self, file_text):
        self.success = True
        self.errors_list = []  # Stores the errors found.

        product_obj = self.pool.get("product.product")
        lot_obj = self.pool.get('stock.production.lot')
        lot_model = 'stock.quant' if version_info[0] > 7 else 'stock.report.prodlots'
        stock_report_prodlots_obj = self.pool[lot_model]

        xml = open_xml(file_text, _type='bar', print_error=self.print_errors)

        imports = []
        imported_lots = []

        stock_obj = self.pool.get("stock.change.product.qty")

        warehouse = self.pool.get('stock.connect').browse(self.cr, self.uid, self.connection_id, context=self.context).warehouse_ids[0]
        location = warehouse
        loc_stock = location.lot_stock_id.id
        loc_blocked = location.lot_blocked_id.id

        article_list = nspath(xml, "//bar:ArticleList/bar:Article")
        self._check(None, article_list, _('This BAR has no products in it.'))
        if not article_list:
            logger.debug("This is an empty BAR file")
            self.post_issue(location, _('This BAR has no products in it.'))

        for article in article_list:
            partial_success = True
            element = {'location_id': loc_stock}
            quantity_uom = float(nspath(article, "bar:QuantityUOM")[0].text)

            element['yc_YCArticleNo'] = nspath(article, "bar:YCArticleNo")[0].text
            article_no = nspath(article, "bar:ArticleNo")
            ean = nspath(article, "bar:EAN")

            # We attempt to identify the product.
            # Priority: YCArticleNo, ArticleNo(default_code), EAN(ean13).
            search_domain = []
            search_domain.append([("yc_YCArticleNo", "=", element['yc_YCArticleNo'])])

            if article_no:
                element['default_code'] = article_no[0].text
                search_domain.append([("default_code", "=", element['default_code'])])
            else:
                element['default_code'] = None

            if ean:
                element['ean13'] = ean[0].text
                search_domain.append([("ean13", "=", element['ean13'])])
            else:
                element['ean13'] = None

            # Attempts to identify the product.
            for domain in search_domain:
                product_id = product_obj.search(self.cr, self.uid, domain, context=self.context)
                if product_id:
                    break
            if quantity_uom == 0 and not product_id:
                self.post_issue(location, _('Product for domain {0} does not exists, and a zero stock update was received').format(search_domain))
                continue
            # If we don't have success identifying the product, we skip this line since it's impossible to continue.
            partial_success &= self._check(location, product_id, _('There is not article for domain {0}.').format(search_domain))
            if not partial_success:
                continue

            partial_success &= self._check(location, len(product_id) == 1, _('There is more than one article for domain {0}.').format(search_domain))
            if not partial_success:
                continue

            product_id = product_id[0]
            product = product_obj.browse(self.cr, self.uid, product_id, self.context)
            element['id'] = product_id
            for k in ('ean13', 'default_code', 'yc_YCArticleNo'):
                if product[k] and element[k]:
                    self._check(product, element[k] == product[k], _('Mismatching product reference {0}').format(k))

            # Checks/Saves Plant
            plant = nspath(article, "bar:Plant")[0].text
            current_plant = self.get_param('plant_id', required=True)
            self._check(product, current_plant, _("Configuration parameter YC PlantID is not defined for product {0}").format(product.name))
            self._check(product, current_plant and current_plant == plant, _('Plant does not match with the value of the configuration parameter YC PlantID for product {0}').format(product.name))

            # Checks <StorageLocation> and <StockType>
            # Notes: Check together with StorageLocation against location_id on stock.move - alarm if wrong.
            #        If free type (' ', '0', 'F', 'U') use the StorageLocation, otherwise location YBLK.
            storage_location = nspath(article, "bar:StorageLocation")[0].text
            stock_type = nspath(article, "bar:StockType")[0].text

            # If there exists the tag <StockType>, then we follow the rules.
            location_to_use_ids = False
            if stock_type in ('X', 'S', '2', '3', '0', 'F', 'U', ' '):
                if stock_type in ('0', 'F', 'U', ' '):
                    location_to_use = storage_location
                else:
                    location_to_use = 'YBLK'
                location_to_use_ids = self.pool.get('stock.location').search(self.cr, self.uid, [('name', '=', location_to_use)], context=self.context)
                self._check(product, len(location_to_use_ids) == 1, _("Location '{0}' was not found in the system, or was found multiple times.").format(location_to_use))
            else:
                self._check(product, False, _("StockType had value '{0}', which is not allowed for product {1}").format(stock_type, product.name))

            # Determines the lot: Lot has precedence over YCLot.
            lot_id = None
            lot_search_domain = None
            lot_to_use = False
            yc_lot = nspath(article, "bar:YCLot")
            if yc_lot:
                lot_to_use = yc_lot[0].text
                lot_search_domain = [('name', '=', lot_to_use), ('product_id', '=', product_id)]
            lot = nspath(article, "bar:Lot")
            if lot:
                lot_to_use = lot[0].text
                lot_search_domain = [('name', '=', lot_to_use), ('product_id', '=', product_id)]
            if lot_search_domain:
                lot_id = lot_obj.search(self.cr, self.uid, lot_search_domain, context=self.context)
                if len(lot_id) > 0:
                    lot_id = lot_id[0]
            # check(product, lot_search_domain is None or lot_id, _("Lot={0} does not exist.").format(lot_search_domain or '<no-lot-found>'))
            if (not lot_id) and lot_search_domain:
                lot_id = lot_obj.create(self.cr, self.uid, {'name': lot_search_domain[0][2], 'product_id': product_id}, context=self.context)
            self._check(product, (not product.track_production) or lot_id, _("Product {0} does not have a lot and it is required so.").format(product.name))

            # If we have a lot, we load it,
            # AND add it to the list of lots which need to update its last appearance in the BAR.
            if lot_id:
                lot = lot_obj.browse(self.cr, self.uid, lot_id, self.context)
                imported_lots.append(lot_id)

            # Dates: BestBeforeDate.
            best_before_date = nspath(article, "bar:BestBeforeDate")
            if best_before_date:
                best_before_date = best_before_date[0].text
                if self._check(product, lot_search_domain, _('BestBeforeDate defined but unknown lot to use in product {0}').format(product.name)):
                    self._check(product,
                                (not lot.use_date) or (self.keep_only_date(lot.use_date) == self.str_date_to_postgres(best_before_date)),
                                _("Use date ({1}) of the lot {0} and tag BestBeforeDate ({2}) do not match for product {3}.").format(lot.name,
                                                                                                                                     self.keep_only_date(lot.use_date),
                                                                                                                                     self.str_date_to_postgres(best_before_date),
                                                                                                                                     product.name))
                if lot_id and not lot.use_date:
                    lot_obj.write(self.cr, self.uid, lot_id, {'use_date': self.str_date_to_postgres(best_before_date)}, self.context)

            # Dates: ProductionDate.
            production_date = nspath(article, "bar:ProductionDate")
            if production_date:
                production_date = production_date[0].text
                self._check(product,
                            (not lot_id) or (not lot.production_date) or (self.keep_only_date(lot.production_date) == self.str_date_to_postgres(production_date)),
                            _("Use date ({1}) of the lot {0} and tag ProductionDate ({2}) do not match for product {3}.").format(lot.name,
                                                                                                                                 self.keep_only_date(lot.production_date),
                                                                                                                                 self.str_date_to_postgres(production_date),
                                                                                                                                 product.name))
                if lot_id and not lot.date:
                    lot_obj.write(self.cr, self.uid, lot_id, {'date': self.str_date_to_postgres(production_date)}, self.context)

            # Checks the QuantityUOM and QuantityISO.
            if stock_type in ('0', 'F', ' '):  # If is free location.
                if location_to_use_ids:
                    element['location_id'] = location_to_use_ids[0]
                if lot_id and location_to_use_ids:  # We have a lot and a location: check against the quantity of the lot+location.
                    stock_report_prodlot_id = stock_report_prodlots_obj.search(self.cr, self.uid, [('location_id', '=', location_to_use_ids[0]),
                                                                                                   ('lot_id' if version_info[0] > 7 else 'prodlot_id', '=', lot_id),
                                                                                                   ('product_id', '=', product_id)
                                                                                                   ], context=self.context)
                    partial_success &= self._check(product, stock_report_prodlot_id,
                                                   _("No combination of location={0} and lot={1} was found in the system for product {2}.").format(location_to_use, lot_to_use, product.name))
                    if partial_success and stock_report_prodlot_id:
                        # Checks that the quantity is correct.
                        stock_report_prodlot = stock_report_prodlots_obj.browse(self.cr, self.uid, stock_report_prodlot_id[0], self.context)
                        if stock_report_prodlot.qty != quantity_uom:
                            self.post_issue(product,
                                            _("QuantityUOM does not match for the combination of location={0} and lot={1}. Scraping will be make.").format(location_to_use, lot_to_use),
                                            create=True,
                                            reopen=True)

                else:  # We don't have a lot: check against the quantity of the product.
                    if product.qty_available != quantity_uom:
                        self.post_issue(product,
                                        _("QuantityUOM does not match the quantity indicated by the field 'product_qty' of the original product. Scraping will be make."),
                                        create=True,
                                        reopen=True)
            else:
                # No free stock type
                element['location_id'] = loc_blocked
            element['qty_available'] = quantity_uom

            # Checks that the QuantityUOM matches with the product.
            quantity_iso = nspath(article, "bar:QuantityUOM")[0].attrib['QuantityISO']
            uom_iso_list = self.pool.get('product.uom').search(self.cr, self.uid, [('uom_iso', '=', quantity_iso)], context=self.context)
            if uom_iso_list:
                element['yc_bar_uom_id'] = uom_iso_list[0]  # Stores the last UOM sent with the BAR.
                uom = self.pool.get('product.uom').browse(self.cr, self.uid, uom_iso_list[0], self.context)
                uom_category = self.pool.get('product.uom.categ').browse(self.cr, self.uid, uom.category_id.id, context=self.context)

                # Checks that the UOM indicated is either the same, or of the same category,
                # than that of the product.
                same_uom_than_product = (uom.id == product.uom_id.id) if product.uom_id else False
                same_category_than_products_uom = (product.uom_id.category_id.id == uom_category.id) if product.uom_id else False
                self._check(product,
                            same_uom_than_product or (not same_uom_than_product and same_category_than_products_uom),
                            _("The UOM of the product {0} is not the same, and they are from different categories.").format(product.name))

#                 self._check(product,
#                             not(product.uom_id and (uom_name != product.uom_id.name)),
#                             _("Unit of measure '{0}' does not match with that of the product ('{1}')").format(uom_name, product.uom_id.name))

                self._check(product, product.uom_id, _("Product {0} does not have a unit of measure.").format(product.name))
            else:
                self._check(product, False, _("Unit of measure '{0}' was not found in the system.").format(quantity_iso))

            if lot_id:
                element['lot'] = lot_id
            # We accept blocked location
            if True or stock_type in ('0', 'F', ' '):  # If it's free location...
                imports.append(element)

        if self.success:
            # print imports

            if not self.context.get('force_import', False):
                bad_imports = [x['yc_YCArticleNo'] for x in imports if x['id'] < 0]
                if len(bad_imports) > 0:
                    raise Warning("Elements not defined in openERP: {0}".format(bad_imports))
            else:
                logger.error("This code is not part of YellowCube's and its use is only intended for developers: START OF THE CODE.")
                new_imports = [x for x in imports if x['id'] < 0 and x['qty_available'] != 0]
                for article in new_imports:
                    imports.remove(article)
                    del article['id']
                    article['type'] = 'product'
                    _id = product_obj.create(self.cr, self.uid, article, context=self.context)
                    location_id = article['location_id']
                    del article['location_id']
                    values = {'product_id': _id, 'location_id': location_id, 'new_quantity': article['qty_available']}
                    if 'lot' in article:
                        values['lot_id' if version_info[0] > 7 else 'prodlot_id'] = article['lot']
                    _update = stock_obj.create(self.cr, self.uid, values, context=self.context)
                    self.context['active_id'] = _id
                    stock_obj.browse(self.cr, self.uid, _update, context=self.context).change_product_qty()
                    self.mark_record(_id, 'product.product')
                    for same in [x for x in new_imports if x['yc_YCArticleNo'] == article['yc_YCArticleNo']]:
                        same['id'] = _id
                logger.error("This code is not part of YellowCube's and its use is only intended for developers: FINISH OF THE CODE.")

            # We return by context, the lots that were updated.
            self.context['imported_lots'] = imported_lots

            # We return by context, the products that where updated
            self.context['imported_products'] = imported_products = []
            for article in imports:
                # For each article it creates a wizard and updates its stock (if the actual stock is
                # lower than that expect, the quantity is moved to the loss-things warehouse;
                # otherwise the quantity is updated).
                _id = article['id']
                imported_products.append(_id)
                if _id <= 0:
                    continue
                del article['id']
                if 'name' in article:
                    del article['name']  # OpenERP is the master, so the name <ArticleDescription> is not overwritten.
                del article['default_code']  # OpenERP is the master, so the default code <ArticleNo> is not overwritten.
                location_id = article['location_id']
                del article['location_id']
                values = {'product_id': _id, 'location_id': location_id, 'new_quantity': article['qty_available']}
                if 'lot' in article:
                    self.mark_record(article['lot'], 'stock.production.lot')
                    values['lot_id' if version_info[0] > 7 else 'prodlot_id'] = article['lot']
                    del article['lot']
                product_obj.write(self.cr, self.uid, _id, article, context=self.context)
                logger.debug("Updating stock {0}".format(values))
                _update = stock_obj.create(self.cr, self.uid, values, context=self.context)
                self.context['active_id'] = _id
                stock_obj.browse(self.cr, self.uid, _update, context=self.context).change_product_qty()
                self.mark_record(_id, 'product.product')

            if 'active_ids' in self.context:
                del self.context['active_ids']

        if not self.success:
            raise Warning(_('Some errors where found when processing BAR file:\n -{0}').format('\n -'.join(self.errors_list)))

        return self.success

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
