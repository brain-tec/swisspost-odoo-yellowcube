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
from stock_event import check_all_events, EVENT_STATE_CANCEL
from openerp import SUPERUSER_ID
from openerp.addons.connector.queue.job import job, related_action
from openerp.addons.connector.session import ConnectorSession
from datetime import datetime, timedelta
from openerp.addons.pc_connect_master.utilities.date_utilities import get_number_of_natural_days
import logging
logger = logging.getLogger(__name__)


@job
def _check_partly_fullfilment_alarm_wait(session, model_name, record_id):
    '''Partly Fulfilled Procurement Alarming Age'''
    picking = session.browse(model_name, record_id)
    ret = True
    if picking.state in ['auto', 'assigned']:
        # If the stock.picking is open once the job triggers, then create an Issue
        _cr = session.cr
        _uid = session.uid
        _ctx = session.context
        if not _ctx:
            _ctx = {}
        ret = _ctx['issue_name'] = _('{0} Partly Fulfilled Alarm').format(picking.name)
        logger.info('stock.picking not finished {0}'.format(picking.name))
        issue_obj = session.pool.get('project.issue')
        issue_ids = issue_obj.find_resource_issues(_cr,
                                                   _uid,
                                                   model_name,
                                                   record_id,
                                                   tags=['procurements', 'missing-wbl'],
                                                   create=True,
                                                   reopen=True,
                                                   context=_ctx)
        for _id in issue_ids:
            issue_obj.message_post(_cr, _uid, _id, _('stock.picking not yet fulfilled'), context=_ctx)
    return ret


class stock_picking_in_ext(osv.Model):
    _inherit = 'stock.picking.in'

    def check_events_on_stock_picking_in(self, cr, uid, ids):
        return self.pool['stock.picking'].check_events_on_stock_picking(cr, uid, ids, context={'active_model': 'stock.picking.in'})

    _constraints = [
        (check_events_on_stock_picking_in, 'check of events on this item', []),
    ]


class stock_picking_out_ext(osv.Model):
    _inherit = 'stock.picking.out'

    def check_events_on_stock_picking_out(self, cr, uid, ids):
        return self.pool['stock.picking'].check_events_on_stock_picking(cr, uid, ids, context={'active_model': 'stock.picking.out'})

    _constraints = [
        (check_events_on_stock_picking_out, 'check of events on this item', []),
    ]


class stock_picking_ext(osv.Model):
    _inherit = 'stock.picking'

    def create(self, cr, uid, vals, context=None):
        if context is None:
            context = {}
        ret = super(stock_picking_ext, self).create(cr, uid, vals, context=context)
        self.check_events_on_stock_picking(cr, uid, [ret])
        return ret

    def write(self, cr, uid, ids, vals, context=None):
        if context is None:
            context = {}
        super(stock_picking_ext, self).write(cr, uid, ids, vals, context=context)
        self.check_events_on_stock_picking(cr, uid, ids)
        return True

    def _store_set_values(self, cr, uid, ids, fields, context):
        ret = super(stock_picking_ext, self)._store_set_values(cr, uid, ids, fields, context)
        self.check_events_on_stock_picking(cr, uid, ids)
        return ret

    def action_done(self, cr, uid, ids, context=None):
        ret = super(stock_picking_ext, self).action_done(cr, uid, ids, context=context)
        self._check_partial_delivery(cr, uid, ids, context)
        return ret

    def action_assign(self, cr, uid, ids, context=None):
        ret = super(stock_picking_ext, self).action_assign(cr, uid, ids, context)
        self.check_events_on_stock_picking(cr, uid, ids)
        return ret

    def test_done(self, cr, uid, ids, context=None):
        ret = super(stock_picking_ext, self).test_done(cr, uid, ids, context=context)
        self._check_partial_delivery(cr, uid, ids, context)
        return ret

    def _check_partial_delivery(self, cr, uid, ids, context):
        config = self.pool.get('configuration.data').get(cr, uid, [], context=context)
        if not config.stock_picking_in_partly_fullfilment_alarm_wait:
            return

        now = datetime.now()

        if config.stock_picking_in_partly_fullfilment_alarm_wait_uom == 'hours':
            limit_delta = timedelta(**{config.stock_picking_in_partly_fullfilment_alarm_wait_uom: config.stock_picking_in_partly_fullfilment_alarm_wait})
            next_execution_date = now + limit_delta
        elif config.stock_picking_in_partly_fullfilment_alarm_wait_uom == 'days':
            config_data = self.pool.get('configuration.data').get(cr, uid, [], context=context)
            actual_weekdays = config_data.get_open_days_support(context=context)
            num_natural_days = get_number_of_natural_days(now, config.stock_picking_in_partly_fullfilment_alarm_wait, 'forward', actual_weekdays)
            next_execution_date = now + timedelta(days=num_natural_days)

        for picking in self.browse(cr, uid, ids, context=context):
            if picking.type not in ['in']:
                continue
            # Now, any stock.picking.in will rise issues
            #  if not picking.backorder_id:
            #     continue
            if picking.state in ['auto', 'assigned']:
                logger.info('Creating differed stock.picking.in check')
                session = ConnectorSession(cr, uid, context)
                _check_partly_fullfilment_alarm_wait.delay(session,
                                                           'stock.picking.in',
                                                           picking.id,
                                                           eta=next_execution_date,
                                                           priority=20)
        return

    def event_change_on_stock_picking_state(self, cr, uid, ids, context, warehouse_id):
        if context is None:
            context = {}
        event_obj = self.pool.get('stock.event')
        picking = self.browse(cr, uid, ids, context)
        model = 'stock.picking.{0}'.format(picking.type)
        state = 'new_picking_state_{0}'.format(picking.state)
        vals = {'event_code': state,
                'model': model,
                'res_id': ids}
        event_obj.find_or_create(cr, uid, vals, context=context)

    def check_events_on_stock_picking(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        # For this check, we must be superuser
        uid = SUPERUSER_ID

        if not isinstance(ids, list):
            ids = [ids]
        for picking in self.browse(cr, uid, ids, context):
            warehouse_ids = []
            locations = []
            # First we get the location of this delivery
            if picking.location_id:
                loc = picking.location_id
                locations.append(loc)
            # Next, we get the location of the lines
            for line in picking.move_lines:
                locations.append(line.location_id)
                locations.append(line.location_dest_id)
            # Last, we get the warehouse of those locations
            warehouse_ids = []
            for loc in locations:
                for wl in loc.warehouse_ids:
                    if wl.warehouse_id and wl.warehouse_id.id not in warehouse_ids:
                        warehouse_ids.append(wl.warehouse_id.id)
            for warehouse_id in warehouse_ids:
                check_all_events(self, cr, uid, [picking.id], context=context, warehouse_id=warehouse_id)
        return True

    def get_process_date(self, cr, uid, ids, name, args, context=None):
        if context is None:
            context = {}
        ret = {}
        for stock_picking in self.browse(cr, uid, ids, context=context):
            ret[stock_picking.id] = stock_picking.min_date
        return ret

    def get_ready_for_export(self, cr, uid, ids, name, args, context=None):
        ''' A stock.picking is ready for export if its sale.orders have
            printed both its invoices and delivery slips.
        '''
        if context is None:
            context = {}

        res = {}
        for stock_picking in self.browse(cr, uid, ids, context=context):
            res[stock_picking.id] = (stock_picking.sale_id.invoices_printed and stock_picking.sale_id.delivery_orders_printed)
        return res

    _columns = {
        'process_date': fields.function(get_process_date,
                                        type='datetime',
                                        string="Process Date",
                                        store=False),

        'ready_for_export': fields.function(get_ready_for_export,
                                            type='boolean',
                                            string='Is it ready for export?',
                                            help='Indicates whether the stock.picking is ready for export to the warehouse.'),
    }

    _defaults = {
        'ready_for_export': False,
    }

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
