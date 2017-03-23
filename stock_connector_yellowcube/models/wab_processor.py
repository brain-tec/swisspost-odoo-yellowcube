# -*- coding: utf-8 -*-
##############################################################################
#
#    Copyright (c) 2016 brain-tec AG (http://www.braintec-group.com)
#    All Right Reserved
#
#    See LICENSE file for full licensing details.
##############################################################################
from .xml_tools import XmlTools
from .file_processor import FileProcessor, WAB_WAR_ORDERNO_GROUP

XML_NAME_LENGTH_LIMIT = 35


class WabProcessor(FileProcessor):
    """
    This class creates the WAB file for Yellowcube

    Version: 1.4
    """

    def __init__(self, backend):
        super(WabProcessor, self).__init__(backend, 'wab')

    def yc_create_wab_file(self, picking_event):
        record = picking_event.get_record()
        is_return = False
        if record.return_type_id:
            is_return = True
        elif record.picking_type_id.default_location_dest_id:
            if record.picking_type_id.default_location_dest_id\
                    .return_location:
                is_return = True
        picking_event.info = ''
        self.log_message(
            'Creating WAB file for {0}\n'.format(record.name),
            event=picking_event,
            timestamp=True)
        get_binding = self.backend_record.get_binding
        kwargs = {
            '_type': 'wab',
        }
        tools = XmlTools(**kwargs)
        create = tools.create_element
        errors = []

        root = create('WAB')
        root.append(self.yc_create_control_reference(tools, 'WAB', '1.4'))

        order = create('Order')
        root.append(order)

        header = create('OrderHeader')
        order.append(header)
        header.append(create('DepositorNo',
                             self.yc_get_parameter('depositor_no')))
        order_no = get_binding(record, WAB_WAR_ORDERNO_GROUP,
                               lambda s: s.id)
        header.append(create('CustomerOrderNo', order_no))
        header.append(create('CustomerOrderDate',
                             record.min_date.split(' ')[0].replace('-', '')))

        partner_address = create('PartnerAddress')
        order.append(partner_address)
        partner = create('Partner')
        partner_address.append(partner)
        partner.append(create('PartnerType', 'WE'))
        partner.append(create('PartnerNo',
                              self.yc_get_parameter('partner_no')))
        partner_ref = get_binding(record.partner_id, 'PartnerReference',
                                  lambda s: s.ref or s.id)
        partner.append(create('PartnerReference', partner_ref))
        if record.partner_id.title:
            partner.append(create('Title', record.partner_id.title.name))
        self.yc_create_longname_element(tools, partner, record.partner_id)
        partner.append(create('Street', record.partner_id.street))
        partner.append(create('CountryCode',
                              record.partner_id.country_id.code))
        partner.append(create('ZIPCode', record.partner_id.zip))
        partner.append(create('City', record.partner_id.city))
        if record.partner_id.phone:
            partner.append(create('PhoneNo', record.partner_id.phone))
        if record.partner_id.mobile:
            partner.append(create('MobileNo', record.partner_id.mobile))
        if record.partner_id.fax:
            partner.append(create('FaxNo', record.partner_id.fax))
        if record.partner_id.email:
            partner.append(create('Email', record.partner_id.email))
        partner.append(create('LanguageCode',
                              (record.partner_id.lang or 'de')[:2]))

        value_added_services = create('ValueAddedServices')
        order.append(value_added_services)
        additional_service = create('AdditionalService')
        value_added_services.append(additional_service)
        if is_return:
            shipping_service_code = 'RETURN'
        else:
            shipping_service_code = get_binding(record.carrier_id,
                                                'BasicShippingServices')
        if not shipping_service_code:
            errors.append("Carrier #%s is missing BasicShippingServices"
                          % record.carrier_id.id)
        additional_service.append(create('BasicShippingServices',
                                         shipping_service_code))

        order_positions = create('OrderPositions')
        order.append(order_positions)
        pos_no_idx = 0
        for line in record.pack_operation_product_ids:
            pos_no_idx += 1
            position = create('Position')
            order_positions.append(position)
            pos_no = get_binding(line,
                                 'CustomerOrderNo{0}'.format(order_no),
                                 lambda s: pos_no_idx)
            position.append(create('PosNo', pos_no))
            position.append(create('ArticleNo',
                                   line.product_id.default_code or ''))
            position.append(create('Plant',
                                   self.yc_get_parameter('plant_id')))
            position.append(create('Quantity', line.product_qty))
            position.append(create('QuantityISO',
                                   line.product_uom_id.iso_code))
            if record.return_type_id:
                position.append(create('ReturnReason',
                                       record.return_type_id.yc_code))

        xml_errors = tools.validate_xml(root)
        if xml_errors:
            errors.append(str(xml_errors))
        if errors:
            self.log_message(
                'WAB file errors:\n{0}\n'.format('\n'.join(errors)),
                event=picking_event)
            picking_event.state = 'error'
        else:
            related_ids = [
                ('stock_connector.event', picking_event.id),
                (picking_event.res_model, picking_event.res_id),
            ]
            file_record = self.yc_save_file(
                root, related_ids, tools, 'WAB', suffix=order_no,
                cancel_duplicates=True
            )
            picking_event.state = 'done'
            record.printed = True
            self.log_message(
                'WAB file processed. %s (#%s)\n' % (
                    file_record.name, file_record.id),
                event=picking_event)
