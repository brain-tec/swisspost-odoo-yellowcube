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
import pooler

class account_oplist(osv.osv_memory):
    _name = 'account.oplist.cust'
    _description = 'Account OP List Cust'
    _inherit = "account.common.report"
    _columns = {
        'result_selection': fields.selection([('customer','Receivable Accounts'),
                                              ('supplier','Payable Accounts'),
                                              ('customer_supplier','Receivable and Payable Accounts')],
                                              "Partner's", required=True),
        'date2': fields.date('Duedate', required=True),
        'company_id': fields.many2one('res.company', 'Company', required=True),
        'partner_id': fields.many2one('res.partner', 'Partner', required=False),        
        'filter_on_periods': fields.boolean('Filter on periods', help="If this flag is set, it takes all open entries depending on the periods whose end date is lower or equal than the end date of the fiscalyear of the duedate."),
    }

    def _get_company(self, cr, uid, context):
        user = pooler.get_pool(cr.dbname).get('res.users').browse(cr, uid, uid, context=context)
        if user.company_id:
            company_id = user.company_id.id
        else:
            company_id = pooler.get_pool(cr.dbname).get('res.company').search(cr, uid, [('parent_id', '=', False)])[0]

        return company_id or False

    _defaults = {
        'result_selection': 'customer_supplier',
        'date2': lambda *a: time.strftime('%Y-%m-%d'),
        'company_id': _get_company,
    }

    def create_oplist(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        datas = {'ids': context.get('active_ids', [])}
        datas['model'] = 'account.tax.code'
        datas['form'] = self.read(cr, uid, ids)[0]
        #datas['form']['company_id'] = self.pool.get('account.tax.code').browse(cr, uid, [datas['form']['chart_tax_id']], context=context)[0].company_id.id
        datas['form']['company_id'] = datas['form']['company_id'][0]
        datas['form']['chart_account_id'] = datas['form']['chart_account_id'][0]
        datas['form']['fiscalyear_id'] = datas['form']['fiscalyear_id'][0]
        return {
            'type': 'ir.actions.report.xml',
            'report_name': 'account.oplist.cust',
            'datas': datas,
        }

account_oplist()


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
