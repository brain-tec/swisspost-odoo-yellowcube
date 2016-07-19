# b-*- encoding: utf-8 -*-
##############################################################################
#
#    Copyright (c) 2015 brain-tec AG (http://www.brain-tec.ch)
#    All Right Reserved
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################
from openerp.osv import osv, fields
from openerp.tools.translate import _
import logging
import sys
logger = logging.getLogger(__name__)


EVENT_STATE_DRAFT = 'draft'
EVENT_STATE_DONE = 'done'
EVENT_STATE_CANCEL = 'cancel'
EVENT_STATE_IGNORED = 'ignore'


_EVENT_STATE = [
    (EVENT_STATE_DRAFT, 'Waiting'),
    (EVENT_STATE_DONE, 'Processed'),
    (EVENT_STATE_CANCEL, 'Cancelled'),
    (EVENT_STATE_IGNORED, 'Ignored'),
]


def check_all_events(self, cr, uid, ids, context, warehouse_id):
    """
    This method search in the current model, for every function that can be used for event checking.
    (For now, it only checks the name begins with 'event_')

    Then, for each method, it calls it, one by one, with every id, on by one,
    also sending the required context.

    The context passed, carries enough info, to simplify inner calls to the create method of stock.event

    Important Note: Does event_ methods, must follow the same signature as this function.

    @param context: context to copy and pass to each event method.
    @param warehouse_id: Id of the related warehouse, which the event relates to
    """
    if not warehouse_id:
        logger.warning("The events cannot be processed because they have not warehouse.")
        return True
    events = [x for x in dir(self) if x[:6] == 'event_']
    logger.debug("Found events: {0}".format(events))
    for event in events:
        f = getattr(self, event)
        for res_id in ids:
            ctx = context.copy()
            ctx.update({
                'active_id': res_id,
                'active_model': context.get('active_model', self._name),
                'warehouse_id': warehouse_id,
            })
            f(cr, uid, res_id, context=ctx, warehouse_id=warehouse_id)
    return True


class stock_event(osv.Model):
    _name = 'stock.event'

    def open_record(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        if isinstance(ids, list):
            ids = ids[0]
        this = self.browse(cr, uid, ids, context)
        return {
            'type': 'ir.actions.act_window',
            'res_model': this.model,
            'res_id': this.res_id,
            'view_mode': 'form',
        }

    def find_or_create(self, cr, uid, vals, context=None):
        """
        This function tries to find an event that matches the key search fields.
        If that event does not exist, then it is created with the info provided at vals
        """
        if context is None:
            context = {}
        search_items = ['warehouse_id', 'event_code', 'model', 'res_id']
        def_vals = self.default_get(cr, uid, search_items, context)
        def_vals.update(vals)
        domain = []
        for k in search_items:
            domain.append((k, '=', def_vals[k]))
        logger.debug("Looking for events {0}".format(domain))
        ids = self.search(cr, uid, domain, context=context)
        if not ids:
            ids = [self.create(cr, uid, vals, context)]
        return ids

    def default_get(self, cr, uid, fields_list, context=None):
        if context is None:
            context = {}
        ret = super(stock_event, self).default_get(cr, uid, fields_list, context=context)
        if 'context' not in ret:
            ret['context'] = str(context)
        for kr, kc in [('model', 'active_model'),
                       ('res_id', 'active_id'),
                       ('warehouse_id', 'warehouse_id')
                       ]:
            if kr not in ret and kc in context:
                ret[kr] = context[kc]
        return ret

    _columns = {
        'warehouse_id': fields.many2one('stock.warehouse', 'Warehouse', required=True),
        'create_date': fields.datetime('Create date', required=False),
        'write_date': fields.datetime('Write date', required=False),
        'event_code': fields.char('Event code', required=True),
        'model': fields.char('res.model'),
        'res_id': fields.integer('resource ID'),
        'context': fields.text('context', required=True),
        'state': fields.selection(_EVENT_STATE, string='state', required=True),
        'info': fields.text('Info', required=False),
        'error': fields.boolean('Error', required=False),
    }

    _rec_name = 'event_code'

    _order = "create_date DESC"

    _defaults = {
        'state': 'draft',
        'error': False,
    }

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
