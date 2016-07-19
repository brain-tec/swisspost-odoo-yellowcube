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
import urllib
from xsd.xml_tools import nspath, open_xml, xml_to_string, validate_xml
from openerp.tools.translate import _
from openerp.release import version_info
V8 = True if version_info[0] > 7 else False
import logging
logger = logging.getLogger(__name__)


@xml_factory_decorator("war")
class yellowcube_war_xml_factory(xml_abstract_factory):

    post_issue_tags = ['lot', 'war-file']
    post_issue_thread = True
    success = True
    errors = None

    def _check(self, obj, cond, msg):
        if not cond:
            self.errors.append(msg)
            self.post_issue(obj, msg)
            self.success = False
            if self.context.get('show_errors', False):
                logger.error(msg)
        return bool(cond)

    def __init__(self, *args, **kargs):
        logger.debug("WAR factory created")
        self.ignore_import_errors = True

    def import_file(self, file_text):

        configuration_data = self.pool.get('configuration.data').get(self.cr, self.uid, [])

        logger.debug("Processing WAR file")
        self.success = True
        self.errors = []

        stock_obj = self.pool.get("stock.picking")
        partner_obj = self.pool.get('res.partner')
        stock_move_obj = self.pool.get('stock.move')
        product_obj = self.pool.get('product.product')
        connection_obj = self.pool.get('stock.connect')

        # Gets the warehouse of the YellowCube.
        warehouse = connection_obj.browse(self.cr, self.uid, self.connection_id, context=self.context).warehouse_ids[0]

        xml = open_xml(file_text, _type='war', print_error=self.print_errors)
        if nspath(xml, '//warr:WAR_List'):
            i = 0
            self.cr.execute("SAVEPOINT yellowcube_war_xml_factory__WARList;")
            for x in nspath(xml, '//warr:WAR_List/warr:WAR'):
                i += 1
                # First, we try to check the records
                try:
                    text = xml_to_string(x)
                    self.import_file(text)
                except Warning as w:
                    self.cr.execute("ROLLBACK TO SAVEPOINT yellowcube_war_xml_factory__WARList;")
                    print 'error>>>' * 5
                    print text
                    print '<<<error' * 5
                    raise Warning('Error on sub WAR file number {0}'.format(i), format_exception(w))
            self.cr.execute("RELEASE SAVEPOINT yellowcube_war_xml_factory__WARList;")
            return True

        validate_xml('war', xml, print_error=False)

        order_header = nspath(xml, "//warr:CustomerOrderHeader")[0]

        customer_order_no = nspath(order_header, "warr:CustomerOrderNo")[0].text
        stock_ids = stock_obj.search(self.cr, self.uid, [('yellowcube_customer_order_no', '=', customer_order_no),
                                                         ('state', 'in', ['confirmed', 'assigned'])], context=self.context)

        # Checks if the stock.picking exists. Otherwise, logs an issue an continues with the next one.
        self._check(warehouse, len(stock_ids) > 0, _("There is not any stock.picking with CustomerOrderNo ={0} in state confirmed or assigned.").format(customer_order_no))
        if not self.success:
            raise Warning('There where some errors in the WAR file: {0}'.format('\n'.join(self.errors)))

        # Gets the stock picking out associated to this WAR.
        picking_out = stock_obj.browse(self.cr, self.uid, stock_ids, context=self.context)[0]

        # Saves BookingVoucherID and BookingVoucherYear on the stock.move
        goods_issue_header = nspath(xml, "//warr:GoodsIssueHeader")[0]
        booking_voucher_id = nspath(goods_issue_header, "warr:BookingVoucherID")[0].text
        booking_voucher_year = nspath(goods_issue_header, "warr:BookingVoucherYear")[0].text
        # TODO: Put this at the end, like in the WBA.
#         for move_line in picking_out.move_lines:
#             stock_move_obj.write(self.cr, self.uid, move_line.id, {'booking_voucher_id': booking_voucher_id,
#                                                                     'booking_voucher_year': booking_voucher_year,
#                                                                     }, self.context)

        # Validates DepositorNo against the system's parameter. If does not match, then aborts and logs an issue.
        depositor_no = nspath(goods_issue_header, "warr:DepositorNo")[0].text
        expected_depositor_no = self.get_param('depositor_no', required=True)
        self._check(warehouse, expected_depositor_no, _("Variable YC DepositorNo is not defined in the configuration data."))
        self._check(warehouse, depositor_no == expected_depositor_no, _("Configuration variable YC DepositorNo does not match with that of tag 'DepositorNo'"))

        # <YCDeliveryNo>
        yellowcube_delivery_no = nspath(order_header, "warr:YCDeliveryNo")[0].text
        if yellowcube_delivery_no and picking_out.yellowcube_delivery_no and picking_out.yellowcube_delivery_no != yellowcube_delivery_no:
            self.post_issue(warehouse,
                            _('YCDeliveryNo {0} does not match its current value {1} in the stock picking.').format(picking_out.yellowcube_delivery_no,
                                                                                                                    yellowcube_delivery_no),
                            create=True,
                            reopen=True)

        if picking_out.yellowcube_delivery_no != yellowcube_delivery_no:
            stock_obj.write(self.cr, self.uid, [picking_out.id], {'yellowcube_delivery_no': yellowcube_delivery_no}, context=self.context)

        # <YCDeloveryDate>
        yellowcube_delivery_date = nspath(order_header, "warr:YCDeliveryDate")[0].text
        if yellowcube_delivery_date and picking_out.yellowcube_delivery_date and picking_out.yellowcube_delivery_date != yellowcube_delivery_date:
            self.post_issue(warehouse,
                            _('YCDeliveryDate {0} does not match its current value {1} in the stock picking.').format(picking_out.yellowcube_delivery_date,
                                                                                                                      yellowcube_delivery_date),
                            create=True,
                            reopen=True)

        if picking_out.yellowcube_delivery_date != yellowcube_delivery_date:
            stock_obj.write(self.cr, self.uid, [picking_out.id], {'yellowcube_delivery_date': yellowcube_delivery_date}, context=self.context)

        # <PartnerReference>
        partner_reference = nspath(order_header, "warr:PartnerReference")
        if partner_reference:
            partner_reference = partner_reference[0].text
            if picking_out.partner_id.ref:
                self._check(warehouse, picking_out.partner_id.ref == partner_reference, _('PartnerReference does not match its current value in the stock picking.'))
            else:
                partner_obj.write(self.cr, self.uid, picking_out.partner_id.id, {'ref': partner_reference}, context=self.context)

        # <PostalShipmentNo>
        carrier_tracking_ref = nspath(order_header, "warr:PostalShipmentNo")[0].text
        stock_obj.write(self.cr, self.uid, [picking_out.id], {'carrier_tracking_ref': carrier_tracking_ref}, context=self.context)

        partials = {}
        id_table = {}
        i = 1
        for line in sorted([x.id for x in picking_out.move_lines]):
            id_table[i] = line
            i += 1

        for order_move in nspath(xml, "//warr:CustomerOrderDetail"):
            partial = {}

            pos_no = int(nspath(order_move, "warr:CustomerOrderPosNo")[0].text)

            # Gets the stock.move associated to this line.
            move_line = None
            for line in picking_out.move_lines:
                if line.id == id_table[pos_no]:
                    move_line = line
                    break

            # Checks that the line exists.
            self._check(picking_out, move_line is not None, _('CustomerOrderPosNo={0}: Mismatch with stock picking line number').format(pos_no))
            if not self.success:
                raise Warning('Error parsing WAR file: {0}'.format('\n'.join(self.errors)))

            partials[move_line if V8 else "move{0}".format(move_line.id)] = partial

            # Caches the product of the stock.move.
            product_id = move_line.product_id.id
            partial['product_id'] = product_id
            product = product_obj.browse(self.cr, self.uid, product_id, self.context)

            # <YCArticleNo>
            yc_article_no = nspath(order_move, "warr:YCArticleNo")[0].text
            if product.yc_YCArticleNo:
                self._check(picking_out, product.yc_YCArticleNo == yc_article_no, _('Product {0} (id={1}): YCArticleNo does not match with YCArticleNo.').format(product.name, product_id))
            else:
                product_obj.write(self.cr, self.uid, product_id, {'yc_YCArticleNo': yc_article_no}, self.context)

            # <ArticleNo>
            article_no = nspath(order_move, "warr:ArticleNo")
            if article_no:
                article_no = article_no[0].text
                self._check(picking_out, product.default_code == article_no, _('Product {0} (id={1}): ArticleNo does not match with default_code.').format(product.name, product_id))

            # <EAN>
            ean = nspath(order_move, "warr:EAN")
            if ean:
                ean = ean[0].text
                if product.ean13:
                    self._check(picking_out, product.ean13 == ean, _('Product {0} (id={1}): EAN does not match with ean13.').format(product.name, product_id))
                else:
                    product_obj.write(self.cr, self.uid, product_id, {'ean13': ean}, self.context)

            # <Lot>
            lot = nspath(order_move, "warr:Lot")
            if lot:
                lot = lot[0].text

                # Searches for that lot in the system.
                lot_ids = self.pool.get('stock.production.lot').search(self.cr, self.uid, [('name', '=', lot),
                                                                                           ('product_id', '=', product_id)
                                                                                           ], context=self.context)
                if not lot_ids:
                    self._check(warehouse, False, _('Lot {0} for product {1} (id={2}) does not exist in the system').format(lot, product.name, product_id))
                elif getattr(move_line, 'restrict_lot_id' if V8 else 'prodlot_id'):
                    if self._check(picking_out, getattr(move_line, 'restrict_lot_id' if V8 else 'prodlot_id').name == lot, _('Product {0} (id={1}): Lot does not match the lot indicated of the original stock.move.').format(product_obj.name, product_id)):
                        partial['restrict_lot_id' if V8 else 'prodlot_id'] = lot_ids[0]

            if product.track_outgoing:
                self._check(warehouse, lot, _("The WAR file must contain a lot, otherwise the stock.move can not be updated for product {0}".format(product.name)))

            # <Plant>
            plant = nspath(order_move, "warr:Plant")[0].text
            current_plant = self.get_param('plant_id', required=True)
            if current_plant:
                self._check(picking_out, current_plant == plant, _('Product {0} (id={1}): Plant does not match with the value of the configuration parameter YC PlantID.').format(product.name, product_id))
            elif not current_plant:
                configuration_data.write(self.cr, self.uid, configuration_data.id, {'yc_plant_id': plant}, self.context)

            #  <QuantityUOM>
            quantity_uom = float(nspath(order_move, "warr:QuantityUOM")[0].text)
            self._check(picking_out, move_line.product_qty >= quantity_uom, _('Product {0} (id={1}): QuantityUOM is greater than that of the stock.move.').format(product.name, product_id))
            partial['product_qty'] = quantity_uom

            # <QuantityISO>
            quantity_iso = nspath(order_move, "warr:QuantityUOM")[0].attrib['QuantityISO']
            uom_iso_list = self.pool.get('product.uom').search(self.cr, self.uid, [('uom_iso', '=', quantity_iso)], context=self.context)
            if len(uom_iso_list) > 0 and move_line.product_uom and (quantity_iso != move_line.product_uom.uom_iso):
                self._check(picking_out, False, _('Product {0} (id={1}): Attribute QuantityISO does not match the ISO code indicated of the original stock.move.').format(product.name, product_id))
            else:
                if not move_line.product_uom:
                    product_uom = uom_iso_list[0]
                    partial['product_uom'] = product_uom
                else:
                    self._check(picking_out, move_line.product_uom.uom_iso == quantity_iso, _('Product {0} (id={1}): Attribute QuantityISO does not match that of the stock.move.').format(product.name, product_id))
                    partial['product_uom'] = move_line.product_uom.id

            # Checks <StorageLocation> and <StockType>
            # Notes: Check together with StorageLocation against location_id on stock.move - alarm if wrong.
            #        If free type (' ', '0', 'F') use the StorageLocation, otherwise location YBLK.
            storage_location = nspath(order_move, "warr:StorageLocation")[0].text
            stock_type = nspath(order_move, "warr:StockType")
            if move_line.location_id or move_line.location_dest_id:
                location_names = []
                if move_line.location_id:
                    location_names.append(move_line.location_id.name)
                if move_line.location_dest_id:
                    location_names.append(move_line.location_dest_id.name)

                if stock_type:
                    # If there exists the tag <StockType>, then we follow the rules.
                    stock_type = stock_type[0].text
                    if stock_type not in ('X', 'S', '2', '3', '0', 'F', ' '):
                        self._check(picking_out, False, _("Product {0} (id={1}): StockType had value '{2}', which is not allowed.").format(product.name, product_id, stock_type))
                    elif stock_type in ('0', 'F', ' '):
                        self._check(picking_out, storage_location in location_names, _('Product {0} (id={1}): StorageLocation {2} and StockType {3} does not match with the location indicated in the stock.move {4}').format(product.name, product_id, storage_location, stock_type, location_names))
                    else:
                        self._check(picking_out, 'YBLK' in location_names, _("Product {0} (id={1}): StorageLocation must be 'YBLK' since StockType is not a free type.").format(product.name, product_id))
                else:
                    # If <StockType> does not exist, it just checks that the values match.
                    if storage_location not in location_names:
                        self._check(picking_out, False, _('Product {0} (id={1}): StorageLocation {2} does not match with the location indicated in the stock.move {3}').format(product.name, product_id, storage_location, location_names))
            else:
                self._check(picking_out, False, _('Product {0} (id={1}): The stock move does not have a location_id.').format(product.name, product_id))

            # <Serial Numbers>
            serial_numbers = nspath(order_move, "warr:SerialNumbers")
            if serial_numbers:
                serial_numbers = serial_numbers[0].text
                if move_line.serial_number_scanned:
                    self._check(picking_out, move_line.serial_number_scanned == serial_numbers, _('Product {0} (id={1}): SerialNumbers does not match the serial_number_scanned indicated of the original stock.move.').format(product.name, product_id))
                else:
                    stock_move_obj.write(self.cr, self.uid, move_line.id, {'serial_number_scanned': serial_numbers}, self.context)

        if self.success:
            picking_id = picking_out.id

            picking_out.message_post(_('Imported WAR file BookingVoucherID={0} BookingVoucherYear={1}').format(booking_voucher_id, booking_voucher_year))
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
            else:
                backorder_id, picking_id = picking_out.wrapper_do_partial(partials)

                # Pickings created by WARs as backorders are not sent to the warehouse, by default.
                if backorder_id:
                    stock_obj.write(self.cr, self.uid, backorder_id, {'do_not_send_to_warehouse': True,
                                                                      }, context=self.context)

            picking_to_deliver = stock_obj.browse(self.cr, self.uid, picking_id, context=self.context)
            picking_to_deliver.action_done()
            picking_to_deliver.set_stock_moves_done()

            # Stores the values associated to BookingVoucherId and BookingVoucherYear, for reference.
            move_ids = [move.id for move in picking_out.move_lines]
            stock_move_obj.write(self.cr, self.uid, move_ids, {'yc_booking_voucher_id': booking_voucher_id,
                                                               'yc_booking_voucher_year': booking_voucher_year,
                                                               }, self.context)
            self.mark_record(picking_out.id, 'stock.picking' if V8 else 'stock.picking.out')

            # The message is sent ONLY if we had success.
#             picking_out.message_post(body=_("""Your order has been shipped through {0} and it can be tracked in the next link:\
#                                             <br/>\
#                                             <a href='https://www.post.ch/swisspost-tracking?formattedParcelCodes={1}'>Track&Trace</a>\
#                                             """).format(picking_out.carrier_id.name, urllib.quote(picking_out.carrier_tracking_ref)),
#                                      type='comment',
#                                      subtype="mail.mt_comment",
#                                      context=self.context,
#                                      partner_ids=picking_out.carrier_id and [picking_out.carrier_id.partner_id.id] or [])
        else:
            raise Warning('There where some errors in the WAR file: {0}'.format('\n'.join(self.errors)))

        return True

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
