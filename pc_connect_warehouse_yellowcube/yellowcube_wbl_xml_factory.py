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
from lxml import etree
from xml_abstract_factory import xml_factory_decorator, xml_abstract_factory
from openerp.addons.pc_log_data.log_data import write_log
from openerp.addons.pc_connect_master.utilities.others import format_exception
from datetime import datetime
from openerp import netsvc
from openerp.tools.translate import _
import logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


@xml_factory_decorator("wbl")
class yellowcube_wbl_xml_factory(xml_abstract_factory):
    _table = "stock.picking"

    def create_element(self, entity, text=None, attrib=None,
                       ns='https://service.swisspost.ch/apache/yellowcube/'
                          'YellowCube_WBL_REQUEST_SupplierOrders.xsd'):
        return self.xml_tools.create_element(entity, text, attrib, ns)

    def _check(self, obj, cond, msg):
        if not cond:
            self.post_issue(obj, msg)
            self.errors.append(msg)
            self.success = False
        return bool(cond)

    def __init__(self, *args, **kargs):
        logger.debug("WBL factory created")

    def create_element(self, entity, text=None, attrib=None,
                       ns='https://service.swisspost.ch/apache/yellowcube/'
                          'YellowCube_WBL_REQUEST_SupplierOrders.xsd'):
        return self.xml_tools.create_element(entity, text, attrib, ns)

    def check_and_load_uom(self, po_line_xml, po_line_index, product_id):

        # For Uom we received ISO code, so we look for the UOM having it.

        uom_obj = self.pool.get('product.uom')
        product_obj = self.pool.get('product.product')

        uom_iso = self.xml_tools.nspath(po_line_xml, "//wbl:QuantityISO")

        # UOM Iso is required as defined in xsd. No check needed about
        # existence

        uom_iso = uom_iso[po_line_index].text
        product_uom = uom_obj.search(
            self.cr, self.uid, [('uom_iso', '=', uom_iso)],
            context=self.context)
        if not product_uom:
            raise Warning(
                _('Could not locate UOM with ISO code {0} from '
                  'the WBL file.').format(uom_iso), self.errors)
        else:
            uom = uom_obj.browse(self.cr, self.uid, product_uom[0],
                                 context=self.context)
            self._check(
                uom, len(product_uom) == 1,
                _("There exist {0} UOM with ISO code {1}.").format(
                    len(product_uom), uom_iso))
            product_uom = product_uom[0]
        return product_uom

    def import_file(self, file_text):
        logger.debug("Processing WBL file")
        self.success = True
        self.errors = []

        wf_service = netsvc.LocalService("workflow")

        file_obj = self.pool.get('stock.connect.file')
        product_obj = self.pool.get('product.product')
        partner_obj = self.pool.get('res.partner')
        purchase_order_obj = self.pool.get('purchase.order')
        purchase_order_line_obj = self.pool.get('purchase.order.line')
        stock_warehouse_obj = self.pool.get('stock.warehouse')
        country_obj = self.pool.get('res.country')
        uom_obj = self.pool.get('product.uom')
        conf_obj = self.pool.get('configuration.data')

        xml = self.xml_tools.open_xml(
            file_text, _type='wbl', print_error=self.print_errors)

        self.cr.execute("SAVEPOINT yellowcube_wbl_xml_factory__WBL;")

        try:
            # Validating XML file, raises if error.
            error = self.xml_tools.validate_xml('wbl', xml, print_error=False)
            if error:
                raise Warning(error)

            # Getting warehouse from definition of stock.connect.file.
            # Its id is sent as additional parameter to those defined in abstract class
            stock_connect_file_id = False
            if 'stock_connect_file_id' in self.context:
                stock_connect_file_id = self.context['stock_connect_file_id']
            file_id = file_obj.browse(self.cr, self.uid, stock_connect_file_id, self.context)
            warehouse_id = file_id.warehouse_id.id

            # Getting Supplier Order section
            supplier_order = self.xml_tools.nspath(
                xml, "//wbl:SupplierOrder")[0]

            # Getting Supplier Order Header subsection
            supplier_order_header = self.xml_tools.nspath(
                supplier_order, "//wbl:SupplierOrderHeader")[0]

            # Given the Supplier No that we receive, we look for an existing partner with that code.
            # If found, we use it as partner for the PO, otherwise we raise an error.
            # If more than one supplier is found, an error message is added and first one found is taken
            supplier_no = self.xml_tools.nspath(
                supplier_order_header, "//wbl:SupplierNo")[0].text

            # Getting supplier prefix from config
            conf_data = conf_obj.get(self.cr, self.uid, [], context=self.context)
            supplier_no = conf_data.supplier_prefix_ref + supplier_no

            supplier_id = partner_obj.search(self.cr, self.uid, [('ref', '=', supplier_no)])
            if not supplier_id:
                raise Warning(_("Could not locate Supplier with id {0} from "
                                "the WBL file.").format(supplier_no))

            self._check(partner_obj.browse(self.cr, self.uid, supplier_id[0]), len(supplier_id) == 1,
                    _("There exist {0} partners with YC Supplier No {1}.").format(len(supplier_id), supplier_no))
            supplier_id = supplier_id[0]

            supplier = partner_obj.browse(self.cr, self.uid, supplier_id)

            # Getting fields for PO as external ref, order date or delivery date

            supplier_order_no = self.xml_tools.nspath(
                supplier_order_header, "//wbl:SupplierOrderNo")[0].text

            supplier_order_date = self.xml_tools.nspath(
                supplier_order_header, "//wbl:SupplierOrderDate")[0].text
            supplier_order_date = datetime.strptime(supplier_order_date, "%Y%m%d").strftime('%Y-%m-%d')

            # If the <SupplierOrderDeliveryDate> is not given, then it sets
            # the expected date to be the default one, but it does it after
            # the purchase order has been created, since the default value
            # takes into account the lines of the purchase.
            supplier_order_delivery_date = self.xml_tools.nspath(
                supplier_order_header,
                "//wbl:SupplierOrderDeliveryDate")
            if supplier_order_delivery_date:
                supplier_order_delivery_date = datetime.strptime(
                    supplier_order_delivery_date[0].text,
                    "%Y%m%d").strftime('%Y-%m-%d')

            # Creating PO with values we have received and others taken from supplier
            vals = {'partner_id': supplier_id,
                    'partner_ref': supplier_order_no,
                    'date_order': supplier_order_date,
                    'warehouse_id': warehouse_id,
                    'location_id': stock_warehouse_obj.browse(self.cr, self.uid, warehouse_id).lot_input_id.id,
                    'pricelist_id': supplier.property_product_pricelist_purchase.id,
                    'fiscal_position': supplier.property_account_position and supplier.property_account_position.id or False,
                    'payment_term_id': supplier.property_supplier_payment_term.id or False,
                    }
            if supplier_order_delivery_date:
                vals.update({
                    'minimum_planned_date': supplier_order_delivery_date,
                })
            new_po_id = purchase_order_obj.create(self.cr, self.uid, vals, self.context)

            # Modifies the name of the Purchase Order so that it has the
            # value of <SupplierOrderNo> appended, separated by a dash.
            new_po = purchase_order_obj.browse(self.cr, self.uid, new_po_id,
                                               context=self.context)
            new_po.write({'name': '{0}-{1}'.format(new_po.name,
                                                   supplier_order_no)})

            # Getting PO lines subsection
            positions = self.xml_tools.nspath(
                supplier_order, "//wbl:SupplierOrderPositions/wbl:Position")
            for i in range(0,len(positions)):
                # Sequence of PO line
                pos_no = self.xml_tools.nspath(
                    positions[i], "//wbl:PosNo")[i].text

                # Getting product id. Looking for product with that code.
                # If no product is found, an exception is raised. If more than one found, an error message is added
                # and first one found is taken as product
                article_no = self.xml_tools.nspath(
                    positions[i], "//wbl:ArticleNo")[i].text
                product_id = product_obj.search(self.cr, self.uid, [('default_code', '=', article_no)])
                if not product_id:
                    raise Warning('Could not locate Product with code {0} from the WBL file.'.format(article_no),
                                  self.errors)
                else:
                    self._check(product_obj.browse(self.cr, self.uid, product_id[0]), len(product_id) == 1,
                                _("There exist {0} products with code {1}.").format(len(product_id), article_no))
                    product_id = product_id[0]

                # Getting other fields for PO line as quantity, uom, and description
                product_qty = self.xml_tools.nspath(
                    positions[i], "//wbl:Quantity")[i].text

                # Checks if UOM was given in the WBL and loads it
                product_uom = self.check_and_load_uom(positions[i], i,
                                                      product_id)

                # The product name is taken from the <PostText> which is
                # optional. So if it doesn't appear the name is taken from
                # the product itself.
                product_name = False
                pos_text = self.xml_tools.nspath(positions[i], "//wbl:PosText")
                if pos_text and len(pos_text) >= (i + 1):
                    product_name = pos_text[i].text
                if not product_name:
                    prod = product_obj.browse(self.cr, self.uid, product_id,
                                              context=self.context)
                    product_name = prod.name

                # Calling to onchange of product to get some other needed vals
                line_vals = purchase_order_line_obj.onchange_product_id(self.cr, self.uid, False,
                                supplier.property_product_pricelist_purchase.id, product_id,
                                float(product_qty), product_uom, supplier_id, supplier_order_date,
                                supplier.property_account_position and supplier.property_account_position.id or False,
                                supplier_order_delivery_date, False, False, self.context)

                line_vals = line_vals['value']
                # Updating vals for PO line with description we received, adding link to PO created before,
                # reformatting taxes to be added properly, as it is a m2m field
                line_vals.update({'product_id': product_id,
                                  'name': product_name,
                                  'product_qty': float(product_qty),
                                  'product_uom': product_uom,
                                  'order_id': new_po_id,
                                  'taxes_id': [(4,x) for x in line_vals['taxes_id']],
                                  'yc_posno': pos_no,
                                })
                # Creating PO line
                purchase_order_line_obj.create(self.cr, self.uid, line_vals, self.context)

            if not supplier_order_delivery_date:
                # If we didn't set SupplierOrderDeliveryDate then we make
                # it be the default value, for that we needed to create
                # the lines of the purchase.
                supplier_order_delivery_date = \
                    purchase_order_obj._minimum_planned_date(
                        self.cr, self.uid, [new_po_id], False, False,
                        context=self.context)[new_po_id]
                new_po.write({
                    'minimum_planned_date': supplier_order_delivery_date,
                })

            if self.success:
                # Confirm PO which creates related picking in
                wf_service.trg_validate(self.uid, 'purchase.order', new_po_id, 'purchase_confirm', self.cr)
            else:
                raise Warning('There were some errors in the WBL file', self.errors)

        except Warning as w:
            self.cr.execute("ROLLBACK TO SAVEPOINT yellowcube_wbl_xml_factory__WBL;")
            print 'error>>>' * 5
            print self.xml_tools.xml_to_string(xml)
            print '<<<error' * 5
            raise Warning('Error on WBL file', format_exception(w))

        self.cr.execute("RELEASE SAVEPOINT yellowcube_wbl_xml_factory__WBL;")

        return new_po_id

    def get_main_file_name(self, _object):
        # Since the functional only computes when the view is loaded, we have to directly call the function which computes the name.
        name = _object.get_yc_filename_postfix()
        return name

    def get_export_files(self, sale_order):
        return {}

    def generate_root_element(self, stock_picking):

        # xml = '<?xml version="1.0" encoding="UTF-8"?>\n'
        # xml = '{0}<WAB xsi:noNamespaceSchemaLocation="YellowCube_WAB_Warenausgangsbestellung.xsd" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">\n'.format(xml)
        xml_root = self.create_element('WBL')
        purchase_order = stock_picking.purchase_id

        # WAB > ControlReference
        now = datetime.now()
        xml_control_reference = self.create_element('ControlReference')
        xml_control_reference.append(self.create_element('Type', text='WBL'))
        xml_control_reference.append(self.create_element(
            'Sender', text=self.get_param('sender', required=True)))
        xml_control_reference.append(self.create_element(
            'Receiver', text=self.get_param('receiver', required=True)))
        xml_control_reference.append(self.create_element(
            'Timestamp',
            text='{0:04d}{1:02d}{2:02d}{3:02d}{4:02d}{5:02d}'.format(
                now.year, now.month, now.day, now.hour, now.hour, now.minute)
        ))
        xml_control_reference.append(self.create_element('OperatingMode', text=self.get_param('operating_mode', required=True)))
        xml_control_reference.append(self.create_element('Version', text='1.0'))
        xml_root.append(xml_control_reference)

        xml_supplier_order = self.create_element("SupplierOrder")
        xml_root.append(xml_supplier_order)

        xml_supplier_order_header = self.create_element('SupplierOrderHeader')
        xml_supplier_order.append(xml_supplier_order_header)
        xml_supplier_order_header.append(self.create_element(
            'DepositorNo', self.get_param('depositor_no', required=True)))
        xml_supplier_order_header.append(self.create_element(
            'Plant', self.get_param('plant_id', required=True)))
        
        
        # Regarding the 'YC SupplierNo', we first check if the supplier has a supplier number,
        # and if that's the case we use it. Otherwise, we use the default supplier number
        # set for the connector.
        if stock_picking.partner_id.supplier and stock_picking.partner_id.yc_supplier_no:
            yc_supplier_no = stock_picking.partner_id.yc_supplier_no
        else:
            yc_supplier_no = self.get_param('supplier_no', required=True)
        xml_supplier_order_header.append(self.create_element(
            'SupplierNo', yc_supplier_no))

#         xml_supplier_order_header.append(create_element('SupplierOrderNo', stock_picking.yellowcube_customer_order_no))
        xml_supplier_order_header.append(etree.Comment(text='res.partner#{0}'.format(stock_picking.partner_id.id)))
        xml_supplier_order_header.append(self.create_element(
            'SupplierName1', stock_picking.partner_id.name))
        xml_supplier_order_header.append(self.create_element(
            'SupplierStreet', '{0} {1}'.format(
                stock_picking.partner_id.street,
                stock_picking.partner_id.street_no)))
        xml_supplier_order_header.append(self.create_element(
            'SupplierCountryCode',
            text=stock_picking.partner_id.country_id.code))
        xml_supplier_order_header.append(self.create_element(
            'SupplierZIPCode', text=stock_picking.partner_id.zip))
        xml_supplier_order_header.append(self.create_element(
            'SupplierCity', text=stock_picking.partner_id.city))
        xml_supplier_order_header.append(self.create_element(
            'SupplierOrderNo',
            stock_picking.get_customer_order_no()[stock_picking.id]))
        # CustomerOrderNo is only required for cross-docking
        # xml_supplier_order_header.append(create_element('CustomerOrderNo', stock_picking.get_customer_order_no()[stock_picking.id]))
        if stock_picking.date:
            dateorder = stock_picking.date.split(' ')[0]
            xml_supplier_order_header.append(self.create_element(
                'SupplierOrderDate', dateorder.replace('-', '')))
        if stock_picking.min_date:
            dateorder = stock_picking.min_date.split(' ')[0]
            xml_supplier_order_header.append(self.create_element(
                'SupplierOrderDeliveryDate', dateorder.replace('-', '')))

        xml_supplier_order_positions = self.create_element(
            'SupplierOrderPositions')
        xml_supplier_order.append(xml_supplier_order_positions)
        for purchase_order_line in self._generate_order_line_element(stock_picking):
            xml_supplier_order_positions.append(purchase_order_line)

        xsd_error = self.xml_tools.validate_xml(
            self._factory_name, xml_root, print_error=self.print_errors)
        if xsd_error:
            write_log(self, self.cr, self.uid, self._table, purchase_order.name, purchase_order.id, 'XSD validation error', correct=False, extra_information=xsd_error)
            raise Warning(xsd_error)
        return xml_root

    def _generate_order_line_element(self, stock_picking):
        ret = []
        i = 1
        id_table = {}
        for ordered_id in sorted([x.id for x in stock_picking.move_lines]):
            id_table[str(ordered_id)] = i
            i += 1
        for move in stock_picking.move_lines:
            xml = self.create_element('Position')

            # If the move line comes from a purchase.order.line that has
            # the yc_posno set, then we re-use it. Otherwise we have to assign
            # a new one to the stock.move.
            if move.purchase_line_id and move.purchase_line_id.yc_posno:
                pos_no = move.purchase_line_id.yc_posno
            else:
                pos_no = id_table[str(move.id)]
                if move.yc_posno and move.yc_posno != pos_no:
                    raise Warning(_("Move line has been used before, "
                                    "and there is a mismatch"), move.name)
            move.write({'yc_posno': pos_no})
            xml.append(self.create_element('PosNo', pos_no))

            xml.append(self.create_element(
                'ArticleNo', move.product_id.default_code))
            xml.append(self.create_element('Quantity', move.product_qty))
            xml.append(self.create_element(
                'QuantityISO', move.product_uom.uom_iso))
            xml.append(self.create_element('PosText', move.product_id.name))
            ret.append(xml)
            xsd_error = self.xml_tools.validate_xml(
                self._factory_name, xml, print_error=self.print_errors)
            if xsd_error:
                write_log(self, self.cr, self.uid, 'stock.picking', stock_picking.name, stock_picking.id, 'XSD validation error', correct=False, extra_information=xsd_error)
        return ret

    def get_base_priority(self):
        return 10

    def get_related_items(self, object_id):
        product_ids = []
        picking = self.pool['stock.picking'].browse(self.cr, self.uid, object_id, context=self.context)
        for line in picking.move_lines:
            product_ids.append(line.product_id.id)
        return {'product.product': product_ids, 'stock.location': None}

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
