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
        self.backend_record.output_for_debug += \
            'Creating WBL file for {0}\n'.format(record.name)
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

        header.append(create('SupplierName1', record.partner_id.name))
        header.append(create('SupplierStreet', record.partner_id.street))
        header.append(create('SupplierCountryCode',
                             record.partner_id.country_id.code))
        header.append(create('SupplierZIPCode', record.partner_id.zip))
        header.append(create('SupplierCity', record.partner_id.city))

        order_no = get_binding(record, WBL_WBA_ORDERNO_GROUP,
                               lambda s: str(s.id))
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
                                 lambda s: str(pos_no_idx))
            position.append(create('PosNo', pos_no))
            position.append(create('ArticleNo',
                                   line.product_id.default_code or ''))
            position.append(create('Quantity', line.product_qty))
            position.append(create('QuantityISO',
                                   line.product_uom_id.iso_code))
            position.append(create('PosText', line.product_id.name))

        errors = tools.validate_xml(root)
        if errors:
            self.backend_record.output_for_debug += \
                'WBL file errors:\n{0}\n'.format(errors)
        else:
            related_ids = [
                ('stock_connector.event', picking_event.id),
                (picking_event.res_model, picking_event.res_id),
            ]
            self.yc_save_file(root, related_ids, tools, 'WBL', suffix=order_no,
                              cancel_duplicates=True)
            picking_event.state = 'done'
            record.printed = True
            self.backend_record.output_for_debug += 'WBL file processed\n'

    @classmethod
    def get_supplier_mo(cls, partner, pattern):
        if not pattern:
            return False
        return pattern.format(
            id=partner.id,
            name=partner.name,
        )
