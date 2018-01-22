# b-*- encoding: utf-8 -*-
##############################################################################
#
#    Copyright (c) 2014 brain-tec AG (http://www.braintec-group.com)
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

from openerp.osv import osv, fields
from xml_abstract_factory import xml_factory_decorator, xml_abstract_factory
from openerp.addons.pc_connect_master.utilities.others import format_exception
from openerp.tools.translate import _
from openerp.release import version_info
V8 = True if version_info[0] > 7 else False
import logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


@xml_factory_decorator("wba")
class yellowcube_wba_xml_factory(xml_abstract_factory):

    post_issue_tags = ['lot', 'wba-file']
    post_issue_thread = True
    success = False
    errors = []

    def _check(self, obj, cond, msg):
        if not cond:
            self.post_issue(obj, msg)
            self.errors.append(msg)
            self.success = False
        return bool(cond)

    def __init__(self, *args, **kargs):
        logger.debug("WBA factory created")
        self.ignore_import_errors = False

    def import_file(self, file_text):
        logger.debug("Processing WBA file")
        self.success = True
        self.errors = []

        # Caches the pools.
        product_obj = self.pool.get('product.product')
        stock_obj = self.pool.get('stock.picking')
        picking_in_obj = self.pool.get('stock.picking.in')
        stock_move_obj = self.pool.get('stock.move')
        warehouse_obj = self.pool.get('stock.warehouse')
        connection_obj = self.pool.get('stock.connect')
        stock_production_lot_obj = self.pool.get('stock.production.lot')
        connect_file_obj = self.pool.get('stock.connect.file')

        warehouse_id = connection_obj.browse(self.cr, self.uid, self.connection_id, context=self.context).warehouse_ids[0].id
        warehouse = warehouse_obj.browse(self.cr, self.uid, warehouse_id, context=self.context)

        # We keep track of the connect file that we are processing so that
        # we can update the value of related_ids, that we'll need afterwards
        # (e.g. to generate the summary WBA).
        stock_connect_file_id = self.context.get('stock_connect_file_id')
        connect_file = connect_file_obj.browse(
            self.cr, self.uid, stock_connect_file_id, context=self.context)

        xml = self.xml_tools.open_xml(
            file_text, _type='wba', print_error=self.print_errors)
        if self.xml_tools.nspath(xml, '//wba:WBA_List'):
            i = 0
            self.cr.execute("SAVEPOINT yellowcube_wba_xml_factory__WBAList;")
            for x in self.xml_tools.nspath(xml, '//wba:WBA_List/wba:WBA'):
                i += 1
                # First, we try to check the records
                try:
                    text = self.xml_tools.xml_to_string(x)
                    self.import_file(text)
                except Warning as w:
                    self.cr.execute("ROLLBACK TO SAVEPOINT yellowcube_wba_xml_factory__WBAList;")
                    print 'error>>>' * 5
                    print text
                    print '<<<error' * 5
                    raise Warning('Error on sub WBA file number {0}'.format(i), format_exception(w))
            self.cr.execute("RELEASE SAVEPOINT yellowcube_wba_xml_factory__WBAList;")
            return True

        errors = self.xml_tools.validate_xml('wba', xml, print_error=False)
        if errors:
            raise Warning(errors)

        # Gets the timestamp.
        timestamp_postgres = self.str_date_to_postgres(
            self.xml_tools.nspath(xml, "//wba:Timestamp")[0].text)

        # Header fields (under <GoodsReceiptHeader>)
        header = self.xml_tools.nspath(xml, "//wba:GoodsReceiptHeader")[0]

        # <BookingVoucherID> and <BookingVoucherYear>.
        booking_voucher_id = self.xml_tools.nspath(
            header, "wba:BookingVoucherID")[0].text
        booking_voucher_year = self.xml_tools.nspath(
            header, "wba:BookingVoucherYear")[0].text
        # This is the stock.picking's ID.
        supplier_order_no = self.xml_tools.nspath(
            header, "wba:SupplierOrderNo")[0].text

        picking_in_ids = stock_obj.search(self.cr, self.uid, [('yellowcube_customer_order_no', '=', supplier_order_no),
                                                              ('state', 'not in', ['cancel', 'done']),
                                                              ], context=self.context)

        # Checks if the stock.picking exists. Otherwise, logs an issue an continues with the next one.
        self._check(warehouse, len(picking_in_ids) > 0, _("There is not any stock.picking with SupplierOrderNo (id) ={0}").format(supplier_order_no))
        if not self.success:
            raise Warning('There were some errors in the WBA file.', self.errors)

        # Gets the stock picking in associated to this purchase order.
        picking_in = stock_obj.browse(self.cr, self.uid, picking_in_ids[0], self.context)

        # Saves the picking to the stock.connect file in the related_ids.
        connect_file.add_related_id('stock.picking.in', picking_in.id)

        # <SupplierNo>.
        # We first check if the supplier has a supplier number, and if that's the case we
        # compare against it. Otherwise, we compare against the default supplier number
        # set for the connector.
        supplier_no = self.xml_tools.nspath(header, "wba:SupplierNo")[0].text
        if picking_in.partner_id.supplier and picking_in.partner_id.yc_supplier_no:
            yc_supplier_no = picking_in.partner_id.yc_supplier_no
            self._check(warehouse, yc_supplier_no == supplier_no, _("Configuration variable YC SupplierNo does not match with that of tag 'SupplierNo' on the supplier."))
        else:
            yc_supplier_no = self.get_param('supplier_no', required=True)
            self._check(warehouse, yc_supplier_no, _("Configuration variable YC SupplierNo is not defined in the system."))
            self._check(warehouse, yc_supplier_no == supplier_no, _("Configuration variable YC SupplierNo does not match with that of tag 'SupplierNo' on the connector."))

        # <SupplierOrderNo>.
        stock_picking_in_count = stock_obj.search(self.cr, self.uid, [('yellowcube_customer_order_no', '=', supplier_order_no)], context=self.context, count=True)
        self._check(warehouse, stock_picking_in_count > 0, _("Stock picking in with ID={0} does not exist in the system, thus can not be processed in the WBA.").format(supplier_order_no))

        id_table = {}
        last_posno = 0

        # Update missing values
        for line in picking_in.move_lines:
            if line.yc_posno:
                if line.yc_posno > last_posno:
                    last_posno = line.yc_posno
            id_table[line.id] = line
        for line_id in sorted([x for x in id_table]):
            line = id_table[line_id]
            if not line.yc_posno:
                last_posno += 1
                line.yc_posno = last_posno
                line.write({'yc_posno': last_posno})

        # Refresh the record
        picking_in = stock_obj.browse(self.cr, self.uid, picking_in_ids[0], self.context)

        for article in self.xml_tools.nspath(
                xml, "//wba:GoodsReceiptList/wba:GoodsReceiptDetail"):
            partials = {}
            partial = {}

            # <SupplierOrderPosNo>
            pos_no = int(self.xml_tools.nspath(
                article, "wba:SupplierOrderPosNo")[0].text)

            # Gets the stock.move associated to this line.
            # In the case that more than one stock.move shares the same
            # value for the yc_posno, because of the order of the stock.move
            # it'll show first the oldest stock.move, which is good for our
            # case since we may add newer stock.moves if the original ones are
            # splitted.
            move_line = None
            for line in picking_in.move_lines:
                if line.yc_posno == pos_no:
                    move_line = line
                    break

            self._check(picking_in, move_line is not None, _('Mismatch with stock picking line number {0}/{1}').format(pos_no, [x.yc_posno for x in picking_in.move_lines]))
            if not self.success:
                raise Warning('Error parsing wba file', self.errors)

            if move_line.yc_qty_done == 0.0 and move_line.yc_eod_received:
                error_msg = \
                    'The WBA file for picking {0} (ID={1}) regarding ' \
                    'BookingVoucherID={2} was not processed because of the ' \
                    'following lines having yc_qty_done == 0 and ' \
                    'yc_eod_received == True:\n' \
                    'Move ID={3}, Product {4} (ID={5}), ' \
                    'Position {6}, Qty={7}'.format(
                        picking_in.name, picking_in.id, booking_voucher_id,
                        move_line.id, move_line.product_id.name,
                        move_line.product_id.id, move_line.yc_posno or '?',
                        move_line.product_qty)
                raise Warning(error_msg)

            partials[move_line if V8 else "move{0}".format(move_line.id)] = partial

            partial['delivery_date'] = timestamp_postgres

            # Caches the product of the stock.move.
            product_id = move_line.product_id.id
            partial['product_id'] = product_id
            product = product_obj.browse(self.cr, self.uid, product_id, self.context)

            # <YCArticleNo>
            yc_article_no = self.xml_tools.nspath(
                article, "wba:YCArticleNo")[0].text
            if not product.yc_YCArticleNo:
                product_obj.write(self.cr, self.uid, product_id, {'yc_YCArticleNo': yc_article_no}, self.context)
                product.message_post(_('Product {0} with ID={1} did not have a YCArticleNo, so it was created with value {2}').format(product.name, product_id, yc_article_no))
            else:
                # If the product already had a YCArticleNo, then we check if the values match.
                self._check(warehouse, product.yc_YCArticleNo == yc_article_no, _("The 'YCArticleNo' does not match with the field 'YCArticleNo' of the product."))

            # <ArticleNo>
            article_no = self.xml_tools.nspath(article, "wba:ArticleNo")
            if article_no:
                article_no = article_no[0].text
                if not product.default_code:
                    product_obj.write(self.cr, self.uid, product_id, {'default_code': article_no}, self.context)
                    product.message_post(_('Product {0} with ID={1} did not have a default_code, so it was created with value {2}').format(product.name, product_id, article_no))
                else:
                    # If the product already has an ArticleNo (field 'default_code' in Odoo), then we check if the values match.
                    self._check(warehouse, product.default_code == article_no,
                                '{0} [{1}!={2}]'.format(_("The 'ArticleNo' does not match with the field 'default_code' of the product."), product.default_code, article_no))

            # <EAN>
            ean = self.xml_tools.nspath(article, "wba:EAN")
            if ean and not self.get_param('ignore_ean'):
                # If we choose not to ignore the EAN, we process it;
                # otherwise we do nothing with the EAN received.
                ean = ean[0].text
                if product.ean13:
                    # If the product already has an EAN (field 'ean13'
                    # in Odoo) then we check if both values match.
                    self._check(warehouse, product.ean13 == ean,
                                _('Product {0} (id={1}): EAN does not '
                                  'match with ean13.').format(product.name,
                                                              product.id))
                else:
                    product_obj.write(self.cr, self.uid, product_id,
                                      {'ean13': ean}, self.context)
                    product.message_post(
                        _('Product {0} with ID={1} did not have an '
                          'ean13 code, so it was created with '
                          'value {2}').format(product.name, product_id, ean))

            # <Lot>
            lot_search_domain = [('product_id', '=', product_id)]
            lot_xml = self.xml_tools.nspath(article, 'wba:Lot')
            lot_name = False
            if lot_xml:
                lot_name = lot_xml[0].text
                lot_search_domain.append(('name', '=', lot_name))

            # <YCLot>
            yc_lot = self.xml_tools.nspath(article, 'wba:YCLot')
            if yc_lot:
                yc_lot = yc_lot[0].text
#                 lot_search_domain.append(('yellowcube_lot', '=', yc_lot))

            # If a lot was indicated but it does not exist in the system, create it.
            lot_ids = stock_production_lot_obj.search(
                self.cr, self.uid, lot_search_domain, limit=1,
                context=self.context)
            if lot_name and not lot_ids:
                lot_id = stock_production_lot_obj.create(self.cr, self.uid, {
                    'name': lot_name,
                    'yellowcube_lot': yc_lot or False,
                    'product_id': product_id,
                    'date': timestamp_postgres,
                }, self.context)
                lot_ids = [lot_id]
                lot = stock_production_lot_obj.browse(
                    self.cr, self.uid, lot_id, context=self.context)
                lot.message_post(_('Stock.production.lot {0} with ID={1} did not existed, and it was created by VoucherID {2}').format(lot_name, lot_id, booking_voucher_id))

            lot = None
            if lot_ids:
                lot = stock_production_lot_obj.browse(self.cr, self.uid, lot_ids[0], self.context)
            # If <YCLot> exists but the stock production lot does not have it, stores it. If it has it, checks.
            if yc_lot and lot:
                if not lot.yellowcube_lot:
                    stock_production_lot_obj.write(self.cr, self.uid, lot.id, {'yellowcube_lot': yc_lot}, self.context)
                    lot.message_post(_('Stock.production.lot {0} with ID={1} did not have a yellowcube_lot, so it was set with value {2}').format(lot.name, lot.id, yc_lot))
                else:
                    self._check(warehouse, lot.yellowcube_lot == yc_lot, _("YCLot in the WBA does not match with the value of the stock.production.lot"))

            if lot_ids:
                partial['restrict_lot_id' if V8 else 'prodlot_id'] = lot_ids[0]

                # If the product is not set as lotted, sets it.
                if not product.track_production or \
                   not product.track_incoming or \
                   not product.track_outgoing or \
                   not product.yc_track_outgoing_scan:
                    product_obj.write(self.cr, self.uid, product_id,
                                      {'track_production': True,
                                       'track_incoming': True,
                                       'track_outgoing': True,
                                       }, context=self.context)

            if product.track_incoming:
                self._check(warehouse, lot is not None, _("The WBA file must contain a lot, otherwise the stock.move can not be updated for product {0}".format(product.name)))

            # <Plant>
            plant = self.xml_tools.nspath(article, 'wba:Plant')[0].text
            current_plant = self.get_param('plant_id', required=True)
            if current_plant:
                self._check(warehouse, current_plant == plant, _('Plant does not match with the value of the configuration parameter YC PlantID.'))
            elif not current_plant:
                self.set_param('plant_id', plant)

            #  <QuantityUOM>
            quantity_uom = float(self.xml_tools.nspath(
                article, "wba:QuantityUOM")[0].text)

            # We allow to receive more quantity than we asked for.
            #self._check(picking_in, move_line.product_qty >= quantity_uom, _('Product {0}: QuantityUOM is greater than that of the stock.move.').format(product.name))

            partial['product_qty'] = quantity_uom

            # <QuantityISO>
            quantity_iso = self.xml_tools.nspath(
                article, "wba:QuantityUOM")[0].attrib['QuantityISO']
            uom_iso_list = self.pool.get('product.uom').search(self.cr, self.uid, [('uom_iso', '=', quantity_iso)], context=self.context)
            if len(uom_iso_list) > 0 and move_line.product_uom and (quantity_iso != move_line.product_uom.uom_iso):
                self._check(picking_in, False, _('Product {0}: Attribute QuantityISO does not match the ISO code indicated of the original stock.move.').format(product.name))
            else:
                if not move_line.product_uom:
                    product_uom = uom_iso_list[0]
                    partial['product_uom'] = product_uom
                else:
                    self._check(warehouse, move_line.product_uom.uom_iso == quantity_iso, _('Product {0}: Attribute QuantityISO does not match that of the stock.move.').format(product.name))
                    partial['product_uom'] = move_line.product_uom.id

            # Checks <StorageLocation> and <StockType>
            # Notes: Check together with StorageLocation against location_id on stock.move - alarm if wrong.
            #        If free type (' ', '0', 'F') use the StorageLocation, otherwise location YBLK.
            storage_location = self.xml_tools.nspath(
                article, "wba:StorageLocation")[0].text
            stock_type = self.xml_tools.nspath(article, "wba:StockType")
            if move_line.location_id:
                if stock_type:
                    # If there exists the tag <StockType>, then we follow the rules.
                    stock_type = stock_type[0].text

                    if stock_type not in ('X', 'S', '2', '3', '0', 'F', ' '):
                        self._check(picking_in, False, _("Product {0}: StockType had value '{1}', which is not allowed.").format(product.name, stock_type), self.context)
                    elif stock_type in ('0', 'F', ' '):
                        if move_line.location_dest_id.name != storage_location:
                            self._check(picking_in,
                                        False,
                                        _('Product {0}: StorageLocation {1} does not match with the location indicated in the stock.move {2}.').format(product.name,
                                                                                                                                                       storage_location,
                                                                                                                                                       move_line.location_dest_id.name))
                    else:
                        if move_line.location_dest_id.name != 'YBLK':
                            self._check(picking_in, False, _("Product {0}: StorageLocation must be 'YBLK' since StockType is not a free type.").format(product.name))
                else:
                    # If <StockType> does not exist, it just checks that the values match.
                    if move_line.location_dest_id.name != storage_location:
                        self._check(picking_in,
                                    False,
                                    _('Product {0}: StorageLocation {1} does not match with the location indicated in the stock.move {2}.').format(product.name,
                                                                                                                                                   storage_location,
                                                                                                                                                   move_line.location_dest_id.name))
            else:
                self._check(picking_in, False, _('Product {0}: The stock move does not have a location_id.').format(product.name))

            # <EndOfDeliveryFlag>
            if self.success:
                yc_qty_done = move_line.yc_qty_done

                new_move_ids = False
                if lot:  # and quantity_uom < move_line.product_qty:
                    new_move_ids = picking_in_obj.split_lot(
                        self.cr, self.uid, picking_in.id, partial, pos_no,
                        context=self.context)

                stock_move_vals = {
                    'yc_booking_voucher_id': booking_voucher_id,
                    'yc_booking_voucher_year': booking_voucher_year,
                    'yc_qty_done': yc_qty_done + quantity_uom,
                    'prodlot_id': lot and lot.id or False,
                }

                end_of_delivery_flag = self.xml_tools.nspath(
                    article, "wba:EndOfDeliveryFlag")[0].text
                if end_of_delivery_flag == '1':
                    stock_move_vals.update({'yc_eod_received': True})

                # Depending if we created a new stock.move while making the
                # split because of the lots, we use the new or the old stock
                # move.
                if new_move_ids:
                    move_line_ids = new_move_ids[picking_in.id]
                else:
                    move_line_ids = [move_line.id]
                stock_move_obj.write(self.cr, self.uid, move_line_ids,
                                     stock_move_vals, context=self.context)

                # The YC EoD flag will have been set just for the last move,
                # not the previous ones that got splitted, thus we search for
                # them and set the flag also.
                if end_of_delivery_flag == '1':
                    yc_eod_move_ids = stock_move_obj.search(
                        self.cr, self.uid, [
                            ('id', 'not in', move_line_ids),
                            ('yc_posno', '=', pos_no),
                            ('yc_eod_received', '=', False),
                            ('picking_id', '=', picking_in.id),
                        ], context=self.context)
                    if yc_eod_move_ids:
                        stock_move_obj.write(
                            self.cr, self.uid, yc_eod_move_ids,
                            {'yc_eod_received': True}, context=self.context)

                picking_in.write({'yellowcube_last_confirmation_timestamp':
                                      fields.datetime.now()})

        if not self.success:
            raise Warning('There were some errors in the WBA file', self.errors)

        return True

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
