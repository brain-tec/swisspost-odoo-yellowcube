# -*- coding: utf-8 -*-
##############################################################################
#
#    Copyright (c) 2016 brain-tec AG (http://www.braintec-group.com)
#    All Right Reserved
#
#    See LICENSE file for full licensing details.
##############################################################################
from openerp.addons.connector.event import on_record_write
from openerp.addons.stock_connector.models.stock_connector_event\
    import register_picking_change, CheckEvents as OldCheckEvents


@on_record_write(model_names=['sale.order'])
def register_sale_order_change(session, model_name, record_id, vals):
    if 'state' not in vals:
        return True
    sale = session.env['sale.order'].browse(record_id)
    pickings = session.env['stock.picking'].search([
        '|',
        ('sale_id', '=', record_id),
        ('group_id', '=', sale.procurement_group_id.id),
    ])
    for picking in pickings:
        # This triggers an event update on every picking
        register_picking_change(session, 'stock.picking', picking.id)


def CheckEvents():
    """
    Tests on OCA connector reset the registered events
    :return:
    """
    OldCheckEvents()
    on_record_write.subscribe(register_sale_order_change,
                              model_names=['sale.order'],
                              replacing=register_sale_order_change)
