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
###############################################################################

from openerp.osv import fields, osv
from openerp.tools.translate import _


class wizard_invoice_report(osv.TransientModel):
    _name = 'pc_connect_master.wiz_invoice_report'

    _columns = {
        'start_date': fields.date('Start Date'),
        'end_date': fields.date('End Date'),
        'period': fields.many2one('account.period', 'Period'),
    }

    def onchange_period(self, cr, uid, ids, period_id, context=None):
        period = self.pool['account.period'].browse(cr, uid, period_id,
                                                    context=context)
        return {
            'value': {
                'start_date': period.date_start,
                'end_date': period.date_stop,
            }
        }

    def action_open(self, cr, uid, ids, context=None):
        invoice_obj = self.pool['account.invoice']
        payment_obj = self.pool['account.move.line']
        if isinstance(ids, list):
            ids = ids[0]
        if context is None:
            context = {}
        else:
            context = context.copy()

        wiz = self.browse(cr, uid, ids, context=context)
        start_condition = ('date_invoice', '>=', wiz.start_date)
        end_condition = ('date_invoice', '<', wiz.end_date)
        open_condition = ('state', '=', 'open')
        if wiz.end_date:
            # Created before the ending period
            domain = ['&', open_condition, end_condition]
        else:
            # Just, state open
            domain = [open_condition]

        # Now, we look for already paid invoices
        domain2 = [('state', '=', 'done')]
        if wiz.end_date:
            domain2 = ['&', end_condition] + domain2
        closed_invoice_ids = invoice_obj.search(cr, uid, domain2,
                                                context=context)
        if wiz.end_date:
            # If they have payments after, then we take those
            unfinished_ids = []
            for invoice_id in closed_invoice_ids:
                if payment_obj.search(cr, uid, [
                    ('invoice_id', '=', invoice_id),
                    ('date', '>', wiz.end_date),
                    ('state', '=', 'valid'),
                ], context=context, count=True, limit=1):
                    unfinished_ids.append(invoice_id)
            if len(unfinished_ids) > 0:
                domain = ['|', ('id', 'in', unfinished_ids)] + domain

        tree_id = self.pool['ir.model.data']\
            .get_object_reference(cr, uid,
                                  'pc_connect_master',
                                  'invoice_report_summary')[1]
        name = _('Chart of Open Invoices')
        if wiz.start_date or wiz.end_date:
            name = '%s (%s - %s)' % (name, wiz.start_date or '', wiz.end_date or '')
        return {
            'name': name,
            'type': 'ir.actions.act_window',
            'res_model': 'account.invoice',
            'res_id': False,
            'target': 'current',
            'context': context,
            'view_mode': 'tree',
            'domain': domain,
            'views': [(tree_id, 'tree'), (None, 'form')]
        }
