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
from openerp.tools import DEFAULT_SERVER_DATETIME_FORMAT
from openerp.addons.pc_connect_master.product_uom_ext import UOM_AGING_SELECTION_VALUES
from datetime import datetime, timedelta
from openerp.addons.pc_connect_master.utilities.date_utilities import get_number_of_natural_days


class stock_picking_config(osv.Model):
    _inherit = 'configuration.data'

    def check_old_stock_picking_out(self, cr, uid, context=None):
        ''' Checks for old pickings which have been for too much time opened,
            this includes also the back-orders; although the parameter to set
            the time to wait for back-orders and regular pickings are different,
            the logic is the same.
        '''
        config = self.get(cr, uid, [], context=context)

        issue_obj = self.pool.get('project.issue')
        stock_picking_obj = self.pool.get('stock.picking')

        now = datetime.now()

        common_domain = [('state', 'not in', ['done', 'cancel'])]
        domain_backorders = []
        domain_regular_pickings = []

        # Gets the target date for regular pickings.
        if config.stock_picking_out_max_open_age:
            if config.stock_picking_out_max_open_age_uom != 'days':
                limit_delta = timedelta(**{config.stock_picking_out_max_open_age_uom: config.stock_picking_out_max_open_age})
                target_date = datetime.strftime(now - limit_delta, DEFAULT_SERVER_DATETIME_FORMAT)
            else:  # if config.stock_picking_out_max_open_age_uom == 'days':
                # If we selected 'days' as the unit of measure, then we take into account only weekdays.
                actual_weekdays = config.get_open_days_support(context=context)
                num_natural_days = get_number_of_natural_days(now, config.stock_picking_out_max_open_age, 'backward', actual_weekdays)
                target_date = datetime.strftime(now - timedelta(days=num_natural_days), DEFAULT_SERVER_DATETIME_FORMAT)
            domain_regular_pickings.append(('date', '<', target_date))

        # Gets the target date for back-orders
        if config.open_backorder_alarming_age_days:
            actual_weekdays = config.get_open_days_support(context=context)
            num_natural_days = get_number_of_natural_days(now, config.open_backorder_alarming_age_days, 'backward', actual_weekdays)
            target_date = datetime.strftime(now - timedelta(days=num_natural_days), DEFAULT_SERVER_DATETIME_FORMAT)
            domain_backorders.extend([('backorder_id', '!=', False),
                                      ('date', '<', target_date),
                                      ])

        # Looks for old pickings.
        old_picking_ids = None
        if domain_regular_pickings:
            domain_regular_pickings.extend(common_domain)
            old_picking_ids = set(stock_picking_obj.search(cr, uid, domain_regular_pickings, context=context))

        # Looks for old back-orders.
        old_backorders_ids = None
        if domain_backorders:
            domain_backorders.extend(common_domain)
            old_backorders_ids = set(stock_picking_obj.search(cr, uid, domain_backorders, context=context))

        pickings_to_alarm_ids = list(old_picking_ids | old_backorders_ids)
        for stock_picking in stock_picking_obj.browse(cr, uid, pickings_to_alarm_ids, context=context):
            msg = _('{0} with ID={1}, has exceeded the alarming date.'.format(stock_picking.name, stock_picking.id))
            tags = []
            if stock_picking.id in old_picking_ids:
                tags.append('delivery-order-max-open-age')
            if stock_picking.id in old_backorders_ids:
                tags.append('backorder-order-max-open-age')

            issue_ids = issue_obj.find_resource_issues(cr, uid, 'stock.picking', stock_picking.id,
                                                       tags=tags, create=True, reopen=True, context=context)
            for issue in issue_obj.browse(cr, uid, issue_ids, context=context):
                if issue.create_date == issue.write_date:
                    # Only write message when just created
                    issue.message_post(msg)

        return True

    _columns = {
        'stock_picking_out_max_open_age': fields.integer('Open Delivery Order Alarming Age', required=True),
        'stock_picking_out_max_open_age_uom': fields.selection(UOM_AGING_SELECTION_VALUES, string='Open Delivery Order Alarming Age UOM', required=True),
        'stock_picking_in_partly_fullfilment_alarm_wait': fields.integer('Open Incoming Shipment Alarming Age', required=True),
        'stock_picking_in_partly_fullfilment_alarm_wait_uom': fields.selection(UOM_AGING_SELECTION_VALUES, string='Open Incoming Shipment Alarming Age UOM', required=True),
    }

    _defaults = {
        'stock_picking_out_max_open_age_uom': UOM_AGING_SELECTION_VALUES[0][0],
        'stock_picking_in_partly_fullfilment_alarm_wait_uom': UOM_AGING_SELECTION_VALUES[0][0],
    }

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
