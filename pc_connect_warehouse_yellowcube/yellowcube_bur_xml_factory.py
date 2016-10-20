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
logger = logging.getLogger(__name__)
from .xml_abstract_factory import xml_factory_decorator, xml_abstract_factory
from openerp.addons.pc_connect_master.utilities.misc import format_exception
from lxml import etree
from datetime import date
from xsd.xml_tools import nspath, validate_xml, open_xml, xml_to_string, repair_xml_file
from openerp.tools.translate import _
from openerp.release import version_info
V8 = True if version_info[0] > 7 else False


@xml_factory_decorator("bur")
class yellowcube_bur_xml_factory(xml_abstract_factory):

    success = False
    post_issue_tags = ['bur']
    post_issue_thread = True
    errors = []

    def _check(self, obj, cond, msg):
        if not cond:
            self.post_issue(obj, msg)
            self.success = False
            self.errors.append(msg)
        return bool(cond)

    def __init__(self, *args, **kargs):
        logger.debug("BUR factory created")
        self.ignore_import_errors = False

    def import_file(self, file_text, only_check=False):
        self.success = True
        self.errors = []
        xml = open_xml(file_text, _type='bur', print_error=self.print_errors)
        if nspath(xml, '//bur:BUR_List'):
            i = 0
            for x in nspath(xml, '//bur:BUR_List/bur:BUR'):
                i += 1
                # First, we try to check the records
                try:
                    text = xml_to_string(x)
                    self.import_file(text, only_check=True)
                except Warning as w:
                    print 'error>>>' * 5
                    print text
                    print '<<<error' * 5
                    raise Warning('Error on sub BUR file number {0}'.format(i), format_exception(w))
            for x in nspath(xml, '//bur:BUR_List/bur:BUR'):
                self.import_file(xml_to_string(x), only_check=False)
            return True

        validate_xml('bur', xml, print_error=False)
        imports = []
        product_obj = self.pool.get("product.product")
        lot_obj = self.pool.get('stock.production.lot')
        connection_obj = self.pool.get('stock.connect')
        mapping_bur_transactiontypes_obj = self.pool.get('mapping_bur_transactiontypes')
        location_obj = self.pool.get('stock.location')

        # Gets the warehouse of the YellowCube.
        warehouse = connection_obj.browse(self.cr, self.uid, self.connection_id, context=self.context).warehouse_ids[0]
        # Header fields (under <GoodsReceiptHeader>)
        header = nspath(xml, "//bur:GoodsMovementsHeader")[0]

        # <BookingVoucherID> and <BookingVoucherYear>.
        # TODO: Check or save the value
        booking_voucher_id = nspath(header, "bur:BookingVoucherID")[0].text
        # TODO: Check or save the value
        booking_voucher_year = nspath(header, "bur:BookingVoucherYear")[0].text
        depositor_no = nspath(header, "bur:DepositorNo")[0].text

        self._check(warehouse, depositor_no == self.get_param('depositor_no'), _('Invalid DepositorNo'))

        for article in nspath(xml, "//bur:BookingList/bur:BookingDetail"):
            partial_success = True
            element = {}

            # YCArticleNo
            element['yc_YCArticleNo'] = nspath(article, "bur:YCArticleNo")[0].text
            search_domain = [("yc_YCArticleNo", "=", element['yc_YCArticleNo'])]
            # ArticleNo
            article_no = nspath(article, "bur:ArticleNo")
            if len(article_no) > 0:
                # ArticleNo: Only set on dictionary, when needed for search (this avoids overwrite)
                element['default_code'] = article_no[0].text
                search_domain = [("default_code", "=", element['default_code'])]
            ids = product_obj.search(self.cr, self.uid, search_domain, context=self.context)
            if len(ids) > 0:
                element['id'] = ids[0]
            else:
                element['id'] = -1
            imports.append(element)
            if not self._check(warehouse, len(ids) == 1, _('Invalid search domain {0}').format(search_domain)):
                continue

            product = product_obj.browse(self.cr, self.uid, ids, context=self.context)[0]
            # EAN
            ean13 = nspath(article, 'bur:EAN')
            if ean13:
                element['ean13'] = ean13[0].text
                if product.ean13:
                    partial_success &= self._check(product,
                                                   product.ean13 == element['ean13'],
                                                   _('Product EAN13 {0} differs from XML EAN {1}').format(product.ean13, element['ean13']))
            # BVPosNo
            # TODO: Check or save the value
            bv_pos_no = nspath(article, 'bur:BVPosNo')[0].text

            # Plant
            plant = nspath(article, 'bur:Plant')[0].text
            partial_success &= self._check(product, plant == self.get_param('plant_id'), _('Mismatching PlantID'))

            # MovePlant
            # TODO: Check or save
            move_plant = nspath(article, 'bur:MovePlant')

            # StorageLocation
            source_location = nspath(article, 'bur:StorageLocation')[0].text

            # MoveStorageLocation
            destination_location = nspath(article, "bur:MoveStorageLocation")
            if destination_location:
                destination_location = destination_location[0].text
            else:
                destination_location = False

            # TransactionType
            transaction_type = nspath(article, "bur:TransactionType")[0].text  # Mandatory field, so won't fail.

            # We now determine the origin and destination locations based on the fields
            # StorageLocation, MoveStorageLocation, and TransactionType.
            # Have a look at task with ID=3725 for the algorithm which is copied below:
            # IF TransactionType is set on odoo
            # THEN use its location names
            # ELIF StorageLocation is recognized as a valid location in Odoo
            # AND MoveSorageLocation is recognized as a valid location in Odoo
            # THEN use those
            # ELSE trigger an issue
            is_mapped, mapped_origin_location, mapped_destination_location = \
                mapping_bur_transactiontypes_obj.get_mapping(self.cr, self.uid,
                                                             [],
                                                             transaction_type,
                                                             context=self.context)
            if is_mapped and mapped_origin_location and mapped_destination_location:
                element['location'] = mapped_origin_location.name
                element['destination'] = mapped_destination_location.name
            elif location_obj.search(self.cr, self.uid, [('name', '=', source_location)], context=self.context, count=True) and \
               destination_location and \
               location_obj.search(self.cr, self.uid, [('name', '=', destination_location)], context=self.context, count=True):
                element['location'] = source_location
                element['destination'] = destination_location
            else:
                # ELSE create an issue and stop processing the BUR. after resolving the TransactionType mapping, the import can be restarted...
                self.success = False  # We know now that we had no success.
                error_message = _('Error when importing BUR: StorageLocation and/or MoveStorageLocation were not defined or incorrect, AND '
                                  'no correct mapping was defined for TransactionType={0}').format(transaction_type)
                self.errors.append(error_message)
                self.post_issue(warehouse, error_message)

            # YCLot
            # TODO: check
            yc_lot = nspath(article, 'bur:YCLot')
            if yc_lot:
                element['yellowcube_lot'] = yc_lot[0].text

            # Lot
            lot = nspath(article, 'bur:Lot')
            if len(lot) > 0:
                element['lot'] = lot[0].text

                lot_id = lot_obj.search(self.cr,
                                         self.uid,
                                         [('product_id', '=', product.id), ('name', '=', element['lot'])],
                                         context=self.context)
                if not self._check(product, len(lot_id) <= 1, _('Impossible to find a unique lot {0}'.format(element['lot']))):
                    continue
                if not lot_id:
                    values = {
                        'product_id': product.id,
                        'name': element['lot']
                    }
                    production_date = nspath(article, "bur:ProductionDate")
                    if production_date:
                        values['date'] = self.str_date_to_postgres(production_date[0].text)
                    lot_use_date = nspath(article, "bur:BestBeforeDate")
                    if lot_use_date:
                        values['use_date'] = self.str_date_to_postgres(lot_use_date[0].text)
                    if only_check:
                        lot_id = None
                    else:
                        lot_id = [lot_obj.create(self.cr, self.uid, values, context=self.context)]
                if lot_id is None and only_check:
                    lot = None
                else:
                    lot = lot_obj.browse(self.cr, self.uid, lot_id, context=self.context)[0]

            # StockType
            element['stock_type'] = nspath(article, 'bur:StockType')[0].text

            # Quantity
            element['qty_available'] = nspath(article, "bur:QuantityUOM")[0].text

            # QuantityUOM
            qty_uom = nspath(article, "bur:QuantityUOM")[0].attrib['QuantityISO']
            qty_uom_ids = self.pool.get('product.uom').search(self.cr, self.uid, [('uom_iso', '=', qty_uom)], context=self.context)

            partial_success &= self._check(product, qty_uom_ids, _('There is not any Unit of Measure with ISO code being {0}.'.format(qty_uom)))
            if partial_success:
                element['qty_uom_id'] = qty_uom_ids[0]

            write_on_lot = {}
            # BestBeforDate
            lot_use_date = nspath(article, "bur:BestBeforeDate")
            element['lot_use_date'] = False
            if len(lot_use_date) > 0:
                lot_use_date = lot_use_date[0].text
                element['lot_use_date'] = self.str_date_to_postgres(lot_use_date)
                if lot is None:
                    self._check(product, only_check, _('The lot may not exists in a two step file'))
                else:
                    if not lot.use_date:
                        write_on_lot['use_date'] = element['lot_use_date']
                    else:
                        partial_success &= self._check(product,
                                                       self.keep_only_date(lot.use_date) == element['lot_use_date'],
                                                       _('Mismatch with lot best before date'))

            # ProductionDate
            production_date = nspath(article, "bur:ProductionDate")
            element['date'] = False
            if production_date:
                lot_date = lot_use_date[0].text
                element['lot_date'] = self.str_date_to_postgres(lot_date)
                if not lot.date:
                    write_on_lot['date'] = element['lot_date']
                else:
                    partial_success &= self._check(product,
                                                   self.keep_only_date(lot.date) == element['lot_date'],
                                                   _('Mismatch with lot fabrication date'))

            if write_on_lot and partial_success:
                lot.write(write_on_lot)

            element['name'] = "BUR-{0}-{1}".format(nspath(xml, "//bur:ControlReference/bur:Timestamp")[0].text, nspath(article, "bur:BVPosNo")[0].text)

        # print imports
        if not self.context.get('force_import', False):
            bad_imports = [x['yc_YCArticleNo'] for x in imports if x['id'] < 0]
            if len(bad_imports) > 0:
                raise Exception("Invalid XML Elements: {0}".format(bad_imports))

        if not self.success:
            raise Warning('There where errors on the import process. See import log thread.', self.errors)

        if only_check:
            # Everything was OK, and it could be imported in a second step.
            return True

        stock_move_pool = self.pool.get("stock.move")
        for article in imports:
            _id = article['id']
            self.mark_record(_id, 'product.product')
            _lot = False
            if 'lot' in article:
                _lot = self.pool.get('stock.production.lot').search(self.cr, self.uid,
                                                                    [('name', '=', article['lot']),
                                                                     ('product_id', '=', _id)],
                                                                    context=self.context)
                if len(_lot) > 0:
                    _lot = _lot[0]
                else:
                    _lot = self.pool.get('stock.production.lot').create(self.cr, self.uid,
                                                                        {'name': article['lot'],
                                                                         'product_id': _id,
                                                                         'date': element.get('lot_date', None),
                                                                         'use_date': element.get('lot_use_date', None)},
                                                                        context=self.context)

            def loc(is_input, element, warehouse):
                key = 'location' if is_input else 'destination'
                if (not input) and element['stock_type'] not in ['', '0', 'F']:
                    return warehouse.lot_blocked_id.id
                if element[key] == 'YROD':
                    return warehouse.lot_input_id.id
                if element[key] == 'YAFS':
                    return warehouse.lot_stock_id.id
                return self.pool['ir.model.data'].get_object_reference(self.cr, self.uid, 'stock', 'location_inventory')[1]

            stock_move_id = stock_move_pool.create(self.cr,
                                                   self.uid,
                                                   {'name': article['name'],
                                                    'product_id': _id,
                                                    'location_id': loc(True, article, warehouse),
                                                    'location_dest_id': loc(False, article, warehouse),
                                                    'product_uom_qty' if V8 else 'product_qty': article['qty_available'],
                                                    'product_uom': article['qty_uom_id'],
                                                    'state': 'done',
                                                    'restrict_lot_id' if V8 else 'prodlot_id': _lot,
                                                    'origin': 'YellowCube',
                                                    'type': 'internal',
                                                    'yc_booking_voucher_id': booking_voucher_id,
                                                    'yc_booking_voucher_year': booking_voucher_year,
                                                    },
                                                   context=self.context)
            self.mark_record(_id, 'product.product')

        return True

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
