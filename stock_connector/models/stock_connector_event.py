# -*- coding: utf-8 -*-
##############################################################################
#
#    Copyright (c) 2016 brain-tec AG (http://www.braintec-group.com)
#    All Right Reserved
#
#    See LICENSE file for full licensing details.
##############################################################################
from openerp import models, fields, api
from openerp.addons.connector.event import on_record_write


@on_record_write(model_names=['stock.move', 'stock.picking'])
def register_picking_change(session, model_name, record_id, vals):
    if 'state' not in vals:
        return True
    record = session.env[model_name].browse(record_id)
    if model_name == 'stock.move':
        return register_picking_change(session,
                                       'stock.picking',
                                       record.picking_id.id,
                                       vals)
    elif model_name == 'stock.picking' and 'state' in vals:
        key = '{0}_state_{1}'.format(model_name, record.state)
        event_obj = session.env['stock_connector.event']
        domain = [
            ('code', '=', key),
            ('res_model', '=', model_name),
            ('res_id', '=', record_id),
            ('state', 'not in', ['done', 'cancel']),
        ]
        if not event_obj.search(domain, limit=1, count=True):
            values = {
                'res_model': model_name,
                'res_id': record_id,
                'code': key,
                'context': str(session.context)
            }
            event_obj.create(values)


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
