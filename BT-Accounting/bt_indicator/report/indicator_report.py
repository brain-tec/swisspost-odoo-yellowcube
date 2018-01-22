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

import time
import pooler
import rml_parse
import copy
from report import report_sxw
import pdb
import re
import datetime
from dateutil.relativedelta import relativedelta
from openerp.osv import osv
from openerp.tools.translate import _

from common_report_header import common_report_header

class indicator_report(report_sxw.rml_parse, common_report_header):
    _name = 'report.account.indicator.cust'
    
    def set_context(self, objects, data, ids, report_type=None):
        #print 'set_context ids: ', ids
        #print 'data: ', data
        #hack jool: 6.1
        #new_ids = ids
        new_ids = [data['form']['id']]
        res = {}
        self.period_ids = []
        period_obj = self.pool.get('account.period')
        res['periods'] = ''
        #hack jool: 6.1
        fiscalyear = data['form'].get('fiscalyear_id', False)
        if fiscalyear:
            res['fiscalyear'] = fiscalyear[0]
        else:
            res['fiscalyear'] = False

        if data['form'].get('period_from', False) and data['form'].get('period_to', False):
            self.period_ids = period_obj.build_ctx_periods(self.cr, self.uid, data['form']['period_from'][0], data['form']['period_to'][0])
            periods_l = period_obj.read(self.cr, self.uid, self.period_ids, ['name'])
            for period in periods_l:
                if res['periods'] == '':
                    res['periods'] = period['name']
                else:
                    res['periods'] += ", "+ period['name']
        return super(indicator_report, self).set_context(objects, data, new_ids, report_type=report_type)
    
    def __init__(self, cr, uid, name, context):
        super(indicator_report, self).__init__(cr, uid, name, context=context)
#        self.bilanz = False
#        if name == 'account.indicator.cust.bilanz':
#            self.bilanz = True
        self.sum_debit = 0.00
        self.sum_credit = 0.00
        self.child_ids = ""
        self.query = ""
        self.ids = context['active_ids']
        self.localcontext.update({
            'time': time,
            'get_period': self._get_period,
            'get_codes': self._get_codes,
            'get_general': self._get_general,
            'get_company': self._get_company,
            'get_currency': self._get_currency,
            'get_lines' : self._get_lines,
            'get_dates':self.get_dates,
            'get_solde':self._get_solde,
            'get_solde_new':self._get_solde_new,
            'lines': self.lines,
            'get_balance_last_year': self.get_balance_last_year,
            'get_start_period': self.get_start_period,
            'get_end_period': self.get_end_period,
            'get_sortby': self._get_sortby,
            'get_filter': self._get_filter,
            'get_journal': self._get_journal,
            'get_start_date':self._get_start_date,
            'get_end_date':self._get_end_date,
            'get_data':self.get_data,
            'calculate_change_in_percent': self._calculate_change_in_percent,
        })
        self.context = context
    
    def _get_solde_new(self, codes, form, current_year=False):
        #split comma seperated into list
        def split_into_list(s, splitifeven):
            if splitifeven & 1:
                return [s]
            return [x.strip() for x in s.split(",") if x.strip() != '']
        code_ids = sum([split_into_list(s, sie) for sie, s in enumerate(codes.split('"'))], [])
        
        ctx = self.context.copy()
        ctx['fiscalyear'] = form['fiscalyear_id'][0]
        # HACK: 07.08.2013 08:33:16: olivier: set periods every time
        pids = []
        pids += map(lambda x: str(x.id), self.pool.get('account.fiscalyear').browse(self.cr, self.uid, form['fiscalyear_id'][0]).period_ids)
        ctx['periods'] = pids
        if form['filter'] == 'filter_period':
            ctx['period_from'] = form['period_from'][0]
            ctx['period_to'] = form['period_to'][0]
            ctx['periods'] = False
        elif form['filter'] == 'filter_date':
            ctx['date_from'] = form['date_from']
            ctx['date_to'] =  form['date_to']
            ctx['periods'] = False
        balance = 0
        for code_id in code_ids:
            ids = self.pool.get('account.account').search(self.cr, self.uid, [('code','=',code_id)])
            ctx['state'] = 'posted'
            accounts = self.pool.get('account.account').read(self.cr, self.uid, ids,['type','code','name','debit','credit','balance','parent_id'], ctx)
            for account in accounts:
                if current_year:
                    balance += account['balance']
                else:
                    balance += self.get_balance_last_year(account['id'], ctx, form)
        
        return balance
    
    def _get_solde(self, form, codes, current_year=False):
        sum_credit_total = 0
        #split comma seperated into list
        def split_into_list(s, splitifeven):
            if splitifeven & 1:
                return [s]
            return [x.strip() for x in s.split(",") if x.strip() != '']
        code_ids = sum([split_into_list(s, sie) for sie, s in enumerate(codes.split('"'))], [])
        
        start = datetime.date.fromtimestamp(time.mktime(time.strptime(form['date_from'],"%Y-%m-%d")))
        end = datetime.date.fromtimestamp(time.mktime(time.strptime(form['date_to'],"%Y-%m-%d")))
        if not current_year:
#            start = start+datetime.timedelta(days=-365)
#            end = end+datetime.timedelta(days=-365)
            start = start-relativedelta(years=1)
            end = end-relativedelta(years=1)
        
        for code_id in code_ids:
            account_ids = self.pool.get('account.account').search(self.cr, self.uid,[('parent_id', 'child_of', code_id)])
            if len(account_ids) == 1:
                self.cr.execute("SELECT (sum(debit) - sum(credit)) as tot_solde "\
                        "FROM account_move_line l "\
                        "WHERE l.period_id in (%s) AND l.date <= '%s' AND l.date >= '%s' AND l.account_id in (%s) "%( self.period_ids, end, start, account_ids[0]))
            else:
                self.cr.execute("SELECT (sum(debit) - sum(credit)) as tot_solde "\
                        "FROM account_move_line l "\
                        "WHERE l.period_id in (%s) AND l.date <= '%s' AND l.date >= '%s' AND l.account_id in %s "%( self.period_ids, end, start, tuple(account_ids)))
            sum_credit = self.cr.fetchone()[0] or 0.0
            if sum_credit <> 0:
                sum_credit = sum_credit*-1
            sum_credit_total += sum_credit
        return sum_credit_total

    def get_data(self,data):
        cr, uid = self.cr, self.uid
        db_pool = pooler.get_pool(self.cr.dbname)

        #Getting Profit or Loss Balance from profit and Loss report
        self.obj_pl.get_data(data)
        self.res_bl = self.obj_pl.final_result()

        account_pool = db_pool.get('account.account')
        currency_pool = db_pool.get('res.currency')

        types = [
            'liability',
            'asset'
        ]

        ctx = self.context.copy()
        ctx['fiscalyear'] = data['form'].get('fiscalyear_id', False)[0]

        if data['form']['filter'] == 'filter_period':
            ctx['periods'] = data['form'].get('periods', False)
        elif data['form']['filter'] == 'filter_date':
            ctx['date_from'] = data['form'].get('date_from', False)
            ctx['date_to'] =  data['form'].get('date_to', False)
        ctx['state'] = data['form'].get('target_move', 'all')
        
    def get_dates(self, form):
        result=''
        date_from = time.strptime(form['date_from'],'%Y-%m-%d')
        date_from = time.strftime("%d.%m.%Y",date_from)

        date_to = time.strptime(form['date_to'],'%Y-%m-%d')
        date_to = time.strftime("%d.%m.%Y",date_to)

        result = date_from + ' - ' + date_to + ' '

        return str(result and result[:-1]) or ''

    def get_balance_last_year(self, account_id, ctx_last_year, form):
#        ctx['date_from'] = str(start_lastyear)
#        ctx['date_to'] = str(end_lastyear)
        
        #ctx['fiscalyear'] = form['fiscalyear_id']
        fiscalyear_obj = self.pool.get('account.fiscalyear')
        fiscalyear_date_start = fiscalyear_obj.browse(self.cr, self.uid, form['fiscalyear_id'][0], context=ctx_last_year).date_start
        fiscalyear_date_stop = fiscalyear_obj.browse(self.cr, self.uid, form['fiscalyear_id'][0], context=ctx_last_year).date_stop
        start = datetime.date.fromtimestamp(time.mktime(time.strptime(fiscalyear_date_start,"%Y-%m-%d")))
        end = datetime.date.fromtimestamp(time.mktime(time.strptime(fiscalyear_date_stop,"%Y-%m-%d")))
        #fiscalyear_start_lastyear = start+datetime.timedelta(days=-365)
        fiscalyear_start_lastyear = start-relativedelta(years=1)
        #fiscalyear_end_lastyear = end+datetime.timedelta(days=-365)
        fiscalyear_end_lastyear = end-relativedelta(years=1)
        fiscalyear_last_year = fiscalyear_obj.search(self.cr, self.uid, [('date_start', '=', fiscalyear_start_lastyear), ('date_stop', '=', fiscalyear_end_lastyear)])
        if len(fiscalyear_last_year) > 0:
            ctx_last_year['fiscalyear'] = fiscalyear_last_year[0]
            if form['filter'] == 'filter_period':
    #            ctx['period_from'] = form['period_from']
    #            ctx['period_to'] = form['period_to']
                fiscalperiod_obj = self.pool.get('account.period')
                fiscalperiod_from = fiscalperiod_obj.browse(self.cr, self.uid, form['period_from'][0], context=ctx_last_year).date_start
                start = datetime.date.fromtimestamp(time.mktime(time.strptime(fiscalperiod_from,"%Y-%m-%d")))
                #fiscalperiod_start_lastyear = start+datetime.timedelta(days=-365)
                fiscalperiod_start_lastyear = start-relativedelta(years=1)
                fiscalperiod_to = fiscalperiod_obj.browse(self.cr, self.uid, form['period_to'][0], context=ctx_last_year).date_start
                start = datetime.date.fromtimestamp(time.mktime(time.strptime(fiscalperiod_to,"%Y-%m-%d")))
                #fiscalperiod_end_lastyear = start+datetime.timedelta(days=-365)
                fiscalperiod_end_lastyear = start-relativedelta(years=1)
                
                fiscalperiod_start_last_year = fiscalperiod_obj.search(self.cr, self.uid, [('date_start', '=', fiscalperiod_start_lastyear)])
                fiscalperiod_end_last_year = fiscalperiod_obj.search(self.cr, self.uid, [('date_start', '=', fiscalperiod_end_lastyear)])
                if fiscalperiod_start_last_year:
                    ctx_last_year['period_from'] = fiscalperiod_start_last_year[0]
                else:
                    ctx_last_year['period_from'] = False
                if fiscalperiod_end_last_year:
                    ctx_last_year['period_to'] = fiscalperiod_end_last_year[0]
                else:
                    ctx_last_year['period_to'] = False
            elif form['filter'] == 'filter_date':
                start = datetime.date.fromtimestamp(time.mktime(time.strptime(form['date_from'],"%Y-%m-%d")))
                end = datetime.date.fromtimestamp(time.mktime(time.strptime(form['date_to'],"%Y-%m-%d")))
                #start_lastyear = start+datetime.timedelta(days=-365)
                start_lastyear = start-relativedelta(years=1)
                #end_lastyear = end+datetime.timedelta(days=-365)
                end_lastyear = end-relativedelta(years=1)
                ctx_last_year['date_from'] = str(start_lastyear)
                ctx_last_year['date_to'] = str(end_lastyear)
            
            ctx_last_year['state'] = 'posted'
            ctx_last_year['periods'] = False
            accounts = self.pool.get('account.account').read(self.cr, self.uid, account_id,['type','code','name','debit','credit','balance','parent_id'], ctx_last_year)
        
            return accounts['balance']
        return 0
        
    def lines(self, code_report, form, ids={}, done=None, level=1):
        # HACK: 07.08.2013 07:24:25: olivier: if code == 'Bilanz' -> get value from field property_balance_start_account in company configuration
        # HACK: 23.04.2014 13:56:07: olivier: get company_id like this
        company = self.pool.get('res.company').browse(self.cr, self.uid, form['company_id'][0])
        code = code_report
        if code_report == 'Bilanz':
            if company.property_balance_start_account:
                code = company.property_balance_start_account.code
            else:
                raise osv.except_osv(_('Warning!'), _('No balance start account is defined for the company.\nPlease define it in the company (Settings > Companies > Companies, in the configuration tab of your company).'))
        if code_report == 'Aktiven':
            if company.property_balance_actives_account:
                code = company.property_balance_actives_account.code
            else:
                raise osv.except_osv(_('Warning!'), _('No balance actives account is defined for the company.\nPlease define it in the company (Settings > Companies > Companies, in the configuration tab of your company).'))
        if code_report == 'Passiven':
            if company.property_balance_passives_account:
                code = company.property_balance_passives_account.code
            else:
                raise osv.except_osv(_('Warning!'), _('No balance passives account is defined for the company.\nPlease define it in the company (Settings > Companies > Companies, in the configuration tab of your company).'))
        # END HACK
        if not ids:
            ids = self.ids
        if not ids:
            return []
        if not done:
            done={}
        if form.has_key('Account_list') and form['Account_list']:
            ids = [form['Account_list']]
            del form['Account_list']
        ids = self.pool.get('account.account').search(self.cr, self.uid, [('code','=',code)])
        res={}
        result_acc=[]
        result_acc_lastyear=[]
        result = []
        ctx = self.context.copy()
        if ids:
            root_node = ids[0] 
        
            ctx['fiscalyear'] = form['fiscalyear_id'][0]
            # HACK: 07.08.2013 08:33:16: olivier: set periods every time
            pids = []
            pids += map(lambda x: str(x.id), self.pool.get('account.fiscalyear').browse(self.cr, self.uid, form['fiscalyear_id'][0]).period_ids)
            ctx['periods'] = pids
            if form['filter'] == 'filter_period':
                ctx['period_from'] = form['period_from'][0]
                ctx['period_to'] = form['period_to'][0]
                ctx['periods'] = False
            elif form['filter'] == 'filter_date':
                ctx['date_from'] = form['date_from']
                ctx['date_to'] =  form['date_to']
                ctx['periods'] = False
    
    #        start = datetime.date.fromtimestamp(time.mktime(time.strptime(form['date_from'],"%Y-%m-%d")))
    #        end = datetime.date.fromtimestamp(time.mktime(time.strptime(form['date_to'],"%Y-%m-%d")))
    #        start_lastyear = start+datetime.timedelta(days=-365)
    #        end_lastyear = end+datetime.timedelta(days=-365)
    #        ctx['date_from'] = str(start)
    #        ctx['date_to'] = str(end)
            child_ids = False
            #hack jool: if code is B -> BILANZ then print just this line without childs!!!
            code_name = self.pool.get('account.account').browse(self.cr, self.uid, ids)[0].name
            if code_report != 'Bilanz':
                child_ids = self.pool.get('account.account')._get_children_and_consol(self.cr, self.uid, ids, ctx)
                
            if child_ids:
                ids = child_ids
            ctx['state'] = 'posted'

            # HACK: 14.05.2014 15:56:10: olivier: loop over ids and get then the account details for each account, otherwise the order is not correct
            #accounts = self.pool.get('account.account').read(self.cr, self.uid, ids,['type','code','name','debit','credit','balance','parent_id'], ctx)
            #for account in accounts:
            for account_id in ids:
                account = self.pool.get('account.account').read(self.cr, self.uid, account_id,['type','code','name','debit','credit','balance','parent_id'], ctx)

                if account['id'] in done:
                    continue
                done[account['id']] = 1
                
                #hack jool: also check if lastyear balance is != 0 -> then we must print the account also!!!!
                ctx_last_year = ctx.copy()
                get_balance_last_year = self.get_balance_last_year(account['id'], ctx_last_year, form)
                if account['credit'] > 0 or account['debit'] > 0 or get_balance_last_year != 0:
                    res = {
                            'id' : account['id'],
                            'type' : account['type'],
                            'code': account['code'],
                            'name': account['name'],
                            'level': level,
                            'debit': account['debit'],
                            'credit': account['credit'],
                            'balance': account['balance'],
                            'balance_last_year': get_balance_last_year,
                           # 'leef': not bool(account['child_id']),
                            'parent_id':account['parent_id'],
                            'bal_type':'',
                        }
                    self.sum_debit += account['debit']
                    self.sum_credit += account['credit']
                    if account['parent_id']:
                        for r in result_acc:
                            if r['id'] == account['parent_id'][0]:
                                #hack jool: set level depending on len of code
                                #res['level'] = r['level'] + 1
                                res['level'] = len(account['code'])
                                break
                    #hack jool: insert root node at position 0
                    if account['id'] == root_node:
                        result_acc.insert(0, res)
                        #result_acc.append(res)
                    else:
                        result_acc.append(res)
        return result_acc
        
    def _get_lines(self, based_on,period_list,company_id=False, parent=False, level=0):
        res = self._get_codes(based_on,company_id,parent,level,period_list)
       
        if period_list[0][2] :
            res = self._add_codes(based_on,res,period_list)
        else :
            self.cr.execute ("select id from account_fiscalyear")
            fy = self.cr.fetchall()
            for y in fy:
                year = y[0]
                self.cr.execute ("select id from account_period where fiscalyear_id = %d"%(year))
                periods = self.cr.fetchall()
                for p in periods :
                    period_list[0][2].append(p[0])

            res = self._add_codes(based_on,res,period_list)

        i = 0
        top_result = []
        while i < len(res):
            res_dict = { 'code' : res[i][1].code,
                'name' : res[i][1].name,
                'debit' : 0,
                'credit' : 0,
                'tax_amount' : res[i][1].sum_period,
                'type' : 1,
                'level' : res[i][0],
                'pos' : 0,
                'id' : res[i][1].id,
            }
            
            top_result.append(res_dict)
            res_general = self._get_general(res[i][1].id,period_list,company_id,based_on)
            ind_general = 0
            while ind_general < len(res_general) :
                res_general[ind_general]['type'] = 2
                res_general[ind_general]['pos'] = 0
                res_general[ind_general]['level'] = res_dict['level']
                top_result.append(res_general[ind_general])
                ind_general+=1
            i+=1
        #array_result = self.sort_result(top_result)
        return top_result
        #return array_result

    def _get_period(self, period_id):
        return self.pool.get('account.period').browse(self.cr, self.uid, period_id).name

    def _get_general(self, tax_code_id,period_list ,company_id, based_on):
        res=[]
        periods_ids = tuple(period_list[0][2])
        if based_on == 'payments':
            self.cr.execute('SELECT SUM(line.tax_amount) AS tax_amount, \
                        SUM(line.debit) AS debit, \
                        SUM(line.credit) AS credit, \
                        COUNT(*) AS count, \
                        account.id AS account_id, \
                        account.name AS name,  \
                        account.code AS code \
                    FROM account_move_line AS line, \
                        account_account AS account, \
                        account_move AS move \
                        LEFT JOIN account_invoice invoice ON \
                            (invoice.move_id = move.id) \
                    WHERE line.state<>%s \
                        AND line.tax_code_id = %s  \
                        AND line.account_id = account.id \
                        AND account.company_id = %s \
                        AND move.id = line.move_id \
                        AND line.period_id IN %s \
                        AND ((invoice.state = %s) \
                            OR (invoice.id IS NULL))  \
                    GROUP BY account.id,account.name,account.code',
                        ('draft',tax_code_id,company_id,periods_ids,'paid'))

        else :
            self.cr.execute('SELECT SUM(line.tax_amount) AS tax_amount, \
                        SUM(line.debit) AS debit, \
                        SUM(line.credit) AS credit, \
                        COUNT(*) AS count, \
                        account.id AS account_id, \
                        account.name AS name,  \
                        account.code AS code \
                    FROM account_move_line AS line, \
                        account_account AS account \
                    WHERE line.state <> %s \
                        AND line.tax_code_id = %s  \
                        AND line.account_id = account.id \
                        AND account.company_id = %s \
                        AND line.period_id IN %s \
                        AND account.active \
                    GROUP BY account.id,account.name,account.code',
                        ('draft',tax_code_id,company_id,periods_ids))
        res = self.cr.dictfetchall()
        
                        #AND line.period_id IN ('+ period_sql_list +') \
        
        i = 0
        while i<len(res):
            res[i]['account'] = self.pool.get('account.account').browse(self.cr, self.uid, res[i]['account_id'])
            i+=1
        return res

    def _get_codes(self,based_on, company_id, parent=False, level=0,period_list=[]):
        tc = self.pool.get('account.tax.code')
        ids = tc.search(self.cr, self.uid, [('parent_id','=',parent),('company_id','=',company_id)])
        
        res = []
        for code in tc.browse(self.cr, self.uid, ids, {'based_on': based_on}):
            res.append(('.'*2*level,code))

            res += self._get_codes(based_on, company_id, code.id, level+1)
        return res

    def _add_codes(self,based_on, account_list=[],period_list=[]):
        res = []
        for account in account_list:
            tc = self.pool.get('account.tax.code')
            ids = tc.search(self.cr, self.uid, [('id','=',account[1].id)])
            sum_tax_add = 0
            for period_ind in period_list[0][2]:
                for code in tc.browse(self.cr, self.uid, ids, {'period_id':period_ind,'based_on': based_on}):
                    sum_tax_add = sum_tax_add + code.sum_period
                    
            code.sum_period = sum_tax_add
            
            res.append((account[0],code))
        return res

    
    def _get_company(self, form):
        return pooler.get_pool(self.cr.dbname).get('res.company').browse(self.cr, self.uid, form['company_id']).name

    def _get_currency(self, form):
        return pooler.get_pool(self.cr.dbname).get('res.company').browse(self.cr, self.uid, form['company_id']).currency_id.name
    
    def sort_result(self,accounts):
        # On boucle sur notre rapport
        result_accounts = []
        ind=0
        old_level=0
        while ind<len(accounts):
            #
            account_elem = accounts[ind]
            #
            
            #
            # we will now check if the level is lower than the previous level, in this case we will make a subtotal
            if (account_elem['level'] < old_level):
                bcl_current_level = old_level
                bcl_rup_ind = ind - 1
                
                while (bcl_current_level >= int(accounts[bcl_rup_ind]['level']) and bcl_rup_ind >= 0 ):
                    tot_elem = copy.copy(accounts[bcl_rup_ind])
                    res_tot = { 'code' : accounts[bcl_rup_ind]['code'],
                        'name' : '',
                        'debit' : 0,
                        'credit' : 0,
                        'tax_amount' : accounts[bcl_rup_ind]['tax_amount'],
                        'type' : accounts[bcl_rup_ind]['type'],
                        'level' : 0,
                        'pos' : 0
                    }
                    
                    if res_tot['type'] == 1:
                        # on change le type pour afficher le total
                        res_tot['type'] = 2
                        result_accounts.append(res_tot)
                    bcl_current_level =  accounts[bcl_rup_ind]['level']
                    bcl_rup_ind -= 1
                    
            old_level = account_elem['level']
            result_accounts.append(account_elem)
            ind+=1
            
                
        return result_accounts
    
    def _calculate_change_in_percent(self, balance_actual_year, balance_last_year):
        if abs(balance_actual_year) < 0.01:
            balance_actual_year = 0
        if abs(balance_last_year) < 0.01:
            balance_last_year = 0
        if balance_actual_year == 0 and balance_last_year == 0:
            return 0
        if balance_last_year == 0:
            return 0
        res = ((balance_actual_year-balance_last_year)/abs(balance_last_year))*100
        if abs(res) < 0.01:
            return 0
        return res

report_sxw.report_sxw('report.account.indicator.cust', 'account.account',
    'addons/bt_indicator/report/indicator_report.rml', parser=indicator_report, header=False)

report_sxw.report_sxw('report.account.indicator.cust.bilanz', 'account.account',
    'addons/bt_indicator/report/indicator_report_bilanz.rml', parser=indicator_report, header=False)

report_sxw.report_sxw('report.account.indicator.cust.er', 'account.account',
    'addons/bt_indicator/report/indicator_report_er.rml', parser=indicator_report, header=False)

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
