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
from xml_abstract_factory import xml_factory_decorator, xml_abstract_factory
from openerp.addons.pc_connect_master.utilities.others import format_exception
from openerp.tools.translate import _
from openerp.release import version_info
V8 = True if version_info[0] > 7 else False
import logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


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

        logger.debug("Processing WAR file")
        self.success = True
        self.errors = []

        stock_obj = self.pool.get("stock.picking")
        product_obj = self.pool.get('product.product')
        connection_obj = self.pool.get('stock.connect')
        lot_obj = self.pool.get('stock.production.lot')

        write_in_picking = {}  # There's just one picking (the one of the file)
        write_in_partner = {}  # There's just one partner (that of the picking)
        write_in_conf = {}  # There's just one configuration.
        write_in_products = {}  # There can be several products.
        write_in_stock_moves = {}  # There can be several stock.moves.

        # Gets the warehouse of the YellowCube.
        warehouse = connection_obj.browse(self.cr, self.uid, self.connection_id, context=self.context).warehouse_ids[0]

        xml = self.xml_tools.open_xml(
            file_text, _type='war', print_error=self.print_errors)
        if self.xml_tools.nspath(xml, '//warr:WAR_List'):
            i = 0
            self.cr.execute("SAVEPOINT yellowcube_war_xml_factory__WARList;")
            for x in self.xml_tools.nspath(xml, '//warr:WAR_List/warr:WAR'):
                i += 1
                # First, we try to check the records
                try:
                    text = self.xml_tools.xml_to_string(x)
                    self.import_file(text)
                except Warning as w:
                    self.cr.execute("ROLLBACK TO SAVEPOINT yellowcube_war_xml_factory__WARList;")
                    print 'error>>>' * 5
                    print text
                    print '<<<error' * 5
                    raise Warning('Error on sub WAR file number {0}'.format(i), format_exception(w))
            self.cr.execute("RELEASE SAVEPOINT yellowcube_war_xml_factory__WARList;")
            return True

        errors = self.xml_tools.validate_xml('war', xml, print_error=False)
        if errors:
            raise Warning(errors)

        order_header = self.xml_tools.nspath(
            xml, "//warr:CustomerOrderHeader")[0]

        customer_order_no = self.xml_tools.nspath(
            order_header, "warr:CustomerOrderNo")[0].text
        stock_ids = stock_obj.search(self.cr, self.uid, [('yellowcube_customer_order_no', '=', customer_order_no),
                                                         ('state', 'in', ['confirmed', 'assigned'])], context=self.context)

        # Checks if the stock.picking exists. Otherwise, logs an issue an continues with the next one.
        self._check(warehouse, len(stock_ids) > 0, _("There is not any stock.picking with CustomerOrderNo ={0} in state confirmed or assigned.").format(customer_order_no))
        if not self.success:
            raise Warning('There were some errors in the WAR file: {0}'.format('\n'.join(self.errors)))

        # Gets the stock picking out associated to this WAR.
        picking_out = stock_obj.browse(self.cr, self.uid, stock_ids, context=self.context)[0]

        # Saves BookingVoucherID and BookingVoucherYear to later save them
        # on the stock.move that are processed.
        goods_issue_header = self.xml_tools.nspath(
            xml, "//warr:GoodsIssueHeader")[0]
        yc_booking_voucher_id = self.xml_tools.nspath(
            goods_issue_header, "warr:BookingVoucherID")[0].text
        yc_booking_voucher_year = self.xml_tools.nspath(
            goods_issue_header, "warr:BookingVoucherYear")[0].text

        # Validates DepositorNo.
        depositor_no = self.xml_tools.nspath(
            goods_issue_header, "warr:DepositorNo")[0].text
        self.check_tag_war_depositorno(depositor_no, warehouse, picking_out)

        # <YCDeliveryNo>
        yellowcube_delivery_no = self.xml_tools.nspath(
            order_header, "warr:YCDeliveryNo")[0].text
        if yellowcube_delivery_no and picking_out.yellowcube_delivery_no and picking_out.yellowcube_delivery_no != yellowcube_delivery_no:
            self.post_issue(warehouse,
                            _('YCDeliveryNo {0} does not match its current value {1} in the stock picking.').format(picking_out.yellowcube_delivery_no,
                                                                                                                    yellowcube_delivery_no),
                            create=True,
                            reopen=True)

        if picking_out.yellowcube_delivery_no != yellowcube_delivery_no:
            write_in_picking.update({'yellowcube_delivery_no': yellowcube_delivery_no})

        # <YCDeloveryDate>
        yellowcube_delivery_date = self.xml_tools.nspath(
            order_header, "warr:YCDeliveryDate")[0].text
        if yellowcube_delivery_date and picking_out.yellowcube_delivery_date and picking_out.yellowcube_delivery_date != yellowcube_delivery_date:
            self.post_issue(warehouse,
                            _('YCDeliveryDate {0} does not match its current value {1} in the stock picking.').format(picking_out.yellowcube_delivery_date,
                                                                                                                      yellowcube_delivery_date),
                            create=True,
                            reopen=True)

        if picking_out.yellowcube_delivery_date != yellowcube_delivery_date:
            write_in_picking.update({'yellowcube_delivery_date': yellowcube_delivery_date})

        # <PartnerReference>
        partner_reference = self.xml_tools.nspath(
            order_header, "warr:PartnerReference")
        if partner_reference:
            self.process_tag_war_partnerreference(partner_reference[0].text,
                                                  picking_out, warehouse,
                                                  write_in_partner)

        # <PostalShipmentNo>
        # This is a mandatory field with length at least 1 according to the
        # Yellowcube Handbook, but an empty tag was received with a client,
        # so things may have changed; so we write code to deal with that.
        carrier_tracking_ref = \
            self.xml_tools.nspath(order_header, "warr:PostalShipmentNo")
        if carrier_tracking_ref:
            carrier_tracking_ref = carrier_tracking_ref[0].text or ''
            if len(carrier_tracking_ref) > 0 and \
               carrier_tracking_ref[-1] not in (',', ';'):
                carrier_tracking_ref += ';'
            new_carrier_tracking_ref = \
                (picking_out.carrier_tracking_ref or '') + carrier_tracking_ref
            write_in_picking.update({
                'carrier_tracking_ref': new_carrier_tracking_ref})

        partials = {}
        id_table = {}
        i = 1
        for line_id in sorted([x.id for x in picking_out.move_lines]):
            id_table[i] = line_id
            i += 1

        for order_move in self.xml_tools.nspath(
                xml, "//warr:CustomerOrderDetail"):

            pos_no = int(self.xml_tools.nspath(
                order_move, "warr:CustomerOrderPosNo")[0].text)

            # Gets the stock.move associated to this line.
            move_line = self.get_associated_move_line(id_table, picking_out,
                                                      pos_no)

            if not move_line:
                raise Warning("No move line was found on picking.out with "
                              "ID={0} for pos_no={1}".format(picking_out.id,
                                                             pos_no))

            # Saves BookingVoucherID and BookingVoucherYear on the stock.move
            write_in_stock_moves.setdefault(move_line.id, {}).update({
                'yc_booking_voucher_id': yc_booking_voucher_id,
                'yc_booking_voucher_year': yc_booking_voucher_year,
            })

            # Checks that the line exists.
            self._check(picking_out, move_line is not None, _('CustomerOrderPosNo={0}: Mismatch with stock picking line number').format(pos_no))
            if not self.success:
                raise Warning('Error parsing WAR file: {0}'.format('\n'.join(self.errors)))

            partial_key = move_line if V8 else "move{0}".format(move_line.id)
            if partial_key in partials:
                partial = partials[partial_key]
            else:
                partial = {}
                # Product Quantity is the only field and increases. Other fields WILL have the same value between details
                partial['product_qty'] = 0
                partials[partial_key] = partial

            # Caches the product of the stock.move.
            product_id = move_line.product_id.id
            partial['product_id'] = product_id
            product = product_obj.browse(self.cr, self.uid, product_id, self.context)

            # <YCArticleNo>
            yc_article_no = self.xml_tools.nspath(
                order_move, "warr:YCArticleNo")[0].text
            self.check_tag_war_ycarticleno(yc_article_no, picking_out,
                                           product, write_in_products)

            # <ArticleNo>
            article_no = self.xml_tools.nspath(order_move, "warr:ArticleNo")
            if article_no:
                article_no = article_no[0].text
                self._check(picking_out, product.default_code == article_no, _('Product {0} (id={1}): ArticleNo does not match with default_code.').format(product.name, product_id))

            # <EAN>
            ean = self.xml_tools.nspath(order_move, "warr:EAN")
            if ean and not self.get_param('ignore_ean'):
                # If we choose not to ignore the EAN, we process it;
                # otherwise we do nothing with the EAN received.
                ean = ean[0].text
                if product.ean13:
                    self._check(picking_out, product.ean13 == ean,
                                _('Product {0} (id={1}): EAN does not '
                                  'match with ean13.').format(product.name,
                                                              product_id))
                else:
                    write_in_products.setdefault(product_id, {}).update(
                        {'ean13': ean})

            # <Lot>
            lot = self.xml_tools.nspath(order_move, "warr:Lot")
            if lot:
                lot = lot[0].text

                # Searches for that lot in the system.
                lot_ids = self.pool.get('stock.production.lot').search(self.cr, self.uid, [('name', '=', lot),
                                                                                           ('product_id', '=', product_id)
                                                                                           ], context=self.context)
                if not lot_ids:
                    self._check(warehouse, False, _('Lot {0} for product {1} (id={2}) does not exist in the system').format(lot, product_obj.name, product_id))
                elif move_line.prodlot_id:
                    if self._check(picking_out, move_line.prodlot_id.name == lot, _('Product {0} (id={1}): Lot does not match the lot indicated of the original stock.move.').format(product.name, product_id)):
                        partial['prodlot_id'] = lot_ids[0]

            # If we are in WAR1 or WAR2, since they don't send the lot but we
            # may need them, then we have to invent a dummy one.
            war12_lot_name = self.get_param('war12_dummy_lot_name')
            if product.track_outgoing and \
                    not lot \
                    and war12_lot_name:
                lot_ids = lot_obj.search(self.cr, self.uid, [
                    ('name', '=', war12_lot_name),
                    ('product_id', '=', product_id),
                ], limit=1, context=self.context)
                if not lot_ids:
                    # The lot does not exist and has to be created.
                    lot_ids = [lot_obj.create(self.cr, self.uid, {
                        'name': war12_lot_name,
                        'product_id': product_id,
                        # 'use_date': '2999-12-12 23:59:59',
                    }, context=self.context)]
                lot = lot_obj.browse(self.cr, self.uid, lot_ids[0],
                                     context=self.context).name
                partial['prodlot_id'] = lot_ids[0]

            if product.track_outgoing:
                self._check(warehouse, lot, _("The WAR file must contain a lot, otherwise the stock.move can not be updated for product {0}".format(product.name)))

            # <Plant>
            plant = self.xml_tools.nspath(order_move, "warr:Plant")[0].text
            current_plant = self.get_param('plant_id', required=True)
            if current_plant:
                self._check(picking_out, current_plant == plant, _('Product {0} (id={1}): Plant does not match with the value of the configuration parameter YC PlantID.').format(product.name, product_id))
            elif not current_plant:
                write_in_conf.update({'yc_plant_id': plant})

            #  <QuantityUOM>
            quantity_uom = float(self.xml_tools.nspath(
                order_move, "warr:QuantityUOM")[0].text)
            self._check(picking_out, move_line.product_qty >= quantity_uom, _('Product {0} (id={1}): QuantityUOM is greater than that of the stock.move.').format(product.name, product_id))
            # new moves, increase the quantity on the partial
            partial['product_qty'] += quantity_uom

            # <QuantityISO>
            quantity_iso = self.xml_tools.nspath(
                order_move, "warr:QuantityUOM")[0].attrib['QuantityISO']
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
            storage_location = self.xml_tools.nspath(
                order_move, "warr:StorageLocation")[0].text
            stock_type = self.xml_tools.nspath(order_move, "warr:StockType")
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
            serial_numbers = self.xml_tools.nspath(
                order_move, "warr:SerialNumbers")
            if serial_numbers:
                serial_numbers = serial_numbers[0].text
                if move_line.serial_number_scanned:
                    self._check(picking_out, move_line.serial_number_scanned == serial_numbers, _('Product {0} (id={1}): SerialNumbers does not match the serial_number_scanned indicated of the original stock.move.').format(product.name, product_id))
                else:
                    write_in_stock_moves[move_line.id].update({
                        'serial_number_scanned': serial_numbers})

        if self.success:
            try:
                self._apply_changes_by_war(picking_out,
                                           write_in_picking,
                                           write_in_partner,
                                           write_in_conf,
                                           write_in_products,
                                           write_in_stock_moves,
                                           partials)
            except Exception as e:
                self.success = False
                self.errors.append(format_exception(e))

        if not self.success:
            raise Warning('There were some errors in the WAR file: {0}'.
                          format('\n'.join(self.errors)))

        return True

    def process_tag_war_partnerreference(self, partner_reference, picking_out,
                                         warehouse, write_in_partner):
        """ Processes the value for the tag <PartnerReference> of a WAR.
        """
        _partner_references = set([])
        if picking_out.partner_id.ref:
            _partner_references.add(picking_out.partner_id.ref)
        if picking_out.partner_id.parent_id and picking_out.partner_id.parent_id.ref:
            _partner_references.add(picking_out.partner_id.parent_id.ref)

        if _partner_references:
            self._check(warehouse, partner_reference in _partner_references,
                        _('PartnerReference does not match its current value '
                          'in the stock picking.'))
        else:
            write_in_partner({'ref': partner_reference})

    def check_tag_war_ycarticleno(self, yc_article_no, picking_out, product,
                                  write_in_products):
        """ Checks the tag <YCArticleNo> of the WAR. It is extracted as a new
            method because it is checked differently for connections which
            are not Yellowcube.
        """
        if product.yc_YCArticleNo:
            self._check(
                picking_out, product.yc_YCArticleNo == yc_article_no,
                _('Product {0} (id={1}): YCArticleNo does not match with '
                  'YCArticleNo.').format(product.name, product.id))
        else:
            write_in_products.setdefault(product.id, {}). \
                update({'yc_YCArticleNo': yc_article_no})

    def check_tag_war_depositorno(self, depositor_no, warehouse, picking_out):
        """ Checks the tag <DepositorNo> of the WAR. It is extracted as a new
            method because it is checked differently for connections which
            are not Yellowcube.
        """
        expected_depositor_no = self.get_param('depositor_no', required=True)
        self._check(warehouse, expected_depositor_no,
                    _("Variable YC DepositorNo is not defined in the "
                      "configuration data."))
        self._check(warehouse, depositor_no == expected_depositor_no,
                    _("Configuration variable YC DepositorNo does not match "
                      "with that of tag 'DepositorNo'"))

    def get_associated_move_line(self, id_table, picking_out, pos_no):
        """ Returns to what move in the picking received the position
            indicated by the CustomerOrderPosNo or the WAR refers.
        :param id_table: Mapping structure, corresponding of a dictionary,
        the keys of which are consecutive numbers (starting in 1) and the
        values being the ID of the stock.move within the picking_out, sorted
        in ascending order by ID (so move with key i has an ID which is lower
        than move with key i+1).
        :param picking_out: The picking.out where to find the move.
        :param pos_no: Value of CustomerOrderPosNo in the WAR.
        :return: 
        """
        move_line = None
        for line in picking_out.move_lines:
            if line.id == id_table[pos_no]:
                move_line = line
                break

        return move_line

    def _apply_changes_by_war(self,
                              picking_out,
                              write_in_picking,
                              write_in_partner,
                              write_in_conf,
                              write_in_products,
                              write_in_stock_moves,
                              partials):
        """ Applies the changes from a WAR into the database.
            
            Calling this method assumes the data provided is correct, and
            is the responsibility of the caller to ensure this, and to
            raise otherwise instead of calling this method.

        :param picking_out: The object stock.picking.out the WAR is applied to. 
        :param write_in_picking: Dictionary of values to write on the picking.
        :param write_in_partner:  Dictionary of values to write on the partner.
        :param write_in_conf: Dictionary of values to write on the config.
        :param write_in_products: Dictionary of dictionaries of values to
        write over the products the ids of which are the keys of the outer
        dictionary.
        :param write_in_stock_moves: Dictionary dictionaries of values to 
        write on the stock moves the ids of which are the keys of the outer
        dictionary.
        :param partials: Data expected by the method do_partials(), which
        (may) create a back-order if the goods are not enough to fulfill the
        original picking.
        :param info: Additional info that can be used in the case this method
        is used as a hook method.
        :return: 
        """
        cr, uid, context = self.cr, self.uid, self.context

        picking_obj = self.pool.get('stock.picking.out')
        partner_obj = self.pool.get('res.partner')
        conf_obj = self.pool.get('configuration.data')
        product_obj = self.pool.get('product.product')
        stock_move_obj = self.pool.get('stock.move')

        # It writes on the picking the values that the caller acquired.
        picking_obj.write(cr, uid, picking_out.id,
                          write_in_picking, context=context)

        # It writes on the partner the values that the caller acquired.
        partner_obj.write(cr, uid, picking_out.partner_id.id,
                          write_in_partner, context=context)

        # It writes on the configuration the values that the caller acquired.
        conf_data = conf_obj.get(cr, uid, [], context=context)
        conf_obj.write(cr, uid, conf_data.id,
                       write_in_conf, context=context)

        # It writes on the products the values that the caller acquired.
        for product_id, product_vals in write_in_products.iteritems():
            product_obj.write(cr, uid, product_id,
                              product_vals, context=context)

        backorder_id, picking_id = picking_out.wrapper_do_partial(partials)

        # Pickings created by WARs as backorders are
        # not sent to the warehouse, by default.
        if backorder_id:
            picking_obj.write(cr, uid, backorder_id,
                              {'do_not_send_to_warehouse': True},
                              context=context)

        picking_to_deliver = picking_obj.browse(cr, uid, picking_id,
                                                context=context)
        picking_to_deliver.action_done()
        picking_to_deliver.set_stock_moves_done()

        # It writes on the stock.moves the values that the caller acquired.
        for move_id, move_vals in write_in_stock_moves.iteritems():
            stock_move_obj.write(cr, uid, move_id, move_vals, context=context)

        # Creates a tracking link for the picking, and sends it through
        # the confirmation email to the client.
        picking_to_deliver.store_tracking_link()
        if conf_data.tracking_email_active:
            picking_to_deliver.send_tracking_email_to_client()

        return True

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
