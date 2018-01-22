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

import pooler
import time
import re
import rml_parse
import datetime
from report import report_sxw
import netsvc
from operator import itemgetter
import operator

from bt_helper.log_rotate import get_log
logger = get_log('NOTSET')
# logger = get_log('DEBUG')

# logger.info("This message is info")
# logger.debug("This message is info")
# logger.critical("This message is info")
# logger.warning("This message is info")
# logger.error("This message is info")

# logger.debug("Value: %s", value)
# logger.debug("Values: %s %s %s" % (value1, value2, value3))



#from common_report_header import common_report_header

#class oplist_report(report_sxw.rml_parse, common_report_header):
class oplist_report(report_sxw.rml_parse):
    _name = 'report.account.oplist.cust'
    
    def set_context(self, objects, data, ids, report_type=None):
        new_ids = ids
        PARTNER_REQUEST = ''
        if data['form']['partner_id']:
            #print 'set_context data: ', data
            #print data['form']['partner_id']
            self.partner_id_where = "AND i.partner_id = " + str(data['form']['partner_id'][0])
        if (data['model'] == 'res.partner'):
            ## Si on imprime depuis les partenaires
            if ids:
                PARTNER_REQUEST = "AND line.partner_id IN (" + ','.join(map(str, ids)) + ")"
        # Transformation des date
        self.transform_date_into_date_array(data)
        self.transform_date_into_period_range_array(data)
        
        if data['form']['filter_on_periods']:
            self.date_or_period_where = " AND i.period_id IN (" + ','.join(map(str, self.period_lst_all)) + ") "
            self.date_or_period_where_manual_entries = " AND i.period_id IN (" + ','.join(map(str, self.period_lst)) + ") "
        else:
            self.date_or_period_where = " AND i.date_invoice <= '" + self.date_lst[len(self.date_lst) - 1] + "' "
            # HACK: 20.03.2015 12:00:47: jool1: check all entries <= date_lst
            #self.date_or_period_where_manual_entries = " AND i.date >= '" + self.date_lst[0] + "' AND i.date <= '" + self.date_lst[len(self.date_lst) - 1] + "' "
            self.date_or_period_where_manual_entries = " AND i.date <= '" + self.date_lst[len(self.date_lst) - 1] + "' "
        
        self.date_set = ''
        if data['form']['date2']:
            self.date_set = data['form']['date2']
        
        self.date_lst_string = ''
        if self.date_lst:
            self.date_lst_string = '\'' + '\',\''.join(map(str, self.date_lst)) + '\''
                
        if data['form']['result_selection'] == 'supplier':
            self.ACCOUNT_TYPE = "('payable')"
        elif data['form']['result_selection'] == 'customer':
            self.ACCOUNT_TYPE = "('receivable')"
        elif data['form']['result_selection'] == 'customer_supplier':
            self.ACCOUNT_TYPE = "('payable','receivable')"
        self.cr.execute(
            "SELECT distinct a.id, a.code " \
            "FROM account_account a " \
            "LEFT JOIN account_account_type t " \
                "ON (a.type=t.code) " \
            "WHERE a.company_id = %s " \
                "AND a.type IN " + self.ACCOUNT_TYPE + " " \
                "AND a.active " \
                "ORDER BY a.code, a.id", (data['form']['company_id'],))
        self.account_ids = ','.join([str(a) for (a, b) in self.cr.fetchall()])
        self.cr.execute(
            "SELECT distinct a.id, a.code " \
            "FROM account_account a " \
            "LEFT JOIN account_account_type t " \
                "ON (a.type=t.code) " \
            "WHERE a.company_id = %s " \
                "AND a.type IN " + self.ACCOUNT_TYPE + " " \
                "AND a.active " \
                "ORDER BY a.code, a.id", (data['form']['company_id'],))
        self.account_ids_list = self.cr.dictfetchall()
        return super(oplist_report, self).set_context(objects, data, new_ids, report_type=report_type)
    
    def __init__(self, cr, uid, name, context):
        super(oplist_report, self).__init__(cr, uid, name, context=context)
        self.data_invoices = []
        self.account_ids_list = []
        self.date_lst = []
        self.period_lst = []
        self.period_lst_all = []
        self.date_lst_string = ''
        self.date_set = ''
        self.total_sum_debit = 0
        self.total_sum_credit = 0
        self.total_sum_currency = 0
        self.last_account_sum_computed = ''
        self.partner_id_where = ''
        self.ACCOUNT_TYPE = "('payable')"
        self.localcontext.update({
            'time': time,
            'lines': self.lines,
            'get_sum_debit': self._get_sum_debit,
            'get_sum_credit': self._get_sum_credit,
            'get_sum_currency': self._get_sum_currency,
            'get_company': self._get_company,
            'get_currency': self._get_currency,
            'comma_me': self.comma_me,
            'get_date': self._get_date,
            'get_partners': self.get_partners,
            'get_accounts': self.get_accounts,
            'get_account_lines': self.get_account_lines,
            'get_sum_account_debit': self._get_sum_account_debit,
            'get_sum_account_credit': self._get_sum_account_credit,
            'get_sum_account_currency': self._get_sum_account_currency,
            'get_account_info': self.get_account_info,
        })
        self.context = context

    def _get_date(self, form):
        date_to = time.strptime(form['date2'], '%Y-%m-%d')
        date_to = time.strftime("%d.%m.%Y", date_to)
        
        result = date_to + ' '
        return str(result and result[:-1]) or ''
            
    def date_range(self, start, end):
        if not start or not end:
            return []
        start = datetime.date.fromtimestamp(time.mktime(time.strptime(start, "%Y-%m-%d")))
        end = datetime.date.fromtimestamp(time.mktime(time.strptime(end, "%Y-%m-%d")))
        full_str_date = []

        r = (end + datetime.timedelta(days=1) - start).days

        date_array = [start + datetime.timedelta(days=i) for i in range(r)]
        for date in date_array:
            full_str_date.append(str(date))
        return full_str_date

    def transform_date_into_date_array(self, data):
        self.cr.execute(
                "select f.date_start from account_fiscalyear f " \
                "WHERE %s >= f.date_start " \
                    "AND %s <= f.date_stop ",
                (data['form']['date2'], data['form']['date2']))
        res = map(itemgetter(0), self.cr.fetchall())
        if res: 
            return_array = self.date_range(res[0], data['form']['date2'])
            self.date_lst = return_array
            self.date_lst.sort()

    def transform_date_into_period_range_array(self, data):
        #get date from and date to of fiscalyear
        self.cr.execute(
                "select f.date_start from account_fiscalyear f " \
                "WHERE %s >= f.date_start " \
                    "AND %s <= f.date_stop ",
                (data['form']['date2'], data['form']['date2']))
        res_fiscalyear = map(itemgetter(0), self.cr.fetchall())
        if res_fiscalyear:
            #get periods in range of date_from and date to
            self.cr.execute(
                    "select id from account_period f " \
                    "WHERE date_start >= %s " \
                        "AND date_stop <= %s ",
                    (res_fiscalyear[0], data['form']['date2']))
            res = map(itemgetter(0), self.cr.fetchall())
            self.period_lst = res
            
            #get periods in range of date to
            self.cr.execute(
                    "select id from account_period f " \
                    "WHERE date_stop <= %s ",
                    (data['form']['date2'],))
            res = map(itemgetter(0), self.cr.fetchall())
            self.period_lst_all = res
        
    def comma_me(self, amount):
        if type(amount) is float:
            amount = str('%.2f' % amount)
        else:
            amount = str(amount)
        if (amount == '0'):
            return ' '
        orig = amount
        new = re.sub("^(-?\d+)(\d{3})", "\g<1>'\g<2>", amount)
        if orig == new:
            return new
        else:
            return self.comma_me(new)
    
    def special_map(self):
        string_map = ''
        for date_string in self.date_lst:
            string_map = date_string + ','
        return string_map

    def get_partners(self, account):
        #self.get_account_lines(str(account['id']))
        partner_list = []
        for r in self.data_invoices:
            #hack jool1: only print partner if balance != 0
            if (r['SumCredit'] - r['SumDebit']) != 0:
#                 print 'r[Partner]: ',r['Partner']
#                 print 'r[Partner_id]: ',r['Partner_id']
                if not r['Partner']:
                    #get name from parent_id
                    parent_partner_id = self.pool.get('res.partner').browse(self.cr, self.uid, int(r['Partner_id'])).parent_id
                    if parent_partner_id:
                        r['Partner'] = pooler.get_pool(self.cr.dbname).get('res.partner').browse(self.cr, self.uid, parent_partner_id.id).name
                    else:
                        r['Partner'] = 'Unbekannt'
                partner_list.append(r)
        #sort list -> upper 'Partner'
        partner_list = sorted(partner_list, key=lambda k: k['Partner'].upper())
        #move zzzzzz "Buchung ohne Partner" to the end
        name_indexer = dict((p['Partner'], i) for i, p in enumerate(partner_list))
        entry_without_partner_index = name_indexer.get('zzzzzz', -1)
        if entry_without_partner_index >= 0:
            partner_list.insert(len(partner_list) - 1, partner_list.pop(entry_without_partner_index))
            
        return partner_list
    
    def get_accounts(self):
        account_list = []
        for a in self.account_ids_list:
            account_list.append(a)
        return account_list
        
    def get_account_info(self, account):
        account = self.pool.get('account.account').browse(self.cr, self.uid, account['id'], context=self.context)
        return account.code + ' ' + account.name
    
    def get_account_lines(self, account_id):
        query1 = (
                "select account_id, move_id, sort_name, id, type, sum(amount_total) as amount_total, create_date, number, name, journal_code, " \
                "sum(sum_debit) as sum_debit, sum(sum_credit) as sum_credit, partner_id, lang, partner_name, sum(amount_currency) as amount_currency, date_invoice " \
                "from ( " \
                "SELECT l.account_id, i.move_id, upper(p.name) as sort_name, i.id, i.type, (case when l.debit > 0 then l.debit else l.credit end) as amount_total, to_char(i.date_invoice, 'dd.mm.yyyy') as create_date, i.number, l.name, j.code as journal_code, " \
                        "0 as sum_debit, 0 as sum_credit, i.partner_id, p.lang, p.ref || ' - ' || p.name as partner_name, (case when l.currency_id is not null then l.amount_currency else 0.0 end) as amount_currency, i.date_invoice " \
                "FROM account_invoice i " \
                "JOIN res_partner p on p.id = i.partner_id " \
                "JOIN account_journal j on j.id = i.journal_id " \
                "JOIN account_move_line l on l.move_id = i.move_id " \
                "WHERE i.state in ('open','paid') " \
                    "AND i.account_id IN (" + str(account_id) + ") " \
                    "AND l.account_id IN (" + str(account_id) + ") " \
                    + str(self.date_or_period_where) + str(self.partner_id_where).replace('i.partner_id', 'l.partner_id') + " ) as a " \
                    "group by move_id, account_id, move_id, sort_name, id, type, create_date, number, name, " \
                    "journal_code, partner_id, lang, partner_name, date_invoice " \
                    "ORDER BY sort_name, date_invoice, number ")
        logger.debug("Query1: %s", query1)
        
        # get all invoices
        self.cr.execute(
                "SELECT l.account_id, i.move_id, upper(p.name) as sort_name, i.id, i.type, (case when l.debit > 0 then l.debit else l.credit end) as amount_total, to_char(i.date_invoice, 'dd.mm.yyyy') as create_date, i.number, l.name, j.code as journal_code, " \
                        "0 as sum_debit, 0 as sum_credit, i.partner_id, p.lang, p.ref || ' - ' || p.name as partner_name, (case when l.currency_id is not null then l.amount_currency else 0.0 end) as amount_currency, i.date_invoice " \
                "FROM account_invoice i " \
                "JOIN res_partner p on p.id = i.partner_id " \
                "JOIN account_journal j on j.id = i.journal_id " \
                "JOIN account_move_line l on l.move_id = i.move_id " \
                "WHERE i.state in ('open','paid') " \
                    "AND i.account_id IN (" + str(account_id) + ") " \
                    "AND l.account_id IN (" + str(account_id) + ") " \
                    + str(self.date_or_period_where) + str(self.partner_id_where).replace('i.partner_id', 'l.partner_id') + " " \
                    "ORDER BY sort_name, i.date_invoice, i.number ")
#"AND i.partner_id =  2332" \
        res_invoices = self.cr.dictfetchall()
        #group the invoices by move_id if invoices > 0
        if res_invoices:
            self.cr.execute(
                "select account_id, move_id, sort_name, id, type, sum(amount_total) as amount_total, create_date, number, name, journal_code, " \
                "sum(sum_debit) as sum_debit, sum(sum_credit) as sum_credit, partner_id, lang, partner_name, sum(amount_currency) as amount_currency, date_invoice " \
                "from ( " \
                "SELECT l.account_id, i.move_id, upper(p.name) as sort_name, i.id, i.type, (case when l.debit > 0 then l.debit else l.credit end) as amount_total, to_char(i.date_invoice, 'dd.mm.yyyy') as create_date, i.number, l.name, j.code as journal_code, " \
                        "0 as sum_debit, 0 as sum_credit, i.partner_id, p.lang, p.ref || ' - ' || p.name as partner_name, (case when l.currency_id is not null then l.amount_currency else 0.0 end) as amount_currency, i.date_invoice " \
                "FROM account_invoice i " \
                "JOIN res_partner p on p.id = i.partner_id " \
                "JOIN account_journal j on j.id = i.journal_id " \
                "JOIN account_move_line l on l.move_id = i.move_id " \
                "WHERE i.state in ('open','paid') " \
                    "AND i.account_id IN (" + str(account_id) + ") " \
                    "AND l.account_id IN (" + str(account_id) + ") " \
                    + str(self.date_or_period_where) + str(self.partner_id_where).replace('i.partner_id', 'l.partner_id') + " ) as a " \
                    "group by move_id, account_id, move_id, sort_name, id, type, create_date, number, name, " \
                    "journal_code, partner_id, lang, partner_name, date_invoice " \
                    "ORDER BY sort_name, date_invoice, number ")
                
            res_invoices = self.cr.dictfetchall()
        #netsvc.Logger().notifyChannel('res_invoices',netsvc.LOG_INFO, res_invoices)
        #temp dictionary to add every partner who should be shown
        temp_dict_partner = []
        #get all move_ids from invoices
        res_move_ids_invoices = []
        res_move_line_ids_invoices = []
        for invoice in res_invoices:
          #if invoice['number'] == '1005/5125':
            #add move_id of invoices
            res_move_ids_invoices.append(invoice['move_id'])
            #flag if invoice is open
            res_invoices_open = True
            #get payment line of the invoice
            payment_lines = self.get_payment_lines(self.cr, self.uid, [invoice['id']])
            #netsvc.Logger().notifyChannel('payment_lines',netsvc.LOG_INFO, payment_lines)
            #paid invoices
            if payment_lines:
                #add move_id of payments
                move_ids = self.move_id_get(self.cr, self.uid, payment_lines)
                #netsvc.Logger().notifyChannel('payment_lines_move_ids',netsvc.LOG_INFO, move_ids)
                # HACK: 02.05.2014 15:26:53: olivier: add move_line_id instead of move_id
                for payment_line in payment_lines:
                    res_move_line_ids_invoices.append(payment_line)
                    
                sum_debit = round(self.payment_lines_get_total_amount_debit(self.cr, self.uid, payment_lines), 2)
                sum_credit = round(self.payment_lines_get_total_amount_credit(self.cr, self.uid, payment_lines), 2)
                #netsvc.Logger().notifyChannel('payment_lines',netsvc.LOG_INFO, payment_lines)
                amount_currency_balace = round(self.payment_lines_get_total_amount_currency(self.cr, self.uid, payment_lines), 2)
                #netsvc.Logger().notifyChannel('invoice',netsvc.LOG_INFO, invoice)
                #netsvc.Logger().notifyChannel('amount_currency_balace',netsvc.LOG_INFO, amount_currency_balace)
                #netsvc.Logger().notifyChannel('sum_debit',netsvc.LOG_INFO, sum_debit)
                #netsvc.Logger().notifyChannel('sum_credit',netsvc.LOG_INFO, sum_credit)
                #netsvc.Logger().notifyChannel('invoice[amount_total]',netsvc.LOG_INFO, invoice['amount_total'])
                if invoice['amount_total'] == sum_debit or invoice['amount_total'] == sum_credit or (sum_debit - sum_credit) == invoice['amount_total']:
                    res_invoices_open = False
                else:
                    #set debit and credit
                    if sum_credit > 0:
                        if sum_debit > 0:
                            # if both debit and credit > 0
                            if invoice['type'] == 'in_invoice' or invoice['type'] == 'out_refund':
                                # if in_invoice or out_refund
                                invoice['sum_debit'] = sum_debit
                                invoice['sum_credit'] = invoice['amount_total'] + sum_credit
                            else:
                                # if out_invoice or in _refund
                                invoice['sum_debit'] = invoice['amount_total'] + sum_debit
                                invoice['sum_credit'] = sum_credit
                        else:
                            invoice['sum_debit'] = invoice['amount_total']
                            invoice['sum_credit'] = sum_credit
                    else:
                        invoice['sum_debit'] = sum_debit
                        invoice['sum_credit'] = invoice['amount_total']
                
                #netsvc.Logger().notifyChannel('invoice[sum_debit]',netsvc.LOG_INFO, invoice['sum_debit'])
                #netsvc.Logger().notifyChannel('invoice[sum_credit]',netsvc.LOG_INFO, invoice['sum_credit'])
                #netsvc.Logger().notifyChannel('invoice[amount_total]2',netsvc.LOG_INFO, invoice['amount_total'])
                if self.feq(invoice['sum_debit'], invoice['sum_credit']):
                    res_invoices_open = False
                invoice['amount_currency'] = invoice['amount_currency'] + amount_currency_balace
            #open invoices
            else:
                #set either credit or debit depending if out_invoice or in_invoice
                if invoice['type'] == 'out_invoice' or invoice['type'] == 'in_refund':
                    invoice['sum_debit'] = invoice['amount_total']
                else:
                    invoice['sum_credit'] = invoice['amount_total']
                
            if res_invoices_open:
                #add invoice if partner already exists in list
                partner_not_exists = True
                for partner in temp_dict_partner:
                    #get parent_id if is_company = False and set as new partner_id
                    current_partner = self.pool.get('res.partner').browse(self.cr, self.uid, int(invoice['partner_id']))
                    if current_partner.is_company == False and current_partner.parent_id:
                        invoice['partner_id'] = current_partner.parent_id.id
                    if partner['Partner_id'] == invoice['partner_id']:
                        partner_not_exists = False
                        partner['Lines'].append(invoice)
                        partner['SumDebit'] += invoice['sum_debit']
                        partner['SumCredit'] += invoice['sum_credit']
                        partner['SumCurrency'] += invoice['amount_currency']
                        break
                
                if partner_not_exists:
                    temp_invoices = []
                    temp_invoices.append(invoice)
                    partner_name = 'zzzzzz'
                    
                    #get parent_id if is_company = False and set as new partner_id
                    current_partner = self.pool.get('res.partner').browse(self.cr, self.uid, int(invoice['partner_id']))
                    if current_partner.is_company == False and current_partner.parent_id:
                        invoice['partner_id'] = current_partner.parent_id.id
                    
                    if invoice['partner_id']:
                        partner_name = pooler.get_pool(self.cr.dbname).get('res.partner').browse(self.cr, self.uid, int(invoice['partner_id'])).name
                    temp_dict = {'Partner': partner_name,
                                 'Partner_id': invoice['partner_id'],
                                 'Lines': temp_invoices,
                                 'SumDebit': invoice['sum_debit'],
                                 'SumCredit': invoice['sum_credit'],
                                 'SumCurrency': invoice['amount_currency']}
                    temp_dict_partner.append(temp_dict)

        #netsvc.Logger().notifyChannel('temp_dict_partner',netsvc.LOG_INFO, temp_dict_partner)
                
        if res_move_ids_invoices:
            res_move_ids_invoices_string = ','.join(str(n) for n in res_move_ids_invoices)
            where_move_ids_invoices = "AND i.move_id NOT IN (" + res_move_ids_invoices_string + ") "
        else:
            where_move_ids_invoices = ""
        # HACK: 02.05.2014 15:26:53: olivier: exclude the move_line's from query result
        if res_move_line_ids_invoices:
            res_move_line_ids_invoices_string = ','.join(str(n) for n in res_move_line_ids_invoices)
            where_move_ids_invoices += "AND i.id NOT IN (" + res_move_line_ids_invoices_string + ") "
        
        
        self.cr.execute("SELECT id FROM account_period WHERE date_stop <= %s", (str(self.date_set),))
        fy_period_set = ','.join(map(lambda id: str(id[0]), self.cr.fetchall()))
        logger.debug("fy_period_set: %s", fy_period_set)
        self.cr.execute("SELECT id FROM account_period WHERE date_start > %s", (str(self.date_set),))
        fy2_period_set = ','.join(map(lambda id: str(id[0]), self.cr.fetchall()))
        logger.debug("fy2_period_set: %s", fy2_period_set)
        
        if fy2_period_set != '':
            fy2_period_set = "AND i.reconcile_id IN (SELECT DISTINCT(reconcile_id) FROM account_move_line a WHERE a.period_id IN ("+fy2_period_set+"))"
        
        self.cr.execute(
                "SELECT i.account_id, i.move_id, upper(p.name) as sort_name, p.name, i.id, /*i.type,*/ i.debit, to_char(i.date, 'dd.mm.yyyy') as create_date, i.ref as number, i.name, j.code as journal_code, " \
                        "debit as sum_debit, credit as sum_credit, i.partner_id, p.lang, p.ref || ' - ' || p.name as partner_name, (case when i.currency_id is not null then COALESCE(i.amount_currency,0.0) else 0.0 end) as amount_currency " \
                "FROM account_move_line i " \
                "LEFT JOIN res_partner p on p.id = i.partner_id " \
                "JOIN account_journal j on j.id = i.journal_id " \
                "WHERE i.account_id IN (" + account_id + ") " + where_move_ids_invoices + " "\
                    "AND j.type != 'situation' " \
                    + str(self.date_or_period_where_manual_entries) + str(self.partner_id_where) + " " \
                    #"AND (i.reconcile_id is Null or (i.reconcile_id is not null and i.period_id IN (" + fy_period_set + ") " \
                    #+ str(fy2_period_set) + " " \
                    #"))" \
                    "ORDER BY sort_name, i.date ")
        
        query2 = (
                "SELECT i.account_id, i.move_id, upper(p.name) as sort_name, p.name, i.id, /*i.type,*/ i.debit, to_char(i.date, 'dd.mm.yyyy') as create_date, i.ref as number, i.name, j.code as journal_code, " \
                        "debit as sum_debit, credit as sum_credit, i.partner_id, p.lang, p.ref || ' - ' || p.name as partner_name, (case when i.currency_id is not null then COALESCE(i.amount_currency,0.0) else 0.0 end) as amount_currency " \
                "FROM account_move_line i " \
                "LEFT JOIN res_partner p on p.id = i.partner_id " \
                "JOIN account_journal j on j.id = i.journal_id " \
                "WHERE i.account_id IN (" + account_id + ") " + where_move_ids_invoices + " "\
                    "AND j.type != 'situation' " \
                    + str(self.date_or_period_where_manual_entries) + str(self.partner_id_where) + " " \
                    #"AND (i.reconcile_id is Null or (i.reconcile_id is not null and i.period_id IN (" + fy_period_set + ") " \
                    #+ str(fy2_period_set) + " " \
                    #"))" \
                    "ORDER BY sort_name, i.date ")
        logger.debug("Query2: %s", query2)
#"AND i.partner_id =  2740" \
        res_invoices_manuell = self.cr.dictfetchall()
        #netsvc.Logger().notifyChannel('res_invoices_manuell',netsvc.LOG_INFO, res_invoices_manuell)
        for invoice in res_invoices_manuell:
            partner_not_exists = True
            if invoice['partner_id']:
    #           if invoice['partner_id'] == 388:
                for partner in temp_dict_partner:
                    #get parent_id if is_company = False and set as new partner_id
                    current_partner = self.pool.get('res.partner').browse(self.cr, self.uid, int(invoice['partner_id']))
                    if current_partner.is_company == False and current_partner.parent_id:
                        invoice['partner_id'] = current_partner.parent_id.id
                        
                    if partner['Partner_id'] == invoice['partner_id']:
                        partner_not_exists = False
                        partner['Lines'].append(invoice)
                        partner['SumDebit'] += invoice['sum_debit']
                        partner['SumCredit'] += invoice['sum_credit']
                        partner['SumCurrency'] += invoice['amount_currency']
                        break
            else:
                for partner in temp_dict_partner:
                    if partner['Partner'] == 'zzzzzz':
                        partner_not_exists = False
                        partner['Lines'].append(invoice)
                        partner['SumDebit'] += invoice['sum_debit']
                        partner['SumCredit'] += invoice['sum_credit']
                        partner['SumCurrency'] += invoice['amount_currency']
                        break
            
            if partner_not_exists:
                temp_invoices = []
                temp_invoices.append(invoice)
                partner_name = 'zzzzzz'
                if invoice['partner_id']:
                    #get parent_id if is_company = False and set as new partner_id
                    current_partner = self.pool.get('res.partner').browse(self.cr, self.uid, int(invoice['partner_id']))
                    if current_partner.is_company == False and current_partner.parent_id:
                        invoice['partner_id'] = current_partner.parent_id.id
                
                if invoice['partner_id']:
                    partner_name = pooler.get_pool(self.cr.dbname).get('res.partner').browse(self.cr, self.uid, int(invoice['partner_id'])).name
                temp_dict = {'Partner': partner_name,
                             'Partner_id': invoice['partner_id'],
                             'Lines': temp_invoices,
                             'SumDebit': invoice['sum_debit'],
                             'SumCredit': invoice['sum_credit'],
                             'SumCurrency': invoice['amount_currency']}
                temp_dict_partner.append(temp_dict)

        #netsvc.Logger().notifyChannel('temp_dict_partner',netsvc.LOG_INFO, temp_dict_partner)
        self.data_invoices = temp_dict_partner
        #account_list = []
        #for r in self.data_invoices:
        #    netsvc.Logger().notifyChannel('get_accounts',netsvc.LOG_INFO, r)
        #    account_list.append(r)
        #return account_list
    
    def feq(self, a, b):
        if abs(a - b) < 0.00000001:
            return 1
        else:
            return 0
    
    def lines(self, partner):
        invoice_lines = []
        
        for r in self.data_invoices:
            if r['Partner_id'] == partner['Partner_id']:
                for line in r['Lines']:
                    if line['sum_debit'] == 0 and line['sum_credit'] == 0:
                        continue
                    else:
                        invoice_lines.append(line)
        return invoice_lines
    
    def _get_sum_debit(self):
        if self.total_sum_debit == 0:
            sumD = 0.00
            sumC = 0.00
            sumCurrency = 0.00
            self.get_account_lines(self.account_ids)
            for r in self.data_invoices:
                if (r['SumCredit'] - r['SumDebit']) != 0:
                    sumD += r['SumDebit']
                    sumC += r['SumCredit']
                    sumCurrency += r['SumCurrency']
            self.total_sum_debit = sumD
            self.total_sum_credit = sumC
            self.total_sum_currency = sumCurrency
        return self.total_sum_debit
    
    def _get_sum_credit(self):
        return self.total_sum_credit
    
    def _get_sum_currency(self):
        return self.total_sum_currency
    
    def _get_sum_account_debit(self, account):
        account_id = str(account['id'])
        sum = 0.00
        if self.last_account_sum_computed != account_id:
            self.get_account_lines(account_id)
            self.last_account_sum_computed = account_id
        for r in self.data_invoices:
            if (r['SumCredit'] - r['SumDebit']) != 0:
                sum += r['SumDebit']
        return sum
    
    def _get_sum_account_credit(self, account):
        account_id = str(account['id'])
        sum = 0.00
        for r in self.data_invoices:
            if (r['SumCredit'] - r['SumDebit']) != 0:
                sum += r['SumCredit']
        return sum
    
    def _get_sum_account_currency(self, account):
        account_id = str(account['id'])
        sum = 0.00
        for r in self.data_invoices:
            if (r['SumCredit'] - r['SumDebit']) != 0:
                sum += r['SumCurrency']
        return sum
    
    def get_payment_lines(self, cr, uid, ids, context=None):
        result = {}
        moves = self.move_line_id_payment_get(cr, uid, ids)
        src = []
        lines = []
        for m in self.pool.get('account.move.line').browse(cr, uid, moves, context):
           # hack by jool1: exclude all payments from sales_journal (hardcoded)
           #if m.journal_id.id != 3:
                temp_lines = []#Added temp list to avoid duplicate records
                if m.reconcile_id:
                    #jool1 - only add if date_created is in range
                    for line in m.reconcile_id.line_id:
                        if line.date <= self.date_lst[len(self.date_lst) - 1]:
                            #if line.journal_id.id == 3:
                                #netsvc.Logger().notifyChannel('res_invoices_manuell',netsvc.LOG_INFO, 'test')
                            temp_lines.append(line.id)
                    #temp_lines = map(lambda x: x.id, m.reconcile_id.line_id)
                elif m.reconcile_partial_id:
                    #jool1 - only add if date_created is in range
                    for line in m.reconcile_partial_id.line_partial_ids:
                        if line.date <= self.date_lst[len(self.date_lst) - 1]:
                            #if line.journal_id.id == 3:
                                #netsvc.Logger().notifyChannel('res_invoices_manuell',netsvc.LOG_INFO, 'test2')
                            temp_lines.append(line.id)
                    #temp_lines = map(lambda x: x.id, m.reconcile_partial_id.line_partial_ids)
                
                lines += [x for x in temp_lines if x not in lines]
                src.append(m.id)
            
        lines = filter(lambda x: x not in src, lines)
        
        return lines

    def move_line_id_payment_get(self, cr, uid, ids, *args):
        res = []
        if not ids:
            return res
        cr.execute('SELECT l.id '\
                   'FROM account_move_line l '\
                   'LEFT JOIN account_invoice i ON (i.move_id=l.move_id) '\
                   'WHERE i.id IN %s '\
                   'AND l.account_id=i.account_id',
                   (tuple(ids),))
        res = map(itemgetter(0), cr.fetchall())
        return res
    
    def move_id_get(self, cr, uid, ids, *args):
        res = []
        if not ids:
            return res
        cr.execute('SELECT l.move_id '\
                   'FROM account_move_line l '\
                   'WHERE l.id IN %s ',
                   (tuple(ids),))
        res = map(itemgetter(0), cr.fetchall())
        return res
    
    def payment_lines_get_total_amount_debit(self, cr, uid, ids, *args):
        res = []
        if not ids:
            return res
        cr.execute('SELECT sum(l.debit) '\
                   'FROM account_move_line l '\
                   'WHERE l.id IN %s ',
                   (tuple(ids),))
        res = map(itemgetter(0), cr.fetchall())
        return res[0]
    
    def payment_lines_get_total_amount_credit(self, cr, uid, ids, *args):
        res = []
        if not ids:
            return res
        cr.execute('SELECT sum(l.credit) '\
                   'FROM account_move_line l '\
                   'WHERE l.id IN %s ',
                   (tuple(ids),))
        res = map(itemgetter(0), cr.fetchall())
        return res[0]
    
    def payment_lines_get_total_amount_currency(self, cr, uid, ids, *args):
        res = []
        if not ids:
            return res
        #cr.execute('SELECT COALESCE(sum(case when l.debit > 0 then abs(l.amount_currency) else abs(l.amount_currency)*-1 end),0) as amount_total '\
        cr.execute('SELECT COALESCE(sum(case when l.debit > 0 then abs((case when l.currency_id is not null then l.amount_currency else 0.0 end)) else abs((case when l.currency_id is not null then l.amount_currency else 0.0 end))*-1 end),0) as amount_total '\
                   'FROM account_move_line l '\
                   'WHERE l.id IN %s ',
                   (tuple(ids),))
        res = map(itemgetter(0), cr.fetchall())
        return res[0]
    
    def total_amount_debit_partner(self, cr, uid, ids, *args):
        res = []
        if not ids:
            return res
        cr.execute('SELECT sum(l.debit) '\
                   'FROM account_move_line l '\
                   'WHERE l.id IN %s ',
                   (tuple(ids),))
        res = map(itemgetter(0), cr.fetchall())
        return res[0]
        
    def total_amount_credit_partner(self, cr, uid, ids, *args):
        res = []
        if not ids:
            return res
        cr.execute('SELECT sum(l.credit) '\
                   'FROM account_move_line l '\
                   'WHERE l.id IN %s ',
                   (tuple(ids),))
        res = map(itemgetter(0), cr.fetchall())
        return res[0]

    def _get_company(self, form):
        return pooler.get_pool(self.cr.dbname).get('res.company').browse(self.cr, self.uid, form['company_id']).name

    def _get_currency(self, form):
        return pooler.get_pool(self.cr.dbname).get('res.company').browse(self.cr, self.uid, form['company_id']).currency_id.name

report_sxw.report_sxw('report.account.oplist.cust', 'account.account',
    'addons/bt_oplist/report/oplist_report.rml', parser=oplist_report, header=False)

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
