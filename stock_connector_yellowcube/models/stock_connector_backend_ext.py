# -*- coding: utf-8 -*-
##############################################################################
#
#    Copyright (c) 2016 brain-tec AG (http://www.braintec-group.com)
#    All Right Reserved
#
#    See LICENSE file for full licensing details.
##############################################################################
from openerp import models, api, fields

OPERATING_MODE = [
    ('T', 'Test'),
    ('P', 'Production'),
    ('D', 'Development'),
]


class StockConnectorBackendExt(models.Model):
    _inherit = 'stock_connector.backend'

    yc_parameter_create_art_multifile = fields.Boolean(default=True)
    yc_parameter_on_art_set_missing_default_code = fields.Boolean(
        'Set product default_code if missing on ART file creation',
        default=False,
    )
    yc_parameter_sync_products = fields.Boolean(
        'Sync Products (ART)',
        default=True,
    )
    yc_parameter_sync_picking_out = fields.Boolean(
        'Sync Delivery Orders (WAB+WAR)',
        default=True,
    )
    yc_parameter_sync_picking_in = fields.Boolean(
        'Sync Incoming Shipments (WBL+WBA)',
        default=True,
    )
    yc_parameter_sync_inventory_moves = fields.Boolean(
        'Sync Inventory Moves (BUR)',
        default=True,
    )
    yc_parameter_sync_inventory_updates = fields.Boolean(
        'Sync Inventory Updates (BAR)',
        default=True,
    )

    yc_parameter_depositor_no = fields.Char('DepositorNo')
    yc_parameter_partner_no = fields.Char('PartnerNo')
    yc_parameter_plant_id = fields.Char('PlantID')
    yc_parameter_receiver = fields.Char('Receiver')
    yc_parameter_sender = fields.Char('Sender')
    yc_parameter_operating_mode = fields.Selection(OPERATING_MODE,
                                                   'Operating Mode',
                                                   default='T')
    yc_parameter_default_supplier_no = fields.Char(
        'Default SupplierNo',
        help="If set, SupplierNo will be set when missing, using format, "
             "with the next arguments: 'id'. E.g.: 'client_{name}'",
        default='partner{id}'
    )

    yc_article_no_ids = fields.\
        One2many('stock_connector.binding', 'backend_id',
                 domain=[('res_model', '=', 'product.product'),
                         ('group', '=', 'YCArticleNo')],
                 string='YCArticleNo')

    @api.model
    def select_versions(self):
        ret = super(StockConnectorBackendExt, self).select_versions()
        ret.append(('0.1-yellowcube-1.0', 'Yellowcube 1.0'))
        return ret
