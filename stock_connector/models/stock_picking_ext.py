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
