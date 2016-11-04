# -*- coding: utf-8 -*-
##############################################################################
#
#    Copyright (c) 2016 brain-tec AG (http://www.braintec-group.com)
#    All Right Reserved
#
#    See LICENSE file for full licensing details.
##############################################################################
from openerp import models, fields


class StockPickingReturnType(models.Model):
    _name = 'stock.picking.return_type'
    _rec_name = 'name'

    name = fields.Char()
