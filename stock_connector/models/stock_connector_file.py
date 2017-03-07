# -*- coding: utf-8 -*-
##############################################################################
#
#    Copyright (c) 2016 brain-tec AG (http://www.braintec-group.com)
#    All Right Reserved
#
#    See LICENSE file for full licensing details.
##############################################################################
from openerp import models, fields, api, exceptions
import logging
logger = logging.getLogger(__name__)


class StockConnectorFile(models.Model):
    _name = 'stock_connector.file'
    _description = 'Warehouse File'

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
                                 required=False)

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

    @api.multi
    def process_file(self):
        self.ensure_one()

        backend_id = self.env.context.get('backend_id', False)
        backend_env = self.env['stock_connector.backend']
        auto_backend = self.env.context.get('auto_backend', False)
        if not backend_id:
            backends = backend_env.search([])
            if len(backends) == 1:
                backend_id = backends.id
        if not backend_id:
            if auto_backend:
                last = False
                for backend_id in backend_env.search([]).ids:
                    last = self.with_context(
                        backend_id=backend_id,
                    ).process_file()
                return last
            else:
                raise exceptions.UserError(
                    'Unknown Backend. Open through backend form view.')

        logger.info('Processing file %s' % self.id)
        return backend_env.browse(backend_id).process_file(self) or True
