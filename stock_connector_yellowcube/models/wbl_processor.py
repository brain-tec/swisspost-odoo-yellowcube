# -*- coding: utf-8 -*-
##############################################################################
#
#    Copyright (c) 2016 brain-tec AG (http://www.braintec-group.com)
#    All Right Reserved
#
#    See LICENSE file for full licensing details.
##############################################################################
from .xml_tools import XmlTools
from .file_processor import FileProcessor, WBL_WBA_ORDERNO_GROUP


class WblProcessor(FileProcessor):
    """
    This class creates the WBL file for Yellowcube

    Version: 1.4
    """

    def __init__(self, backend):
        super(WblProcessor, self).__init__(backend, 'wbl')

    def yc_create_wbl_file(self, picking_event):
        record = picking_event.get_record()
        picking_event.info = ''
        self.log_message(
            'Creating WBL file for {0}\n'.format(record.name),
            event=picking_event,
            timestamp=True)
        get_binding = self.backend_record.get_binding
        kwargs = {
            '_type': 'wbl',
        }
        tools = XmlTools(**kwargs)
        create = tools.create_element

        root = create('WBL')
        root.append(self.yc_create_control_reference(tools, 'WBL', '2.1'))

        order = create('SupplierOrder')
        root.append(order)

        header = create('SupplierOrderHeader')
        order.append(header)
        header.append(create('DepositorNo',
                             self.yc_get_parameter('depositor_no')))
        header.append(create('Plant',
                             self.yc_get_parameter('plant_id')))
        supplier_order_no = get_binding(
            record.partner_id,
            'yc_SupplierNo',
            lambda p: self.get_supplier_mo(p,
                                           self.yc_get_parameter(
                                               'default_supplier_no')))
        header.append(create('SupplierNo', supplier_order_no))

        self.yc_create_longname_element(tools, header, record.partner_id,
                                        tag='SupplierName%s')
        header.append(create('SupplierStreet', record.partner_id.street))
        header.append(create('SupplierCountryCode',
                             record.partner_id.country_id.code))
        header.append(create('SupplierZIPCode', record.partner_id.zip))
        header.append(create('SupplierCity', record.partner_id.city))

        order_no = get_binding(record, WBL_WBA_ORDERNO_GROUP,
                               lambda s: s.id)
        header.append(create('SupplierOrderNo', order_no))
        if record.date:
            header.append(create('SupplierOrderDate',
                                 record.date.split(' ')[0]
                                 .replace('-', '')))
        if record.min_date:
            header.append(create('SupplierOrderDeliveryDate',
                                 record.min_date.split(' ')[0]
                                 .replace('-', '')))

        order_positions = create('SupplierOrderPositions')
        order.append(order_positions)
        pos_no_idx = 0
        for line in record.pack_operation_product_ids:
            pos_no_idx += 1
            position = create('Position')
            order_positions.append(position)
            pos_no = get_binding(line, 'SupplierOrderNo{0}'.format(order_no),
                                 lambda s: pos_no_idx)
            position.append(create('PosNo', pos_no))
            position.append(create('ArticleNo',
                                   line.product_id.default_code or ''))
            position.append(create('Quantity', line.product_qty))
            position.append(create('QuantityISO',
                                   line.product_uom_id.iso_code))
            position.append(create('PosText', line.product_id.name))

        errors = tools.validate_xml(root)
        if errors:
            self.log_message(
                'WBL file errors:\n{0}\n'.format(errors),
                event=picking_event)
            picking_event.state = 'error'
        else:
            related_ids = [
                ('stock_connector.event', picking_event.id),
                (picking_event.res_model, picking_event.res_id),
            ]
            self.yc_save_file(root, related_ids, tools, 'WBL', suffix=order_no,
                              cancel_duplicates=True)
            picking_event.state = 'done'
            record.printed = True
            self.log_message('WBL file processed\n', event=picking_event)

    @classmethod
    def get_supplier_mo(cls, partner, pattern):
        if not pattern:
            return False
        return pattern.format(
            id=partner.id,
            name=partner.name,
        )

    def yc_create_longname_element(self, tools, node, record, tag='Name%s',
                                   limit=4, name_limit=35):
        name = record.name

        name_parts = [name]
        partner_name_limit = limit - 2
        if len(name) > name_limit:
            node.append(tools.create_comment(name))
            name_parts = self._yc_chop_long_name(tools, name, name_limit,
                                                 partner_name_limit)
        if record.additional_description:
            name_parts.extend(self._yc_chop_long_name(tools, record
                                                      .additional_description))
        if record.street2:
            name_parts.extend(self._yc_chop_long_name(tools, record.street2))

        idx = 1
        for part in name_parts:
            node.append(tools.create_element(tag % idx, part))
            idx += 1
            if idx > limit:
                break
