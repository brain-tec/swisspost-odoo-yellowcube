# -*- coding: utf-8 -*-
##############################################################################
#
#    Copyright (c) 2016 brain-tec AG (http://www.braintec-group.com)
#    All Right Reserved
#
#    See LICENSE file for full licensing details.
##############################################################################
from openerp import models, fields, api, exceptions
from openerp.addons.connector.event import on_record_write
import logging
logger = logging.getLogger(__name__)


@on_record_write(model_names=['stock.move', 'stock.picking'])
def register_picking_change(session, model_name, record_id, vals=None):
    if vals is not None and 'state' not in vals:
        return True
    record = session.env[model_name].browse(record_id)
    if model_name == 'stock.move':
        return register_picking_change(session,
                                       'stock.picking',
                                       record.picking_id.id,
                                       vals)
    elif model_name == 'stock.picking':
        key = '{0}_state_{1}'.format(model_name, record.state)
        event_obj = session.env['stock_connector.event']
        domain = [
            ('code', '=', key),
            ('res_model', '=', model_name),
            ('res_id', '=', record_id),
            ('state', 'not in', ['done', 'cancel']),
        ]
        new_event = event_obj.search(domain, limit=1)
        if len(new_event) == 0:
            values = {
                'res_model': model_name,
                'res_id': record_id,
                'code': key,
                'context': str(session.context)
            }
            new_event = event_obj.create(values)
        for backend in session.env['stock_connector.backend'].search([]):
            # A change may not create a new event,
            # but it can be important to the backend
            backend.notify_new_event(new_event)


def CheckEvents():
    """
    Tests on OCA connector reset the registered events
    :return:
    """
    on_record_write.subscribe(register_picking_change,
                              model_names=['stock.move', 'stock.picking'],
                              replacing=register_picking_change)


class StockConnectorEvent(models.Model):
    _name = 'stock_connector.event'

    @api.model
    def select_state(self):
        return [
            ('error', 'Error'),
            ('ready', 'Ready'),
            ('done', 'Processed'),
            ('cancel', 'Cancelled'),
        ]

    @api.one
    def _get_name(self):
        record = self.get_record().name_get()
        if record:
            self.name = record[0][1]
        else:
            self.name = False

    name = fields.Char(compute='_get_name', store=False)
    res_model = fields.Char('Model', required=True, index=True)
    res_id = fields.Integer('Resource ID', required=True, index=True)
    code = fields.Char()
    context = fields.Text(required=False)
    state = fields.Selection(selection='select_state',
                             required=True, default='ready')
    info = fields.Text()

    def get_record(self):
        return self.env[self.res_model].browse(self.res_id)

    @api.multi
    def process_event(self):
        self.ensure_one()
        if 'backend_id' not in self.env.context:
            raise exceptions\
                .UserError('Missing Backend. Open through backend form view.')
        logger.info('Processing event %s' % self.id)
        return self.env['stock_connector.backend']\
            .browse(self.env.context['backend_id']).process_event(self) or True
