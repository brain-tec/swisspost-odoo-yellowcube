# -*- coding: utf-8 -*-
##############################################################################
#
#    Copyright (c) 2016 brain-tec AG (http://www.braintec-group.com)
#    All Right Reserved
#
#    See LICENSE file for full licensing details.
##############################################################################
from openerp import models, fields, api


class StockConnectorBindingExt(models.Model):
    _inherit = 'stock_connector.binding'

    product_product_id = fields.Many2one('product.product',
                                         string='Product',
                                         compute='get_res_id',
                                         inverse='set_res_id')

    stock_location_id = fields.Many2one('stock.location',
                                        string='Location',
                                        compute='get_res_id',
                                        inverse='set_res_id')

    delivery_carrier_id = fields.Many2one('delivery.carrier',
                                          string='Shipping method',
                                          compute='get_res_id',
                                          inverse='set_res_id')

    @api.one
    @api.depends('res_id')
    def get_res_id(self):
        for field in self.set_res_id._depends:
            setattr(self, field, self.res_id)

    @api.one
    @api.depends('product_product_id',
                 'stock_location_id',
                 'delivery_carrier_id')
    def set_res_id(self):
        for field in self.set_res_id._depends:
            if self.res_id != getattr(self, field):
                self.res_id = getattr(self, field)
