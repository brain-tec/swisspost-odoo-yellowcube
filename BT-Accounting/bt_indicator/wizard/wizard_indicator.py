# -*- encoding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution	
#    Copyright (C) 2004-2009 Tiny SPRL (<http://tiny.be>). All Rights Reserved
#    $Id$
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

from osv import osv, fields
import time

def onchange_filter_cust(self, cr, uid, ids, filter='filter_no', fiscalyear_id=False, context=None):
    res = {'value': {}}
    if filter == 'filter_no':
        res['value'] = {'period_from': False, 'period_to': False, 'date_from': False ,'date_to': False}
    if filter == 'filter_date':
        res['value'] = {'period_from': False, 'period_to': False, 'date_from': time.strftime('%Y-01-01'), 'date_to': time.strftime('%Y-%m-%d')}
    if filter == 'filter_period' and fiscalyear_id:
        start_period = end_period = False
        cr.execute('''
            SELECT * FROM (SELECT p.id
                           FROM account_period p
                           LEFT JOIN account_fiscalyear f ON (p.fiscalyear_id = f.id)
                           WHERE f.id = %s
                           --AND p.special = false
                           ORDER BY p.date_start ASC, p.code, p.special ASC
                           LIMIT 1) AS period_start
            UNION ALL
            SELECT * FROM (SELECT p.id
                           FROM account_period p
                           LEFT JOIN account_fiscalyear f ON (p.fiscalyear_id = f.id)
                           WHERE f.id = %s
                           AND p.date_start < NOW() AT TIME ZONE 'UTC'
                           AND p.special = false
                           ORDER BY p.date_stop DESC, p.code DESC
                           LIMIT 1) AS period_stop''', (fiscalyear_id, fiscalyear_id))
        periods =  [i[0] for i in cr.fetchall()]
        if periods and len(periods) > 1:
            start_period = periods[0]
            end_period = periods[1]
        res['value'] = {'period_from': start_period, 'period_to': end_period, 'date_from': False, 'date_to': False}
    return res

class account_indicator(osv.osv_memory):
    _name = 'account.indicator.cust'
    _description = 'Account Indicator Cust'
    _inherit = "account.common.report"
    _columns = {
        'based_on': fields.selection([('invoices', 'Invoices'),
                                      ('payments', 'Payments'),],
                                      'Based On', required=True),
        'chart_tax_id': fields.many2one('account.tax.code', 'Chart of Tax', help='Select Charts of Taxes', required=True, domain = [('parent_id','=', False)]),
        #'filter': fields.selection([('filter_date', 'Date')], "Filter by", required=True),
        'filter': fields.selection([('filter_no', 'No Filters'), ('filter_date', 'Date'), ('filter_period', 'Periods')], "Filter by", required=True),
    }

    def _get_tax(self, cr, uid, context=None):
        taxes = self.pool.get('account.tax.code').search(cr, uid, [('parent_id', '=', False)], limit=1)
        return taxes and taxes[0] or False

    _defaults = {
        'based_on': 'invoices',
        'chart_tax_id': _get_tax,
        'filter': 'filter_period',
    }

    def create_indicator(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        datas = {'ids': context.get('active_ids', [])}
        datas['model'] = 'account.tax.code'
        datas['form'] = self.read(cr, uid, ids)[0]
        #datas['form']['company_id'] = self.pool.get('account.tax.code').browse(cr, uid, [datas['form']['chart_tax_id']], context=context)[0].company_id.id
        return {
            'type': 'ir.actions.report.xml',
            'report_name': 'account.indicator.cust',
            'datas': datas,
        }

#    def onchange_fiscalyear(self, cr, uid, ids, fiscalyear=False, context=None):
#        res = {}
#        if not fiscalyear:
#            res['value'] = {'initial_balance': False}
#        else:
#            now = time.strftime('%Y-%m-%d')
#            fiscalyear_select = self.pool.get('account.fiscalyear').browse(cr, uid, fiscalyear)
#            fiscalyear_now = self.pool.get('account.fiscalyear').search(cr, uid, [('date_start', '<', now), ('date_stop', '>', now)], limit=1 )[0]
#            if fiscalyear_now == fiscalyear:
#                res['value'] = {'period_from': False, 'period_to': False, 'date_from': time.strftime('%Y-01-01'), 'date_to': time.strftime('%Y-%m-%d')}
#            else:
#                res['value'] = {'period_from': False, 'period_to': False, 'date_from': fiscalyear_select.date_start, 'date_to': fiscalyear_select.date_stop}
#        return res

    def onchange_filter_cust(self, cr, uid, ids, filter='filter_no', fiscalyear_id=False, context=None):
        return onchange_filter_cust(self, cr, uid, ids, filter, fiscalyear_id, context)
    
account_indicator()

class account_indicator_bilanz(osv.osv_memory):
    _name = 'account.indicator.cust.bilanz'
    _description = 'Account Indicator Cust Bilanz'
    _inherit = "account.common.report"
    _columns = {
        'based_on': fields.selection([('invoices', 'Invoices'),
                                      ('payments', 'Payments'),],
                                      'Based On', required=True),
        'chart_tax_id': fields.many2one('account.tax.code', 'Chart of Tax', help='Select Charts of Taxes', required=True, domain = [('parent_id','=', False)]),
        #'filter': fields.selection([('filter_date', 'Date')], "Filter by", required=True),
        'filter': fields.selection([('filter_no', 'No Filters'), ('filter_date', 'Date'), ('filter_period', 'Periods')], "Filter by", required=True),
    }

    def _get_tax(self, cr, uid, context=None):
        taxes = self.pool.get('account.tax.code').search(cr, uid, [('parent_id', '=', False)], limit=1)
        return taxes and taxes[0] or False

    _defaults = {
        'based_on': 'invoices',
        'chart_tax_id': _get_tax,
        'filter': 'filter_period',
    }

    def create_indicator(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        datas = {'ids': context.get('active_ids', [])}
        datas['model'] = 'account.tax.code'
        datas['form'] = self.read(cr, uid, ids)[0]
        #datas['form']['company_id'] = self.pool.get('account.tax.code').browse(cr, uid, [datas['form']['chart_tax_id']], context=context)[0].company_id.id
        return {
            'type': 'ir.actions.report.xml',
            'report_name': 'account.indicator.cust.bilanz',
            'datas': datas,
        }

    def onchange_filter_cust(self, cr, uid, ids, filter='filter_no', fiscalyear_id=False, context=None):
        return onchange_filter_cust(self, cr, uid, ids, filter, fiscalyear_id, context)

account_indicator_bilanz()


class account_indicator_er(osv.osv_memory):
    _name = 'account.indicator.cust.er'
    _description = 'Account Indicator Cust ER'
    _inherit = "account.common.report"
    _columns = {
        'based_on': fields.selection([('invoices', 'Invoices'),
                                      ('payments', 'Payments'),],
                                      'Based On', required=True),
        'chart_tax_id': fields.many2one('account.tax.code', 'Chart of Tax', help='Select Charts of Taxes', required=True, domain = [('parent_id','=', False)]),
        #'filter': fields.selection([('filter_date', 'Date')], "Filter by", required=True),
        'filter': fields.selection([('filter_no', 'No Filters'), ('filter_date', 'Date'), ('filter_period', 'Periods')], "Filter by", required=True),
    }

    def _get_tax(self, cr, uid, context=None):
        taxes = self.pool.get('account.tax.code').search(cr, uid, [('parent_id', '=', False)], limit=1)
        return taxes and taxes[0] or False

    _defaults = {
        'based_on': 'invoices',
        'chart_tax_id': _get_tax,
        'filter': 'filter_period',
    }

    def create_indicator(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        datas = {'ids': context.get('active_ids', [])}
        datas['model'] = 'account.tax.code'
        datas['form'] = self.read(cr, uid, ids)[0]
        #datas['form']['company_id'] = self.pool.get('account.tax.code').browse(cr, uid, [datas['form']['chart_tax_id']], context=context)[0].company_id.id
        return {
            'type': 'ir.actions.report.xml',
            'report_name': 'account.indicator.cust.er',
            'datas': datas,
        }

#    def onchange_fiscalyear(self, cr, uid, ids, fiscalyear=False, context=None):
#        res = {}
#        if not fiscalyear:
#            res['value'] = {'initial_balance': False}
#        else:
#            now = time.strftime('%Y-%m-%d')
#            fiscalyear_select = self.pool.get('account.fiscalyear').browse(cr, uid, fiscalyear)
#            fiscalyear_now = self.pool.get('account.fiscalyear').search(cr, uid, [('date_start', '<', now), ('date_stop', '>', now)], limit=1 )[0]
#            if fiscalyear_now == fiscalyear:
#                res['value'] = {'period_from': False, 'period_to': False, 'date_from': time.strftime('%Y-01-01'), 'date_to': time.strftime('%Y-%m-%d')}
#            else:
#                res['value'] = {'period_from': False, 'period_to': False, 'date_from': fiscalyear_select.date_start, 'date_to': fiscalyear_select.date_stop}
#        return res

    def onchange_filter_cust(self, cr, uid, ids, filter='filter_no', fiscalyear_id=False, context=None):
        return onchange_filter_cust(self, cr, uid, ids, filter, fiscalyear_id, context)
    
account_indicator_er()

#import time
#import wizard
#
#dates_form = '''<?xml version="1.0"?>
#<form string="Indicator Report">
#    <field name="date1"/>
#    <field name="date2"/>
#</form>'''
#
#dates_fields = {
#    'date1': {'string':'Start of period', 'type':'date', 'required':True, 'default': lambda *a: time.strftime('%Y-01-01')},
#    'date2': {'string':'End of period', 'type':'date', 'required':True, 'default': lambda *a: time.strftime('%Y-%m-%d')},
#}
#
#class wizard_report(wizard.interface):
#    states = {
#        'init': {
#            'actions': [],
#            'result': {'type':'form', 'arch':dates_form, 'fields':dates_fields, 'state':[('end','Cancel'), ('report','Print')]}
#        },
#        'report': {
#            'actions': [],
#            'result': {'type':'print', 'report':'account.indicator.cust', 'state':'end'}
#        }
#    }
#wizard_report('account.indicator.cust')

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: