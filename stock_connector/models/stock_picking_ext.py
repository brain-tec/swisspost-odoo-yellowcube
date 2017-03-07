# -*- coding: utf-8 -*-
##############################################################################
#
#    Copyright (c) 2016 brain-tec AG (http://www.braintec-group.com)
#    All Right Reserved
#
#    See LICENSE file for full licensing details.
##############################################################################
from openerp import models, fields, api


class StockPickingExt(models.Model):
    _inherit = 'stock.picking'

    related_event_ids = fields.One2many(
        'stock_connector.event', 'res_id', 'Backend Events',
        domain=[('res_model', '=', 'stock.picking')], readonly=True
    )
    related_file_ids = fields.One2many(
        'stock_connector.file', None,
        'Backend Files', readonly=True,
        compute='_get_related_file_ids'
    )

    return_type_id = fields.Many2one('stock.picking.return_type',
                                     'Return Type')

    do_not_sync_with_connector = fields.Boolean()

    @api.model
    def create(self, vals):
        if (
            'picking_type_id' in vals and
            not vals.get('do_not_sync_with_connector', False)
        ):
            picking_type = self.env['stock.picking.type'].browse(
                vals['picking_type_id']
            )
            vals['do_not_sync_with_connector'] \
                = picking_type.do_not_sync_with_connector
        return super(StockPickingExt, self).create(vals)

    @api.one
    def _get_related_file_ids(self):
        relation_records = self.env['stock_connector.file.record'].search([
            ('res_model', '=', 'stock.picking'),
            ('res_id', '=', self.id)
        ])
        self.related_file_ids = relation_records.mapped('parent_id')
