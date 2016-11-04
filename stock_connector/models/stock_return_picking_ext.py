# -*- coding: utf-8 -*-
##############################################################################
#
#    Copyright (c) 2016 brain-tec AG (http://www.braintec-group.com)
#    All Right Reserved
#
#    See LICENSE file for full licensing details.
##############################################################################
from openerp import models, api, fields


class StockReturnPickingExt(models.TransientModel):
    _inherit = 'stock.return.picking'

    @api.multi
    def _create_returns(self):
        new_picking, pick_type_id = super(StockReturnPickingExt, self)\
            ._create_returns()
        picking = self.env['stock.picking'].browse(new_picking)
        picking.return_type_id = self.return_type_id
        return new_picking, pick_type_id

    @api.model
    def default_get(self, fields_list):
        ret = super(StockReturnPickingExt, self).default_get(fields_list)
        record_id = self.env.context and self.env.context.get('active_id',
                                                              False) or False
        pick = self.env['stock.picking'].browse(record_id)
        picking_type = pick.picking_type_id
        ret['return_type_id'] = picking_type.return_type_id.id
        return ret

    return_type_id = fields.Many2one('stock.picking.return_type',
                                     'Return Type')
