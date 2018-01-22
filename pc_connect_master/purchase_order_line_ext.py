# b-*- encoding: utf-8 -*-
##############################################################################
#
#    Copyright (c) 2016 brain-tec AG (http://www.braintec-group.com)
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
from openerp.addons.pc_connect_master.utilities.date_utilities import get_number_of_natural_days
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT
from datetime import datetime, timedelta


class purchase_order_line_ext(osv.Model):
    _inherit = "purchase.order.line"

    def _get_date_planned(self, cr, uid, supplier_info, date_order_str, context=None):
        """ Overridden so that we substract the amount of days which are not weekdays
            if that is what is indicated in the configuration.
        """
        date_planned = super(purchase_order_line_ext, self)._get_date_planned(cr, uid, supplier_info, date_order_str, context)

        conf_data = self.pool.get('configuration.data').get(cr, uid, [], context=context)
        if conf_data.purchase_schedule_date_consider_only_weekdays:
            supplier_delay = int(supplier_info.delay) if supplier_info else 0
            date_order = datetime.strptime(date_order_str, DEFAULT_SERVER_DATE_FORMAT)
            num_natural_days = get_number_of_natural_days(date_order, supplier_delay, 'forward')
            date_planned = date_order + timedelta(days=num_natural_days)

        return date_planned

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
