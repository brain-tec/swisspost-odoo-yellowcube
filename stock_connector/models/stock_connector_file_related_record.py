# -*- coding: utf-8 -*-
##############################################################################
#
#    Copyright (c) 2016 brain-tec AG (http://www.braintec-group.com)
#    All Right Reserved
#
#    See LICENSE file for full licensing details.
##############################################################################
from openerp import models, fields, api


class StockConnecrFileRelatedRecord(models.Model):
    _name = 'stock_connector.file.record'

    @api.onchange('res_model', 'res_id')
    @api.one
    def _get_name(self):
        record = self.get_record()
        self.name = record.name_get()[0][1] if record else 'UNAVAILABLE RECORD'

    name = fields.Char(compute='_get_name', store=False)
    parent_id = fields.Many2one('stock_connector.file', 'Parent')
    res_model = fields.Char('Model', required=True)
    res_id = fields.Integer('Resource ID', required=True)

    def get_record(self):
        if self.res_id and self.res_model and self.res_model in self.env:
            return self.env[self.res_model].browse(self.res_id)
        else:
            return None

    @api.multi
    def open_record(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'res_id': self.res_id,
            'res_model': self.res_model,
            'target': 'current',
            'view_mode': 'form',
        }
