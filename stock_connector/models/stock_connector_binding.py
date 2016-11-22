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
                                 required=True, readonly=False,
                                 string='Backend')

    res_model = fields.Char(required=True)
    res_id = fields.Integer(required=True)
    group = fields.Char(required=True)

    binding = fields.Char(required=True)

    name = fields.Char(compute='_get_name', store=False)
    xml_id = fields.Char(compute='_get_xml_id', inverse='_set_xml_id',
                         store=False)

    @api.one
    @api.depends('res_id', 'res_model')
    @api.onchange('res_id', 'res_model')
    def _get_name(self):
        record = self.record
        if record and hasattr(record, 'name'):
            self.name = record.name
        else:
            self.name = None

    @api.one
    @api.depends('res_id', 'res_model')
    @api.onchange('res_id', 'res_model')
    def _get_xml_id(self):
        if self.res_model and self.res_id:
            xml_id = self.env['ir.model.data'].search(
                [
                    ('model', '=', self.res_model),
                    ('res_id', '=', self.res_id),
                ], limit=1)
            self.xml_id = xml_id.complete_name if len(xml_id) == 1 else None
        else:
            self.xml_id = None

    @api.one
    def _set_xml_id(self):
        if self.xml_id:
            _, self.res_model, self.res_id = self.env['ir.model.data']\
                .xmlid_lookup(self.xml_id)

    @api.model
    def create(self, vals):
        if vals.get('xml_id', False):
            _, vals['res_model'], vals['res_id'] = self.env['ir.model.data']\
                .xmlid_lookup(vals['xml_id'])
        return super(StockConnectorBinding, self).create(vals)

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

    _order = 'backend_id, group, binding ASC'
