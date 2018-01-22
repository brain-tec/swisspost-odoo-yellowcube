# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>).
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

from osv import fields, osv
import time

class account_report_general_ledger(osv.osv_memory):
    _inherit = "account.common.account.report"
    _name = "account.report.general.ledger"
    _description = "General Ledger Report"

    _columns = {
        'landscape': fields.boolean("Landscape Mode"),
        'initial_balance': fields.boolean("Include initial balances",
                                          help='It adds initial balance row on report which display previous sum amount of debit/credit/balance'),
        'amount_currency': fields.boolean("With Currency", help="It adds the currency column if the currency is different then the company currency"),
        'sortby': fields.selection([('sort_date', 'Date'), ('sort_journal_partner', 'Journal & Partner')], 'Sort By', required=True),
        'filter': fields.selection([('filter_no', 'No Filters'), ('filter_date', 'Date'), ('filter_period', 'Periods')], "Filter by", required=True),
        'account_id': fields.many2one('account.account', 'Account', required=False,
                                      help='Set Account to filter the output',),    
    }
    _defaults = {
        #hack by jool
        'landscape': False,
        'amount_currency': False,
        'sortby': 'sort_date',
        'initial_balance': True,
        'filter': 'filter_period',
    }

    def onchange_fiscalyear(self, cr, uid, ids, fiscalyear=False, context=None):
        res = {}
        if not fiscalyear:
            res['value'] = {'initial_balance': False}
        else:
            now = time.strftime('%Y-%m-%d')
            fiscalyear_select = self.pool.get('account.fiscalyear').browse(cr, uid, fiscalyear)
            fiscalyear_now = self.pool.get('account.fiscalyear').search(cr, uid, [('date_start', '<', now), ('date_stop', '>', now)], limit=1 )[0]
            if fiscalyear_now == fiscalyear:
                res['value'] = {'period_from': False, 'period_to': False, 'date_from': time.strftime('%Y-01-01'), 'date_to': time.strftime('%Y-%m-%d')}
            else:
                res['value'] = {'period_from': False, 'period_to': False, 'date_from': fiscalyear_select.date_start, 'date_to': fiscalyear_select.date_stop}
        return res

    def _print_report(self, cr, uid, ids, data, context=None):
        if context is None:
            context = {}
        data = self.pre_print_report(cr, uid, ids, data, context=context)
        print 'data: ', data
        data['form'].update(self.read(cr, uid, ids, ['landscape',  'initial_balance', 'amount_currency', 'sortby', 'account_id'])[0])
        print 'data: ', data
        if not data['form']['fiscalyear_id']:# GTK client problem onchange does not consider in save record
            data['form'].update({'initial_balance': False})
        if data['form']['landscape']:
            return { 'type': 'ir.actions.report.xml', 'report_name': 'account.ledger_bt_landscape', 'datas': data}
        #hack jool
        return { 'type': 'ir.actions.report.xml', 'report_name': 'account.ledger_bt', 'datas': data}

account_report_general_ledger()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
