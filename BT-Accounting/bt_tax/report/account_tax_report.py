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

import time

from common_report_header import common_report_header
from report import report_sxw
import netsvc 
import pooler


class tax_report(report_sxw.rml_parse, common_report_header):
    _name = 'report.account.vat.declaration.cust'

    def _record_to_report_line(self, record):
        if record.move_id.state != 'posted':
            return {'res': False, 
                  'account_codes': '', 
                  'amount_new': 0,
                  'amount_new_currency': 0,
                  'text_move': '', 
                  'tax_amount_new': 0,
                  'tax_amount_new_currency': 0, 
                  } 
#        if record.move_id.id == 8140:
#            print 'record: ', record
#            print 'record.debit: ', record.debit
#            print 'record.credit: ', record.credit
        if record.debit > 0:
            amount_new = record.debit*-1
            amount_new_currency = abs(record.amount_currency)*-1
        else:
            amount_new = record.credit
            amount_new_currency = abs(record.amount_currency)
        
        tax_amount = 0
        self.cr.execute("select debit-credit as sum, amount_currency, account_id, tax_amount from account_move_line \
                        where tax_code_id in (select distinct base_code_id from account_tax \
                        where tax_code_id = (select tax_code_id from account_move_line where id = %s) and base_code_id is not null) \
                        and move_id = %s "%(record.id, record.move_id.id))
        
        get_tax_amount_total_move = self.cr.dictfetchall()
#        if record.move_id.id == 8140:
#            print ("select debit-credit as sum, amount_currency, account_id, tax_amount from account_move_line \
#                        where tax_code_id = (select base_code_id from account_tax \
#                        where tax_code_id = (select tax_code_id from account_move_line where id = %s)) \
#                        and move_id = %s "%(record.id, record.move_id.id)) 
#            print 'get_tax_amount_total_move1: ', get_tax_amount_total_move            
        if not get_tax_amount_total_move:
            self.cr.execute("select debit-credit as sum, amount_currency, account_id, tax_amount from account_move_line \
                        where tax_code_id in (select distinct tax_code_id from account_tax \
                        where base_code_id = (select tax_code_id from account_move_line where id = %s) and tax_code_id is not null) \
                        and move_id = %s "%(record.id, record.move_id.id))
            get_tax_amount_total_move = self.cr.dictfetchall()
        
        
#        if record.move_id.id == 8140:
#            print 'get_tax_amount_total_move2: ', get_tax_amount_total_move
            
        tax_amount = abs(record.tax_amount_base)
        amount_new_currency = 0
        obj_account = self.pool.get('account.account')
        codes = []
        codes_string = ''
#         total_tax_amount_all_lines_count = 0
        if get_tax_amount_total_move:
            sum = 0
            sum_currency = 0
            for line in get_tax_amount_total_move:
                #split it according to the tax_amount of all records in the same move_id and the same tax_code_id
                
                #set total tax_amount of all lines with same move_id and tax_code_id
                self.cr.execute("select sum(tax_amount), count(*) from account_move_line \
                            where move_id = %s \
                            and tax_code_id = %s "%(record.move_id.id, record.tax_code_id.id))
                result_sum_count = self.cr.fetchone()
                total_tax_amount_all_lines = result_sum_count[0] or 0.0
                total_tax_amount_all_lines_count = result_sum_count[1] or 0
                
                percentage_of_line = 100
                if total_tax_amount_all_lines:
                    percentage_of_line = 100 / total_tax_amount_all_lines * record.tax_amount
                
                #sum += line['sum']
                sum += line['sum'] / 100 * percentage_of_line
                amount_currency = 0
                if line['amount_currency']:
                    #amount_currency = line['amount_currency']
                    amount_currency = line['amount_currency'] / 100 * percentage_of_line
                sum_currency += amount_currency
                
                code = record.account_id.code
                if code not in codes:
                    codes.append(code)

            tax_amount = sum
            amount_new_currency = sum_currency
        else:
            code = record.account_id.code
            if code not in codes:
                codes.append(code)
            
        codes_string = ",".join(codes)
        tax_amount_new = abs(record.tax_amount)
        tax_amount_base = record.tax_amount_base
        
#        if record.move_id.id == 8140:
#            print 'DIFF: ', abs(abs(tax_amount)-abs(tax_amount_base))
        #if abs(abs(tax_amount)-abs(tax_amount_base)) < 0.02:
        tax_amount_base = tax_amount
            
        #set tax_amount_base == tax_mount when tax_amount_base is not set in record
        if record.tax_amount_base == 0:
            tax_amount_base = tax_amount
            
#        if record.move_id.id == 8140:
#            print 'tax_amount_base: ', tax_amount_base
#            print 'tax_amount > 0: ', tax_amount
        if tax_amount > 0:
            amount_new = abs(tax_amount_base)*-1
            amount_new_currency = abs(amount_new_currency)*-1
            tax_amount_new = tax_amount_new *-1
        elif tax_amount < 0:
            amount_new = abs(tax_amount_base)
            amount_new_currency = abs(amount_new_currency)
            tax_amount_new = tax_amount_new
        else:
            if amount_new < 0:
                tax_amount_new = abs(tax_amount_new)*-1
            elif amount_new > 0:
                tax_amount_new = abs(tax_amount_new)
            
#        if record.move_id.id == 8140:
#            print 'amount_new: ', amount_new

        tax_amount_new_currency = abs(record.amount_currency)
        if amount_new_currency < 0:
            tax_amount_new_currency = abs(tax_amount_new_currency)*-1

        amount_new = round(amount_new/0.01)*0.01
        amount_new_currency = round(amount_new_currency/0.01)*0.01
        tax_amount_new = round(tax_amount_new/0.01)*0.01
        tax_amount_new_currency = round(tax_amount_new_currency/0.01)*0.01

        if get_tax_amount_total_move:
            tax_amount_total_move = get_tax_amount_total_move and get_tax_amount_total_move[0]['tax_amount'] or 0.0
            if record.move_id.id not in self.move_ids_used_dict_per_tax:
                self.move_ids_used_dict_per_tax[record.move_id.id] = {
                                                              'total': get_tax_amount_total_move and get_tax_amount_total_move[0]['tax_amount'] or 0.0,
                                                              'total_used': amount_new,
                                                              'total_lines': total_tax_amount_all_lines_count,
                                                              'total_lines_used': 1
                                                              }
                if tax_amount_total_move == 0:
                    amount_new = 0
            else:
                #check if new total sum is > total_used
                self.move_ids_used_dict_per_tax[record.move_id.id]['total_lines_used'] += 1
                amount_new_temp = self.move_ids_used_dict_per_tax[record.move_id.id]['total_used'] + amount_new
                if abs(amount_new_temp - tax_amount_total_move) >= 0.0001 and self.move_ids_used_dict_per_tax[record.move_id.id]['total_lines_used'] == total_tax_amount_all_lines_count:
                    # then set sum to the difference remaining
                    amount_new = amount_new_temp - self.move_ids_used_dict_per_tax[record.move_id.id]['total_used']
                self.move_ids_used_dict_per_tax[record.move_id.id]['total_used'] += amount_new
                if tax_amount_total_move == 0:
                    amount_new = 0
        else:
            amount_new = 0

        return {'res': record, 
                  'account_codes': codes_string, 
                  'amount_new': amount_new,
                  'amount_new_currency': amount_new_currency,
                  'text_move': record.ref, 
                  'tax_amount_new': tax_amount_new,
                  'tax_amount_new_currency': tax_amount_new_currency, 
                  } 
    
    def set_context(self, objects, data, ids, report_type=None):
        new_ids = ids
        res = {}
        period_ids = []
        self.period_ids = []
        period_obj = self.pool.get('account.period')
        res['periods'] = ''
        self.fiscalyear = data['form'].get('fiscalyear_id', False)
        res['fiscalyear'] = self.fiscalyear

        if data['form'].get('period_from', False) and data['form'].get('period_to', False):
            self.period_ids = period_obj.build_ctx_periods(self.cr, self.uid, data['form']['period_from'], data['form']['period_to'])
            periods_l = period_obj.read(self.cr, self.uid, self.period_ids, ['name'])
            for period in periods_l:
                if res['periods'] == '':
                    res['periods'] = period['name']
                else:
                    res['periods'] += ", "+ period['name']
        return super(tax_report, self).set_context(objects, data, new_ids, report_type=report_type)

    def __init__(self, cr, uid, name, context=None):
        if context is None:
            context = {}
        super(tax_report, self).__init__(cr, uid, name, context=context)
        self.localcontext.update({
            'time': time,
            'get_codes': self._get_codes,
            'get_general': self._get_general,
            'get_currency': self._get_currency,
            'get_lines': self._get_lines,
            'get_fiscalyear': self._get_fiscalyear,
            'get_account': self._get_account,
            'get_start_period': self.get_start_period,
            'get_end_period': self.get_end_period,
            'get_basedon': self._get_basedon,
            #'get_tax_lines':self._get_tax_lines,
            'get_tax_lines_new': self._get_tax_lines_new,
            '_record_to_report_line': self._record_to_report_line,
        })
        self.context = context

    def _get_basedon(self, form):
        return form['form']['based_on']

    def _get_lines(self, based_on, company_id=False, is_detail=False, parent=False, level=0):
        period_list = self.period_ids
        res = self._get_codes(based_on, company_id, parent, level, period_list)
        if period_list:
            res = self._add_codes(based_on, res, period_list, is_detail)
        else:
            self.cr.execute ("select id from account_period where fiscalyear_id = %s",(self.fiscalyear,))
            periods = self.cr.fetchall()
            for p in periods:
                period_list.append(p[0])
            res = self._add_codes(based_on, res, period_list, is_detail)

        i = 0
        top_result = []
        while i < len(res):
            lines = self._get_tax_lines_new(based_on,res[i][1].id)
            res_dict = { 
                'code': res[i][1].code,
                'name': res[i][1].name,
                'debit': 0,
                'credit': 0,
                'tax_amount': res[i][1].sum_period,
                'type': 1,
                'level': res[i][0],
                'pos': 0,
                'id' : res[i][1].id,
                'bold': 1,
            }

            if is_detail:
                if len(lines) > 0:
                    top_result.append(res_dict)
            else:
                #hack jool: just add if res[i][1].child_ids or res[i][1].line_ids               
                if res[i][1].child_ids or res[i][1].line_ids:
                    top_result.append(res_dict)
                
            res_general = self._get_general(res[i][1].id, period_list, company_id, based_on)
            ind_general = 0
            while ind_general < len(res_general):
                res_general[ind_general]['type'] = 2
                res_general[ind_general]['pos'] = 0
                res_general[ind_general]['level'] = res_dict['level'] + '....'
                res_general[ind_general]['bold']= 0
                top_result.append(res_general[ind_general])
                ind_general+=1
            i+=1
        return top_result

    def _get_general(self, tax_code_id, period_list, company_id, based_on):
        res = []
        obj_account = self.pool.get('account.account')
        periods_ids = tuple(period_list)
        if based_on == 'payments':
            #self.cr.execute('SELECT SUM(line.tax_amount) AS tax_amount, \
            self.cr.execute('SELECT SUM(line.debit - line.credit) AS tax_amount, \
                        SUM(line.debit) AS debit, \
                        SUM(line.credit) AS credit, \
                        COUNT(*) AS count, \
                        account.id AS account_id, \
                        account.name AS name,  \
                        account.code AS code \
                    FROM account_move_line AS line, \
                        account_account AS account, \
                        account_move AS move \
                        RIGHT JOIN account_tax_code AS tax_code_table ON \
                            (tax_code_table.id = line.tax_code_id) \
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
                    GROUP BY account.id,account.name,account.code ORDER BY account.code', ('draft', tax_code_id,
                        company_id, periods_ids, 'paid',))

        else:
            #self.cr.execute('SELECT SUM(line.tax_amount) AS tax_amount, \
            self.cr.execute('SELECT SUM(line.debit - line.credit) AS tax_amount, \
                        SUM(line.debit) AS debit, \
                        SUM(line.credit) AS credit, \
                        COUNT(*) AS count, \
                        account.id AS account_id, \
                        account.name AS name,  \
                        account.code AS code \
                    FROM account_move_line AS line, \
                        account_account AS account, \
                        account_tax_code AS tax_code_table \
                    WHERE line.state <> %s \
                        AND tax_code_table.id = line.tax_code_id \
                        AND line.tax_code_id = %s  \
                        AND line.account_id = account.id \
                        AND account.company_id = %s \
                        AND line.period_id IN %s\
                        AND account.active \
                    GROUP BY account.id,account.name,account.code ORDER BY account.code', ('draft', tax_code_id,
                        company_id, periods_ids,))
        res = self.cr.dictfetchall()
        
        i = 0
        while i<len(res):
            res[i]['account'] = obj_account.browse(self.cr, self.uid, res[i]['account_id'], context=self.context)
            i+=1
        return res

    def _get_codes(self, based_on, company_id, parent=False, level=0, period_list=[]):
        obj_tc = self.pool.get('account.tax.code')
        ids = obj_tc.search(self.cr, self.uid, [('parent_id','=',parent),('company_id','=',company_id)], order='sequence', context=self.context)

        res = []
        ctx = self.context.copy()
        ctx['based_on'] = based_on
        for code in obj_tc.browse(self.cr, self.uid, ids, context=ctx):
            res.append(('.'*2*level, code))

            res += self._get_codes(based_on, company_id, code.id, level+1)
        return res

    def _add_codes(self, based_on, account_list=[], period_list=[], is_detail=False):
        res = []
        obj_tc = self.pool.get('account.tax.code')
        ctx = self.context.copy()
        ctx['based_on'] = based_on
        for account in account_list:
            # hack jool1 - fibu
            if is_detail:
                if account[1].show_in_tax_journal:
                    ids = obj_tc.search(self.cr, self.uid, [('id','=',account[1].id)], context=self.context)
                    sum_tax_add = 0
                    for period_id in period_list:
                        ctx['period_id'] = period_id
                        for code in obj_tc.browse(self.cr, self.uid, ids, context=ctx):
                            sum_tax_add = sum_tax_add + code.sum_period
                           
                    code.sum_period = sum_tax_add
                    res.append((account[0],code))
            else: 
                ids = obj_tc.search(self.cr, self.uid, [('id','=', account[1].id)], context=self.context)
                sum_tax_add = 0
                for period_id in period_list:
                    ctx['period_id'] = period_id
                    for code in obj_tc.browse(self.cr, self.uid, ids, context=ctx):
                        sum_tax_add = sum_tax_add + code.sum_period

                code.sum_period = sum_tax_add
                res.append((account[0], code))
        return res

    def _get_currency(self, form):
        return self.pool.get('res.company').browse(self.cr, self.uid, form['company_id'], context=self.context).currency_id.name

    def _get_tax_lines_new(self, based_on, tax_code):
        period_list = self.period_ids
        periods_ids = tuple(period_list)
        line_ids = self.pool.get('account.move.line').search(self.cr, self.uid, [('tax_code_id','=',tax_code),('period_id','in',periods_ids)], order='date, move_id, account_id')
        if not line_ids: return []
        self.move_ids_used_dict_per_tax = {}
        return map(self._record_to_report_line, self.pool.get('account.move.line').browse(self.cr, self.uid, line_ids, context=self.context))

report_sxw.report_sxw('report.account.vat.declaration.cust', 'account.tax.code',
    'addons/bt_tax/report/account_tax_report.rml', parser=tax_report, header="internal")

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
