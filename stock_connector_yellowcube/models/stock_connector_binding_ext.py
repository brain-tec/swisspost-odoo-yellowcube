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
                                         inverse='set_res_id_by_product')

    stock_location_id = fields.Many2one('stock.location',
                                        string='Location',
                                        compute='get_res_id',
                                        inverse='set_res_id_by_location')

    delivery_carrier_id = fields.Many2one('delivery.carrier',
                                          string='Shipping method',
                                          compute='get_res_id',
                                          inverse='set_res_id_by_carrier')

    stock_picking_type_id = fields.Many2one('stock.picking.type',
                                            string='Picking Type',
                                            compute='get_res_id',
                                            inverse='set_res_id_by_picktype')

    @api.one
    @api.depends('res_id')
    def get_res_id(self):
        for field in [
            'product_product_id',
            'stock_location_id',
            'delivery_carrier_id',
            'stock_picking_type_id',
        ]:
            setattr(self, field, self.res_id)

    @api.one
    @api.depends('product_product_id')
    def set_res_id_by_product(self):
        self.res_id = self.product_product_id.id

    @api.one
    @api.depends('stock_location_id')
    def set_res_id_by_location(self):
        self.res_id = self.stock_location_id.id

    @api.one
    @api.depends('delivery_carrier_id')
    def set_res_id_by_carrier(self):
        self.res_id = self.delivery_carrier_id.id

    @api.one
    @api.depends('stock_picking_type_id')
    def set_res_id_by_picktype(self):
        self.res_id = self.stock_picking_type_id.id
