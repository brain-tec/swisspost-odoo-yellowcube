# -*- coding: utf-8 -*-
##############################################################################
#
#    Copyright (c) 2016 brain-tec AG (http://www.braintec-group.com)
#    All Right Reserved
#
#    See LICENSE file for full licensing details.
##############################################################################
from openerp import models, fields, api


class StockConnectorBinding(models.Model):
    _name = 'stock_connector.binding'

    backend_id = fields.Many2one('stock_connector.backend',
                                 required=True, readonly=True,
                                 string='Backend')

    res_model = fields.Char(required=True)
    res_id = fields.Integer(required=True)
    group = fields.Char(required=True)

    binding = fields.Char(required=True)

    name = fields.Char(compute='_get_name', store=False)

    @api.one
    @api.depends('res_id', 'res_model')
    @api.onchange('res_id', 'res_model')
    def _get_name(self):
        record = self.record
        if record and hasattr(record, 'name'):
            self.name = record.name
        else:
            self.name = None

    @api.multi
    def __get_record(self):
        if self.ids:
            self.ensure_one()
            return self.env[self.res_model].browse(self.res_id)
        else:
            return None

    record = property(__get_record)

    _sql_constraints = [
        ('binding_uniq', 'unique(backend_id, "group", binding)',
         'Each binding must be unique by backend'),
        ('res_id_uniq', 'unique(backend_id, "group", res_model, res_id)',
         'Each record must be unique by backend'),
    ]
