# b-*- encoding: utf-8 -*-
##############################################################################
#
#    Copyright (c) 2014 brain-tec AG (http://www.brain-tec.ch)
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
from openerp.tools.safe_eval import safe_eval


class queue_job_ext(osv.Model):
    _inherit = 'queue.job'

    _columns = {'graph_count': fields.integer(string="Graph weigth", required=True)}

    _defaults = {'graph_count': 1}

    def open_resource(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        if isinstance(ids, list):
            ids = ids[0]

        job = self.browse(cr, uid, ids, context=context)

        # This is highly heuristic, and attempts to extract the model name,
        # and the resource ID, of the function call to be executed by the job.
        # It will work provided that the model name doesn't contain commas (which
        # I think will be always true).
        params = job.func_string[job.func_string.index('(') + 1:]
        res_model = safe_eval(params.split(',')[0])
        res_id = safe_eval(params.split(',')[1])

        if len(params) < 2 or not params[1]:
            return False

        return {
            'name': job.name,
            'context': context,
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': res_model,
            'res_id': res_id,
            'type': 'ir.actions.act_window',
            'target': None,
        }

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
