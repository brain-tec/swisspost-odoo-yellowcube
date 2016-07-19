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
import datetime
from openerp.tools import DEFAULT_SERVER_DATETIME_FORMAT
from openerp.addons.pc_connect_master.utilities.date_utilities import get_number_of_natural_days


class stock_production_lot_ext(osv.Model):
    _inherit = 'stock.production.lot'

    def yc_get_missing_bar_lots(self, cr, uid, ids, context=None):
        ''' Returns the list of IDs for those lots which were not seen in a BAR for the
            amount of days which was indicated in the stock.connect
            AND which had some stock available.
        '''
        if context is None:
            context = {}

        ret = []
        now = datetime.datetime.now()
        connect_pool = self.pool.get('stock.connect')

        # Gets all those stock.connect which have been set to check for the products which has not appeared in BAR for a certain amount of days.
        connect_ids = connect_pool.search(cr, uid, [('yc_missing_bar_days_due', '>', '0')], context=context, order='yc_missing_bar_days_due DESC')
        if connect_ids:

            # Gets the number of days to check against.
            limit = connect_pool.read(cr, uid, connect_ids, ['yc_missing_bar_days_due'], context=context)[0]['yc_missing_bar_days_due']

            # Searches for those lots which were absent in a BAR for the given amount of days.
            config_data = self.pool.get('configuration.data').get(cr, uid, [], context=context)
            actual_weekdays = config_data.get_open_days_support(context=context)
            date_limit = now - datetime.timedelta(days=get_number_of_natural_days(now, limit, 'backward', actual_weekdays))
            domain = [('yc_last_bar_update', '<', date_limit.strftime(DEFAULT_SERVER_DATETIME_FORMAT)),
                      ('virtual_available_for_sale', '>', 0)]
            if ids:
                domain.append(('id', 'in', ids))
            ids = self.search(cr, uid, domain, context=context)

            ret.extend(ids)

        return ret

    _columns = {
        'yellowcube_lot': fields.char('YCLot', size=10, help="YellowCube's lot."),
        'yc_last_bar_update': fields.datetime('Last Update from a BAR File'),
    }

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
