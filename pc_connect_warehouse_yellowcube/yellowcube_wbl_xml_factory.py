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
from lxml import etree
from xml_abstract_factory import xml_factory_decorator, xml_abstract_factory
from openerp.addons.pc_connect_master.utilities.misc import format_exception
from xsd.xml_tools import validate_xml, export_filename
from xsd.xml_tools import create_element as old_create_element
from datetime import datetime
import logging
logger = logging.getLogger(__name__)


def create_element(entity, text=None, attrib=None, ns='https://service.swisspost.ch/apache/yellowcube/YellowCube_WBL_REQUEST_SupplierOrders.xsd'):
    return old_create_element(entity, text, attrib, ns)


@xml_factory_decorator("wbl")
class yellowcube_wbl_xml_factory(xml_abstract_factory):
    _table = "stock.picking"

    def __init__(self, *args, **kargs):
        logger.debug("WBL factory created")

    def import_file(self, file_text):
        logger.debug("Unrequired functionality")
        return True

    def get_main_file_name(self, _object):
        # Since the functional only computes when the view is loaded, we have to directly call the function which computes the name.
        name = _object.get_yc_filename_postfix()
        return name

    def get_export_files(self, sale_order):
        return {}

    def generate_root_element(self, stock_picking):

        # xml = '<?xml version="1.0" encoding="UTF-8"?>\n'
        # xml = '{0}<WAB xsi:noNamespaceSchemaLocation="YellowCube_WAB_Warenausgangsbestellung.xsd" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">\n'.format(xml)
        xml_root = create_element('WBL')
        purchase_order = stock_picking.purchase_id

        # WAB > ControlReference
        now = datetime.now()
        xml_control_reference = create_element('ControlReference')
        xml_control_reference.append(create_element('Type', text='WBL'))
        xml_control_reference.append(create_element('Sender', text=self.get_param('sender', required=True)))
        xml_control_reference.append(create_element('Receiver', text=self.get_param('receiver', required=True)))
        xml_control_reference.append(create_element(
            'Timestamp',
            text='{0:04d}{1:02d}{2:02d}{3:02d}{4:02d}{5:02d}'.format(now.year, now.month, now.day, now.hour, now.hour, now.minute)
        ))
        xml_control_reference.append(create_element('OperatingMode', text=self.get_param('operating_mode', required=True)))
        xml_control_reference.append(create_element('Version', text='1.0'))
        xml_root.append(xml_control_reference)

        xml_supplier_order = create_element("SupplierOrder")
        xml_root.append(xml_supplier_order)

        xml_supplier_order_header = create_element('SupplierOrderHeader')
        xml_supplier_order.append(xml_supplier_order_header)
        xml_supplier_order_header.append(create_element('DepositorNo', self.get_param('depositor_no', required=True)))
        xml_supplier_order_header.append(create_element('Plant', self.get_param('plant_id', required=True)))

        # Regarding the 'YC SupplierNo', we first check if the supplier has a supplier number,
        # and if that's the case we use it. Otherwise, we use the default supplier number
        # set for the connector.
        if stock_picking.partner_id.supplier and stock_picking.partner_id.yc_supplier_no:
            yc_supplier_no = stock_picking.partner_id.yc_supplier_no
        else:
            yc_supplier_no = self.get_param('supplier_no', required=True)
        xml_supplier_order_header.append(create_element('SupplierNo', yc_supplier_no))

#         xml_supplier_order_header.append(create_element('SupplierOrderNo', stock_picking.yellowcube_customer_order_no))
        xml_supplier_order_header.append(etree.Comment(text='res.partner#{0}'.format(stock_picking.partner_id.id)))
        xml_supplier_order_header.append(create_element('SupplierName1', stock_picking.partner_id.name))
        xml_supplier_order_header.append(create_element('SupplierStreet', '{0} {1}'.format(stock_picking.partner_id.street, stock_picking.partner_id.street_no)))
        xml_supplier_order_header.append(create_element('SupplierCountryCode', text=stock_picking.partner_id.country_id.code))
        xml_supplier_order_header.append(create_element('SupplierZIPCode', text=stock_picking.partner_id.zip))
        xml_supplier_order_header.append(create_element('SupplierCity', text=stock_picking.partner_id.city))
        xml_supplier_order_header.append(create_element('SupplierOrderNo', stock_picking.get_customer_order_no()[stock_picking.id]))
        # CustomerOrderNo is only required for cross-docking
        # xml_supplier_order_header.append(create_element('CustomerOrderNo', stock_picking.get_customer_order_no()[stock_picking.id]))
        if stock_picking.date:
            dateorder = stock_picking.date.split(' ')[0]
            xml_supplier_order_header.append(create_element('SupplierOrderDate', dateorder.replace('-', '')))
        if stock_picking.min_date:
            dateorder = stock_picking.min_date.split(' ')[0]
            xml_supplier_order_header.append(create_element('SupplierOrderDeliveryDate', dateorder.replace('-', '')))

        xml_supplier_order_positions = create_element('SupplierOrderPositions')
        xml_supplier_order.append(xml_supplier_order_positions)
        for purchase_order_line in self._generate_order_line_element(stock_picking):
            xml_supplier_order_positions.append(purchase_order_line)

        xsd_error = validate_xml(self._factory_name, xml_root, print_error=self.print_errors)
        if xsd_error:
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
            xml = create_element('Position')
            pos_no = id_table[str(move.id)]
            if move.yc_posno and move.yc_posno != pos_no:
                raise Warning(_("Move line has been used before, and there is a mismatch"), move.name)
            move.write({'yc_posno': pos_no})
            xml.append(create_element('PosNo', pos_no))
            xml.append(create_element('ArticleNo', move.product_id.default_code))
            xml.append(create_element('Quantity', move.product_qty))
            xml.append(create_element('QuantityISO', move.product_uom.uom_iso))
            xml.append(create_element('PosText', move.product_id.name))
            ret.append(xml)
            xsd_error = validate_xml(self._factory_name, xml, print_error=self.print_errors)
            if xsd_error:
                logger.error('XSD validation error: {0}'.format(xsd_error))
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
