# -*- coding: utf-8 -*-
##############################################################################
#
#    Copyright (c) 2016 brain-tec AG (http://www.braintec-group.com)
#    All Right Reserved
#
#    See LICENSE file for full licensing details.
##############################################################################
from openerp import models, fields


class StockPickingTypeExt(models.Model):
    _inherit = 'stock.picking.type'

    return_type_id = fields.Many2one('stock.picking.return_type',
                                     'Return Type')