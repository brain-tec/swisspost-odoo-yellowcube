# -*- coding: utf-8 -*-
##############################################################################
#
#    Copyright (c) 2016 brain-tec AG (http://www.braintec-group.com)
#    All Right Reserved
#
#    See LICENSE file for full licensing details.
##############################################################################
from openerp import models, fields


class StockLocationExt(models.Model):
    _inherit = 'stock.location'

    yc_storage_location = fields.\
        One2many('stock_connector.binding', 'res_id',
                 domain=[('res_model', '=', 'stock.location'),
                         ('group', '=', 'StorageLocation')],
                 string='Storage Location')
