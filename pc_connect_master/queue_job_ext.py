# b-*- encoding: utf-8 -*-
##############################################################################
#
#    Copyright (c) 2014 brain-tec AG (http://www.braintec-group.com)
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
from utilities.db import create_db_index
from openerp.tools.translate import _
from openerp.tools.safe_eval import safe_eval


class queue_job_ext(osv.Model):
    _inherit = 'queue.job'

    _columns = {'graph_count': fields.integer(string="Graph weigth", required=True)}

    _defaults = {'graph_count': 1}

    def init(self, cr):
        """ Creates some indices that can not be created directly using the ORM
        """
        create_db_index(cr, 'queue_job_active_state_exc_info_index', 'queue_job', 'active, state, exc_info')

    def open_resource(self, cr, uid, ids, context=None):
        """ Opens the record associated to the job.
        """
        if context is None:
            context = {}
        if not isinstance(ids, list):
            ids = [ids]

        job = self.browse(cr, uid, ids[0], context=context)

        # This is highly heuristic, and attempts to extract the resource ID.
        params = job.func_string[job.func_string.index('(') + 1:]
        res_model = job.model_name
        if 'stock.picking.in' in job.func_string:
            # This is special func_string of the type
            # _check_partly_fullfilment_alarm_wait('stock.picking.in', 254L)
            res_id = safe_eval(params.split(',')[-1].rstrip(')').rstrip('L'))
        else:
            res_id = safe_eval(params.split(',')[1])

        if len(params) < 2 or not params[1]:
            return False

        vals = {
            'name': job.name,
            'context': context,
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': res_model,
            'res_id': res_id,
            'type': 'ir.actions.act_window',
            'target': None,
        }

        # Customer Invoices require a special view, since the default one
        # looses a lot of information.
        if res_model == 'account.invoice':
            act_window_obj = self.pool.get('ir.actions.act_window')
            act_window_view_obj = self.pool.get('ir.actions.act_window.view')
            act_window_ids = act_window_obj.search(
                cr, uid, [
                    ('name', '=', 'Customer Invoices'),
                    ('res_model', '=', 'account.invoice'),
                    ('type', '=', 'ir.actions.act_window'),
                ], limit=1, context=context)
            act_window_view_ids = []
            if act_window_ids:
                act_window_view_ids = act_window_view_obj.search(
                    cr, uid, [
                        ('act_window_id', '=', act_window_ids[0]),
                        ('view_mode', '=', 'form'),
                    ], limit=1, context=context)
            if act_window_view_ids:
                act_window_view = act_window_view_obj.browse(
                    cr, uid, act_window_view_ids[0], context=context)
                vals.update({'view_id': act_window_view.view_id.id})

        return vals

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
