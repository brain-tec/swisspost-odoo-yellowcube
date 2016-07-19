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
from xml_abstract_factory import xml_factory_decorator, xml_abstract_factory
from openerp.addons.pc_connect_master.utilities.misc import format_exception
from lxml import etree
from xsd.xml_tools import nspath, open_xml, validate_xml, xml_to_string
from datetime import date
from openerp.tools.translate import _
from openerp.release import version_info
V8 = True if version_info[0] > 7 else False
import logging
logger = logging.getLogger(__name__)


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
        stock_move_obj = self.pool.get('stock.move')
        warehouse_obj = self.pool.get('stock.warehouse')
        purchase_order_obj = self.pool.get('purchase.order')
        config_param_obj = self.pool.get('ir.config_parameter')
        connection_obj = self.pool.get('stock.connect')
        stock_production_lot_obj = self.pool.get('stock.production.lot')

        warehouse_id = connection_obj.browse(self.cr, self.uid, self.connection_id, context=self.context).warehouse_ids[0].id
        warehouse = warehouse_obj.browse(self.cr, self.uid, warehouse_id, context=self.context)

        xml = open_xml(file_text, _type='wba', print_error=self.print_errors)
        if nspath(xml, '//wba:WBA_List'):
            i = 0
            self.cr.execute("SAVEPOINT yellowcube_wba_xml_factory__WBAList;")
            for x in nspath(xml, '//wba:WBA_List/wba:WBA'):
                i += 1
                # First, we try to check the records
                try:
                    text = xml_to_string(x)
                    self.import_file(text)
                except Warning as w:
                    self.cr.execute("ROLLBACK TO SAVEPOINT yellowcube_wba_xml_factory__WBAList;")
                    print 'error>>>' * 5
                    print text
                    print '<<<error' * 5
                    raise Warning('Error on sub WBA file number {0}'.format(i), format_exception(w))
            self.cr.execute("RELEASE SAVEPOINT yellowcube_wba_xml_factory__WBAList;")
            return True

        validate_xml('wba', xml, print_error=False)

        imports = []

        # Gets the timestamp.
        timestamp_postgres = self.str_date_to_postgres(nspath(xml, "//wba:Timestamp")[0].text)

        # Header fields (under <GoodsReceiptHeader>)
        header = nspath(xml, "//wba:GoodsReceiptHeader")[0]

        # <BookingVoucherID> and <BookingVoucherYear>.
        booking_voucher_id = nspath(header, "wba:BookingVoucherID")[0].text
        booking_voucher_year = nspath(header, "wba:BookingVoucherYear")[0].text
        supplier_order_no = nspath(header, "wba:SupplierOrderNo")[0].text  # This is the stock.picking's ID.
        picking_in_ids = stock_obj.search(self.cr, self.uid, [('yellowcube_customer_order_no', '=', supplier_order_no),
                                                              ('state', 'not in', ['cancel', 'done']),
                                                              ], context=self.context)

        # Checks if the stock.picking exists. Otherwise, logs an issue an continues with the next one.
        self._check(warehouse, len(picking_in_ids) > 0, _("There is not any stock.picking with SupplierOrderNo (id) ={0}").format(supplier_order_no))
        if not self.success:
            raise Warning('There where some errors in the WBA file.', self.errors)

        # Gets the stock picking in associated to this purchase order.
        picking_in = stock_obj.browse(self.cr, self.uid, picking_in_ids[0], self.context)

        # <SupplierNo>.
        # We first check if the supplier has a supplier number, and if that's the case we
        # compare against it. Otherwise, we compare against the default supplier number
        # set for the connector.
        supplier_no = nspath(header, "wba:SupplierNo")[0].text
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

        for article in nspath(xml, "//wba:GoodsReceiptList/wba:GoodsReceiptDetail"):
            partials = {}
            partial = {}

            # <SupplierOrderPosNo>
            pos_no = int(nspath(article, "wba:SupplierOrderPosNo")[0].text)

            # Gets the stock.move associated to this line.
            move_line = None
            for line in picking_in.move_lines:
                if line.yc_posno == pos_no:
                    move_line = line
                    break

            self._check(picking_in, move_line is not None, _('Mismatch with stock picking line number {0}/{1}').format(pos_no, [x.yc_posno for x in picking_in.move_lines]))
            if not self.success:
                raise Warning('Error parsing wba file', self.errors)

            partials[move_line if V8 else "move{0}".format(move_line.id)] = partial

            partial['delivery_date'] = timestamp_postgres

            # Caches the product of the stock.move.
            product_id = move_line.product_id.id
            partial['product_id'] = product_id
            product = product_obj.browse(self.cr, self.uid, product_id, self.context)

            # <YCArticleNo>
            yc_article_no = nspath(article, "wba:YCArticleNo")[0].text
            if not product.yc_YCArticleNo:
                product_obj.write(self.cr, self.uid, product_id, {'yc_YCArticleNo': yc_article_no}, self.context)
                product.message_post(_('Product {0} with ID={1} did not have a YCArticleNo, so it was created with value {2}').format(product.name, product_id, yc_article_no))
            else:
                # If the product already had a YCArticleNo, then we check if the values match.
                self._check(warehouse, product.yc_YCArticleNo == yc_article_no, _("The 'YCArticleNo' does not match with the field 'YCArticleNo' of the product."))

            # <ArticleNo>
            article_no = nspath(article, "wba:ArticleNo")
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
            ean = nspath(article, "wba:EAN")
            if ean:
                ean = ean[0].text
                if not product.ean13:
                    product_obj.write(self.cr, self.uid, product_id, {'ean13': ean}, self.context)
                    product.message_post(_('Product {0} with ID={1} did not have an ean13 code, so it was created with value {2}').format(product.name, product_id, ean))
                else:
                    # If the product already has an EAN (field 'ean13' in Odoo) then we check if both values match.
                    self._check(warehouse, product.ean13 == ean, _("The 'EAN' does not match with the field 'ean13' of the product."))

            # <Lot>
            lot_search_domain = [('product_id', '=', product_id)]
            lot = nspath(article, 'wba:Lot')
            if lot:
                lot = lot[0].text
                lot_search_domain.append(('name', '=', lot))

            # <YCLot>
            yc_lot = nspath(article, 'wba:YCLot')
            if yc_lot:
                yc_lot = yc_lot[0].text
#                 lot_search_domain.append(('yellowcube_lot', '=', yc_lot))

            # If a lot was indicated but it does not exist in the system, create it.
            lot_ids = stock_production_lot_obj.search(self.cr, self.uid, lot_search_domain, context=self.context)
            if lot and (not lot_ids):
                lot_id_ = stock_production_lot_obj.create(self.cr, self.uid, {'name': lot,
                                                                              'yellowcube_lot': yc_lot or False,
                                                                              'product_id': product_id,
                                                                              'date': timestamp_postgres},
                                                          self.context)
                lot_ids = [lot_id_]
                lot = stock_production_lot_obj.browse(self.cr, self.uid, lot_id_, self.context)
                lot.message_post(_('Stock.production.lot {0} with ID={1} did not existed, and it was created by VoucherID {2}').format(lot.name, lot.id, booking_voucher_id),)

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

            if product.track_incoming:
                self._check(warehouse, lot is not None, _("The WBA file must contain a lot, otherwise the stock.move can not be updated for product {0}".format(product.name)))

            # <Plant>
            plant = nspath(article, 'wba:Plant')[0].text
            current_plant = self.get_param('plant_id', required=True)
            if current_plant:
                self._check(warehouse, current_plant == plant, _('Plant does not match with the value of the configuration parameter YC PlantID.'))
            elif not current_plant:
                self.set_param('plant_id', plant)

            #  <QuantityUOM>
            quantity_uom = float(nspath(article, "wba:QuantityUOM")[0].text)
            self._check(picking_in, move_line.product_qty >= quantity_uom, _('Product {0}: QuantityUOM is greater than that of the stock.move.').format(product.name))
            partial['product_qty'] = quantity_uom

            # <QuantityISO>
            quantity_iso = nspath(article, "wba:QuantityUOM")[0].attrib['QuantityISO']
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
            storage_location = nspath(article, "wba:StorageLocation")[0].text
            stock_type = nspath(article, "wba:StockType")
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
                end_of_delivery_flag = nspath(article, "wba:EndOfDeliveryFlag")[0].text
                complete_move_ids = []
                if V8:
                    for move in partials:
                        vals = partials[move]
                        new_move_id = stock_move_obj.split(self.cr,
                                                           self.uid,
                                                           move,
                                                           vals['product_qty'],
                                                           restrict_lot_id=vals.get('restrict_lot_id', False),
                                                           context=self.context)
                        stock_move_obj.action_done(self.cr, self.uid, [new_move_id], context=self.context)
                        complete_move_ids.append(new_move_id)
                else:
                    do_partial_data = picking_in.do_partial(partials)
                    # We store all the moves for this picking which are in state 'done'.
                    for partial_data_id in do_partial_data:
                        stock_picking_id = do_partial_data[partial_data_id]['delivered_picking']
                        sp = stock_obj.browse(self.cr, self.uid, stock_picking_id, context=self.context)
                        for move in sp.move_lines:
                            if move.state == 'done':
                                complete_move_ids.append(move.id)

                if end_of_delivery_flag == '1':  # delivery is completed.
                    number_of_pending_moves = stock_move_obj.search(self.cr, self.uid, [('picking_id', '=', picking_in.id),
                                                                                        ('state', 'in', ('draft', 'waiting', 'confirmed', 'assigned')),
                                                                                        ], context=self.context, count=True)
                    if number_of_pending_moves > 0:
                        pass  # They don't want this alarm __for the moment__.
                        #self.post_issue(picking_in, _('Tag EndOfDeliveryFlag was set, but there exists some stock move which are not in state finish nor cancelled.'))
                    else:
                        picking_in.action_done()  # Closes the picking.

                # moves may have been deleted in the process (???)
                # So that is why we need to iterate over those which are kept.
                move_ids = stock_move_obj.search(self.cr, self.uid, [('id', 'in', complete_move_ids)], context=self.context)
                stock_move_obj.write(self.cr, self.uid, move_ids, {'yc_booking_voucher_id': booking_voucher_id,
                                                                   'yc_booking_voucher_year': booking_voucher_year,
                                                                   }, self.context)

        if self.success:
            self.mark_record(picking_in.id, 'stock.picking' if V8 else 'stock.picking.in')
            # Only confirm when received the end of delivery flag
            # picking_in.action_done()
        else:
            raise Warning('There where some errors in the WBA file', self.errors)

        return True

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
