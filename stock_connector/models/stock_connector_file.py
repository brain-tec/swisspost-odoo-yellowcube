# -*- coding: utf-8 -*-
##############################################################################
#
#    Copyright (c) 2016 brain-tec AG (http://www.braintec-group.com)
#    All Right Reserved
#
#    See LICENSE file for full licensing details.
##############################################################################
from openerp import models, fields, api


class StockConnectorFile(models.Model):
    _name = 'stock_connector.file'

    @api.model
    def select_state(self):
        return [
            ('error', 'Error'),
            ('ready', 'Ready'),
            ('done', 'Processed'),
            ('cancel', 'Cancelled'),
        ]

    name = fields.Char(required=True)
    type = fields.Char()
    content = fields.Text()
    state = fields.Selection(selection='select_state', required=True,
                             default='ready')
    info = fields.Text()
    child_ids = fields.One2many('stock_connector.file.record', 'parent_id',
                                'Records')
    attachment_ids = fields.\
        One2many('ir.attachment', 'res_id',
                 domain=lambda self: [('res_model', '=', self._name)],
                 auto_join=True, string='Attachments')
    attachment_count = fields.Integer(compute='_get_attachment_count',
                                      store=False)
    backend_id = fields.Many2one('stock_connector.backend', readonly=True,
                                 required=True)

    transmit = fields.Selection([('out', 'To send'),
                                 ('in', 'Received')])

    @api.one
    def _get_attachment_count(self):
        self.attachment_count = len(self.attachment_ids)

    @api.multi
    def open_attachments(self):
        """
        This method is called from the interface when pressing
         the top-right side button.
        """
        self.ensure_one()
        tree_view_id = self.env.ref('base.view_attachment_tree').id
        form_view_id = self.env.ref('base.view_attachment_form').id
        return {
            'name': 'Attachments',
            'type': 'ir.actions.act_window',
            'res_model': 'ir.attachment',
            'views': [[tree_view_id, 'tree'], [form_view_id, 'form']],
            'domain': [('id', 'in', [x.id for x in self.attachment_ids])],
            'context': {
                'default_res_model': self._name,
                'default_res_id': self.id,
            },
        }
