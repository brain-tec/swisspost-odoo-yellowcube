# b-*- encoding: utf-8 -*-
##############################################################################
#
#    Copyright (c) 2017 brain-tec AG (http://www.braintec-group.com)
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

from openerp.osv import osv, fields, orm
from openerp.addons.connector.queue.job import PENDING


class IrCronExt(orm.Model):
    _inherit = 'ir.cron'

    def _callback(self, cr, uid, model_name, method_name, args, job_id):
        """ Executes a scheduler. 
        
            Overridden so that if any of the jobs require to execute
            the MRP-scheduler in order to proceed, we do it before the
            jobs are executed. This is done because the scheduler may
            be expensive, and we really only need to execute it just once
            per each fire of the automation (since although more than one
            job may benefit from it, just an execution is needed).
        """

        search_domain = [
            ('state', '=', PENDING),
            ('func_string', 'like', '%deliveryorder_assignation_dropship%'),
        ]
        mrp_scheduler_execution_required = \
            bool(self.pool.get('queue.job').search(
                cr, uid, search_domain, count=True, limit=1))
        if mrp_scheduler_execution_required:
            self.pool.get('procurement.order').\
                mrp_scheduler_for_sale_order_automation(cr, uid)

        ret = super(IrCronExt, self)._callback(
            cr, uid, model_name, method_name, args, job_id)

        return ret
