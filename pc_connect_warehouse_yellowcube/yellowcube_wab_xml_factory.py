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
from openerp.osv import osv, fields
from openerp.tools.translate import _
from xml_abstract_factory import xml_factory_decorator, xml_abstract_factory, get_customer_order_number
from openerp.addons.pc_connect_master.utilities.misc import format_exception
from xsd.xml_tools import validate_xml, export_filename
from xsd.xml_tools import create_element as old_create_element
from datetime import datetime
from lxml.etree import Comment
from openerp.release import version_info
import logging
logger = logging.getLogger(__name__)


def create_element(entity, text=None, attrib=None, ns='https://service.swisspost.ch/apache/yellowcube/YellowCube_WAB_REQUEST_Warenausgangsbestellung.xsd'):
    return old_create_element(entity, text, attrib, ns)


@xml_factory_decorator("wab")
class yellowcube_wab_xml_factory(xml_abstract_factory):
    _table = 'stock.picking'

    def __init__(self, *args, **kargs):
        logger.debug("WAB factory created")

    def import_file(self, file_text):
        logger.debug("Unrequired functionality")
        return True

    def get_main_file_name(self, _object):
        # This solves an issue with un-calculated values
        return _object.get_yc_filename_postfix()

    def check_attach_invoice_in_wab(self, stock_picking):
        ''' Indicates whether to attach the invoice to the received stock picking in the WAB.
            We only attach the invoices if ALL the following conditions are met:
               0) Precondition: The invoice has to be sent to the WAB according to the configuration.
               1) It is the first delivery for a given sale order.
               2) The payment method of the sale order has epayment DE-activated.
               3) The shipping address is the same of the invoice address.
               4) The picking is not a backorder.
        '''
        if stock_picking.type not in ['out', 'outgoing']:
            return False

        # 0) Precondition: The invoice has to be sent to the WAB according to the configuration.
        attach_invoice = (self.get_param('wab_invoice_send_mode') in ['pcl_wab', 'pdf_wab'])

        # 1) It is the first or only delivery for a given sale order.
        attach_invoice &= stock_picking.is_first_delivery()

        # 2) The payment method of the sale order has the epayment DE-activated.
        attach_invoice &= (not stock_picking.payment_method_has_epayment())

        # 3) The shipping address is the same of the invoice address for the sale order (if any).
        attach_invoice &= stock_picking.equal_addresses_ship_invoice()

        # 4) The picking is not a backorder.
        attach_invoice &= (not stock_picking.backorder_id)

        return attach_invoice

    def get_export_files(self, stock_picking):
        """
        @return: dictionary <KEY=output_filename, VALUE=original_path>.
        """
        result = {}
        sale_order = stock_picking.sale_id
        self.context['yc_customer_order_no'] = stock_picking.yellowcube_customer_order_no

        yc_sender = self.get_param('sender', required=True)
        if not yc_sender:
            error_msg = _('Required variable YC Sender (yc_sender) is not defined in the configuration parameters.')
            logger.error(error_msg)
            raise Exception(error_msg)
        yc_sender = yc_sender.replace(' ', '_')
        self.context['yc_sender'] = yc_sender

        # We do not always attach the invoice, but only under certain circumstances.
        attach_invoice = self.check_attach_invoice_in_wab(stock_picking)
        if attach_invoice:
            invoice_file_extension = 'pcl' if (self.get_param('wab_invoice_send_mode') == 'pcl_wab') else 'pdf'
            for invoice in sale_order.invoice_ids:
                result.update(invoice.with_context(self.context).get_attachment_wab(invoice_file_extension))

        # Adds the attachment for the stock.picking.
        result.update(stock_picking.with_context(self.context).get_attachment_wab())
        del self.context['yc_customer_order_no']
        del self.context['yc_sender']
        return result

    def generate_root_element(self, stock_picking):
        # xml = '<?xml version="1.0" encoding="UTF-8"?>\n'
        # xml = '{0}<WAB xsi:noNamespaceSchemaLocation="YellowCube_WAB_Warenausgangsbestellung.xsd" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">\n'.format(xml)
        DELIVERYINSTRUCTIONS_TAG_MAX_LENGTH = 15

        xml_root = create_element('WAB')

        self.context['yc_customer_order_no'] = stock_picking.yellowcube_customer_order_no

        picking_mode = stock_picking.type
        sale_order = stock_picking.sale_id
        xml_root.append(Comment(_('Sale Order #{0}: {1}').format(sale_order.id, sale_order.name)))

        if not sale_order:
            raise Warning(_("There is no sale.order related to this stock.picking (type={0})").format(picking_mode))
        if not self.context.get('yc_ignore_wab_reports', False):
            sale_order.generate_reports()

        # WAB > ControlReference
        now = datetime.now()
        xml_control_reference = create_element('ControlReference')
        xml_control_reference.append(create_element('Type', text='WAB'))
        xml_control_reference.append(create_element('Sender', text=self.get_param('sender', required=True)))
        xml_control_reference.append(create_element('Receiver', text=self.get_param('receiver', required=True)))
        xml_control_reference.append(create_element(
            'Timestamp',
            text='{0:04d}{1:02d}{2:02d}{3:02d}{4:02d}{5:02d}'.format(now.year, now.month, now.day, now.hour, now.hour, now.minute)
        ))
        xml_control_reference.append(create_element('OperatingMode', text=self.get_param('operating_mode', required=True)))
        xml_control_reference.append(create_element('Version', text='1.0'))
        xml_root.append(xml_control_reference)

        # WAB -> Order
        xml_order = create_element('Order')
        xml_root.append(xml_order)
        # WAB -> OrderHeader
        xml_order_header = create_element('OrderHeader')
        xml_order_header.append(create_element('DepositorNo', self.get_param('depositor_no', required=True)))
        xml_order_header.append(create_element('CustomerOrderNo', text=stock_picking.get_customer_order_no()[stock_picking.id]))
        dateorder = sale_order.date_order.split(' ')[0]
        xml_order_header.append(create_element('CustomerOrderDate', text=dateorder.replace('-', '')))
        xml_order.append(xml_order_header)

        # WAB -> PartnerAddress
        xml_partner_address = create_element('PartnerAddress')
        xml_partner_address.append(self._generate_partner_address_element(sale_order.partner_shipping_id, self.get_param('wab_partner_type_for_shipping_address')))
        if self.get_param('wab_add_invoicing_address'):
            xml_partner_address.append(self._generate_partner_address_element(sale_order.partner_invoice_id, self.get_param('wab_partner_type_for_invoicing_address')))
        xml_order.append(xml_partner_address)

        # WAB -> ValueAddedServices
        xml_value_added_services = create_element('ValueAddedServices')
        xml_additional_service = create_element('AdditionalService')

        if picking_mode in ['out', 'outgoing']:
            # <BasicShippingServices> under ValueAddedServices/AdditionalService
            if stock_picking.carrier_id and stock_picking.carrier_id.yc_basic_shipping:
                xml_additional_service.append(create_element('BasicShippingServices', text=stock_picking.carrier_id.yc_basic_shipping))
            else:
                raise Warning(_('Missing Basic shipping in delivery method'), sale_order.name)
        else:
            xml_additional_service.append(create_element('BasicShippingServices', text="RETOURE"))

        # <AdditionalShippingServices> under ValueAddedServices/AdditionalService
        if stock_picking.carrier_id and stock_picking.carrier_id.yc_additional_shipping:
            xml_additional_service.append(create_element('AdditionalShippingServices', text=stock_picking.carrier_id.yc_additional_shipping))

        # <DeliveryInstructions> under ValueAddedServices/AdditionalService
        if stock_picking.carrier_id and stock_picking.carrier_id.pc_delivery_instructions:
            xml_additional_service.append(create_element('DeliveryInstructions', text=stock_picking.carrier_id.pc_delivery_instructions[:DELIVERYINSTRUCTIONS_TAG_MAX_LENGTH]))

        # <FrightShippingFlag> under ValueAddedServices/AdditionalService
        xml_additional_service.append(create_element('FrightShippingFlag', text=('1' if stock_picking.carrier_id.pc_freight_shipping else '0')))

        # <ShippingInterface> under ValueAddedServices/AdditionalService
        if stock_picking.carrier_id and stock_picking.carrier_id.pc_shipping_interface:
            xml_additional_service.append(create_element('ShippingInterface', text=stock_picking.carrier_id.pc_shipping_interface))

        xml_value_added_services.append(xml_additional_service)
        xml_order.append(xml_value_added_services)

        # WAB -> OrderPositions
        xml_order_positions = create_element('OrderPositions')
        for position in self._generate_order_position_element(stock_picking):
            xml_order_positions.append(position)
        xml_order.append(xml_order_positions)

        # WAB -> OrderDocuments
        xml_order_documents = create_element('OrderDocuments', attrib={'OrderDocumentsFlag': '1'})
        xml_order_doc_filenames = create_element('OrderDocFilenames')
        for filename in self.get_export_files(stock_picking):
            xml_order_doc_filenames.append(create_element('OrderDocFilename', text=filename))
        xml_order_documents.append(xml_order_doc_filenames)
        xml_order.append(xml_order_documents)

        xsd_error = validate_xml("wab", xml_root, print_error=self.print_errors)
        if xsd_error:
            raise Warning(xsd_error)
        if 'yc_customer_order_no' in self.context:
            del self.context['yc_customer_order_no']
        return xml_root

    def _generate_partner_address_element(self, partner, partner_type):
        ''' Creates and returns a <Partner> tag for the WAB.
        '''
        # Having this local, makes possible to pass languages to getTextAlias
        context = self.context.copy()
        if partner.lang:
            context['lang'] = partner.lang

        MAX_NUMBER_OF_NAME_TAGS = 4

        xml = create_element("Partner")
        xml.append(create_element('PartnerType', text=partner_type))

        partner_no = self.get_param('partner_no', required=True)
        xml.append(create_element('PartnerNo', text=partner_no))
        if partner.is_company:
            partner_ref = partner.ref
        else:
            partner_ref = partner.parent_id.ref
        xml.append(create_element('PartnerReference', text=partner_ref))

        if partner.title:
            xml.append(create_element('Title', partner.title.name))

        names = self.__generate_partner_name(partner)
        for idx in xrange(len(names)):
            if idx >= MAX_NUMBER_OF_NAME_TAGS:
                break
            # This will generate elements Name1 ... Name4
            xml.append(create_element('Name{0}'.format(idx + 1), text=names[idx]))

        street = False
        if partner.street:
            street = ' '.join([partner.street, partner.street_no or '']).strip(' ')
        elif partner.po_box:
            street = ' '.join([_('P.O. Box'), partner.po_box])
        if street:
            xml.append(create_element('Street', text=street))
        xml.append(create_element('CountryCode', text=partner.country_id.code))
        xml.append(create_element('ZIPCode', text=partner.zip))
        xml.append(create_element('City', text=partner.city))
        if partner.phone:
            xml.append(create_element('PhoneNo', text=partner.phone))
        if partner.mobile:
            xml.append(create_element('MobileNo', text=partner.mobile))
        if partner.email:
            xml.append(create_element('Email', text=partner.email))
        if not partner.lang:
            raise Warning(_("Missing partner #{0} language code").format(partner.id))
            # Language code is required
        xml.append(create_element('LanguageCode', text=partner.lang[:2]))
        xsd_error = validate_xml("wab", xml, print_error=self.print_errors)
        if xsd_error:
            logger.error('XSD validation error: {0}'.format(xsd_error))
        return xml

    def _generate_order_position_element(self, stock_picking):
        PICKINGMESSAGE_TAG_MAX_LENGTH = 132
        SHORTDESCRIPTION_TAG_MAX_LENGTH = 40

        ret = []
        i = 1
        id_table = {}
        for ordered_id in sorted([x.id for x in stock_picking.move_lines]):
            id_table[str(ordered_id)] = i
            i += 1
        for move in stock_picking.move_lines:
            if self.get_param('enable_product_lifecycle') and (move.product_id.product_state not in ['in_production']):
                raise Warning(_('Product {0} is not ready on the lifecycle. State: {1}').format(move.product_id.default_code, move.product_id.product_state))
            xml = create_element('Position')
            xml.append(create_element('PosNo', text=id_table[str(move.id)]))
            xml.append(create_element('ArticleNo', text=move.product_id.default_code))
            value = getattr(move, 'restrict_lot_id' if version_info[0] > 7 else 'prodlot_id', None)
            if value:
                xml.append(create_element('Lot', text=value.name))
            xml.append(create_element('Plant', text=self.get_param('plant_id', required=True)))
            xml.append(create_element('Quantity', text=move.product_qty))
            if not move.product_uom.uom_iso:
                raise Warning(_("Undefined ISO code for UOM '{0}', in product {1}").format(move.product_uom.name, move.product_id.default_code))
            xml.append(create_element('QuantityISO', text=move.product_uom.uom_iso))

            # Conditionally fills the tag <ShortDescription>, depending on if it's used as it has to be used
            # (encoding the product's name),  or if it's used to encode another information...
            short_description_usage = self.get_param('wab_shortdescription_mapping')
            if short_description_usage == 'name':
                short_description_value = move.product_id.name[:SHORTDESCRIPTION_TAG_MAX_LENGTH]
            else:  # if short_description_usage == 'price':
                short_description_value = "%0.2f" % move.product_id.list_price
            xml.append(create_element('ShortDescription', text=short_description_value))

            # Conditionally fills the tag <PickingMessage>, depending on if it's not used or if it's used
            # to encode  the reference of the carrier of the picking... This is supposed to be a temporary
            # solution until the new XSD is crafted.
            picking_message_usage = self.get_param('wab_pickingmessage_mapping')
            if picking_message_usage == 'carrier_tracking_ref':
                carrier_tracking_ref = stock_picking.carrier_tracking_ref
                if carrier_tracking_ref:
                    xml.append(create_element('PickingMessage', text=carrier_tracking_ref[:PICKINGMESSAGE_TAG_MAX_LENGTH]))

            if stock_picking.yellowcube_return_reason:
                xml.append(create_element('ReturnReason', text=stock_picking.yellowcube_return_reason))
            ret.append(xml)
            xsd_error = validate_xml("wab", xml, print_error=self.print_errors)
            if xsd_error:
                logger.error('XSD validation error: {0}'.format(xsd_error))
        return ret

    def __generate_partner_name(self, partner):
        '''
        Generates the content for tag 'Name1..Name4'.

        Returns a list of contents, up to 4-elements length.
        '''
        FIELDS_LENGHT_LIMIT = 35
        PARTNERNAME_SPAN_LINES = 2
        MAX_NUMBER_OF_NAME_TAGS = 4

        ret = []

        # First line (Name1).
        if partner.is_company:
            name1 = partner.name  # By default, unless the partner is not a company.
        else:
            name1 = partner.lastname
            if partner.firstname:
                name1 = ('%s %s' % (partner.firstname, partner.lastname)).strip()
        if len(name1) <= FIELDS_LENGHT_LIMIT:
            ret.append(name1)
        elif ' ' in name1 or '-' in name1:
            # If longer, we try to break it into multiple words and lines
            name1s = name1.strip().split(' ')
            idx = 0
            nameline = 1
            finished = False
            while not finished and nameline <= PARTNERNAME_SPAN_LINES:
                new_name1 = ''
                while len(new_name1) + len(name1s[idx]) < FIELDS_LENGHT_LIMIT:
                    # First we get full-words
                    new_name1 = ' '.join([new_name1, name1s[idx]]).strip()
                    idx += 1
                    if idx >= len(name1s):
                        finished = True
                        break
                if not finished:
                    # Second, we try to fill with hyphened words
                    rest_chars = FIELDS_LENGHT_LIMIT - len(new_name1) - 1
                    pos_hyphen = name1s[idx].rfind('-', 0, rest_chars)
                    if pos_hyphen > 0:
                        new_name1 = ' '.join([new_name1, name1s[idx][:pos_hyphen]])
                        # We keep the hyphen in a new-line if required
                        name1s[idx] = name1s[idx][pos_hyphen:]
                ret.append(new_name1.strip())
                nameline += 1
        else:
            ret.append(name1[:FIELDS_LENGHT_LIMIT])

        # Second line (optional).
        if (not partner.is_company) and partner.company:
            # If it's a company we already put its name as partner.name,
            # so there is no need to write it again.
            ret.append(partner.company[:FIELDS_LENGHT_LIMIT])

        # Third line (optional).
        if partner.street2:
            ret.append(partner.street2[:FIELDS_LENGHT_LIMIT])

        # Fourth line (optional).
        if partner.po_box and partner.street:
            ret.append(' '.join([_('P.O. Box'), str(partner.po_box)])[:FIELDS_LENGHT_LIMIT])

        if len(ret) > MAX_NUMBER_OF_NAME_TAGS:
            if len(name1) > FIELDS_LENGHT_LIMIT:
                ret = ret[0:1] + ret[2:5]

        return ret

    def mark_as_exported(self, _id):
        self.pool.get('stock.picking').write(self.cr, self.uid, _id, {'yellowcube_exported_wab': True}, context=self.context)

    def get_base_priority(self):
        return 10

    def get_related_items(self, object_id):
        product_ids = []
        picking = self.pool['stock.picking'].browse(self.cr, self.uid, object_id, context=self.context)
        for line in picking.move_lines:
            if line.product_id.type in ['consu', 'product']:
                product_ids.append(line.product_id.id)
        return {'product.product': product_ids, 'stock.location': None}

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
