# b-*- encoding: utf-8 -*-
#
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
#


from openerp.osv import osv
import time
from report import report_sxw
from openerp.tools.translate import _
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT
import sys
import os
sys.path.append(
    os.path.abspath(os.path.join(os.path.dirname(__file__), os.path.pardir)))
from account_invoice_ext import get_bank_account
# libraries to sort, group and print lists
import operator
import itertools
from datetime import timedelta, datetime, date
from openerp.addons.bt_helper.tools.bt_reports import delete_report_from_db

class invoice_followup_report(report_sxw.rml_parse):

    def __init__(self, cr, uid, name, context):

        super(invoice_followup_report, self).__init__(cr, uid, name, context)

        self.localcontext.update({
            'cr': cr,
            'uid': uid,
            'get_grouped_invoices': self.get_grouped_invoices,
            'get_partner_invoice_address_data':
                self.get_partner_invoice_address_data,

            'get_followup_level_text': self._get_followup_level_text,
            'get_followup_level_name': self._get_followup_level_name,

            'current_date': date.today().strftime('%Y-%m-%d'),
            'format_number': self._format_number,

        })

    def get_grouped_invoices(self, objects):
        invoices = []
        for inv in objects:
            if inv.followup_level_id:
                invoice = {}
                invoice['partner_id'] = inv.partner_id.id
                invoice['company_id'] = inv.company_id.partner_id.id
                invoice['partner_name'] = inv.partner_id.name
                invoice['lang'] = inv.partner_id.lang
                invoice[
                    'followup_responsible'] = inv.partner_id.followup_responsible_id.name or ''
                invoice[
                    'followup_responsible_email'] = inv.partner_id.followup_responsible_id.email or ''

                invoice['followup_level_id'] = inv.followup_level_id.id

                invoice[
                    'currency'] = inv.currency_id.symbol if inv.currency_id else ''
                invoice['number'] = inv.number
                invoice['date_invoice'] = inv.date_invoice
                invoice['date_due'] = inv.date_due
                invoice['invoice_id'] = inv.id
                invoice['followup_level_name'] = inv.followup_level_id.name
                invoice['total'] = inv.amount_total
                invoice['total_unpaid'] = inv.residual

                penalization_total = 0
                for penalization_invoice in inv.followup_penalization_invoice_ids:
                    penalization_total += penalization_invoice.amount_total

                invoice['penalization_total'] = penalization_total
                invoice['followup_total'] = penalization_total + inv.residual

                invoice['data'] = inv

                invoices.append(invoice)

        invoices.sort(key=operator.itemgetter('partner_id'), reverse=False)

        invoices_grouped_by_partner = []
        for __, items in itertools.groupby(invoices, operator.itemgetter('partner_id')):
            invoices_grouped_by_partner.append(list(items))

        inv_grouped_by_partner_and_level = []
        for partner_group in invoices_grouped_by_partner:
            partner_group.sort(
                key=operator.itemgetter(
                    'followup_level_id'),
                reverse=False)

            partner_grouped_by_level = []
            for __, items in itertools.groupby(partner_group, operator.itemgetter('followup_level_id')):
                partner_grouped_by_level.append(list(items))

            inv_grouped_by_partner_and_level.append(partner_grouped_by_level)

        return inv_grouped_by_partner_and_level

    def _format_number(self, number, number_of_spaces=5):
        '''Converts a number like '123456789012345' into '12 34567 89012 345'.'''

        return ''.join([' '[(i - 2) % number_of_spaces:] + c for i, c in enumerate(number)])

    #===========================================================================
    # Invoice Address Data is address Data from partner in invoice, not from contact
    #=========================================================================
    def get_partner_invoice_address_data(
            self, cr, uid, partner_id, context=None):

        res_partner_obj = self.pool.get(
            'res.partner').browse(cr,
                                  uid,
                                  partner_id,
                                  context=context)

        # it would be util to put data of the parent if parent exists

        res = {
            'name': res_partner_obj.name,
             'street': res_partner_obj.street,
             'street2': res_partner_obj.street2 or '',
             'country_code':
                 (
                     res_partner_obj.country_id and res_partner_obj.country_id.code) or '',
             'zip': res_partner_obj.zip or '',
             'city': res_partner_obj.city or '',
             'country_name':
                 (
                     res_partner_obj.country_id and res_partner_obj.country_id.name) or '',
        }

        return res

    def _get_followup_level_name(
            self, cr, uid, invoice_id, lang, context=None):
        if context is None:
            context = {}
        context = context.copy()
        context.update({'lang': lang})

        invoice_obj = self.pool.get('account.invoice')
        followup_level_obj = self.pool.get('followup.level')

        invoice = invoice_obj.browse(cr, uid, invoice_id, context)
        followup_level = followup_level_obj.browse(
            cr,
            uid,
            invoice.followup_level_id.id,
            context)

        level_name = followup_level.name or ''

        return level_name

    def _get_followup_level_text(
            self, cr, uid, invoice_id, lang, context=None):
        if context is None:
            context = {}
        context.update({'lang': lang})

        invoice_obj = self.pool.get('account.invoice')
        followup_level_obj = self.pool.get('followup.level')

        invoice = invoice_obj.browse(cr, uid, invoice_id, context)
        followup_level = followup_level_obj.browse(
            cr,
            uid,
            invoice.followup_level_id.id,
            context)

        text = followup_level.description and followup_level.description.replace(
            "\n", "<br />") or ''

        user_id = invoice.partner_id.followup_responsible_id and invoice.partner_id.followup_responsible_id.id or uid
        user = self.pool.get('res.users').browse(cr, uid, user_id, context)

        user_signature = user.signature and user.signature.replace(
            "\n", "<br />") or ''

        # Gets the date in the format of the partner.
        partner = invoice.partner_id
        partner_lang_date_format = partner.get_partner_date_format()

        num_days = followup_level.delay
        new_due_date = (datetime.strptime(invoice.date_due, DEFAULT_SERVER_DATE_FORMAT) + timedelta(num_days)).strftime(partner_lang_date_format)

        if text:
            values = {
                'partner_name': invoice.partner_id.name,
                'company_name': invoice.company_id.name,
                'user_signature': user_signature,
                'date': time.strftime('%Y-%m-%d'),
                'new_due_date': new_due_date,
                'num_days': followup_level.delay,
                'account_number':
                    get_bank_account(self, cr, uid, context=context)
            }
            text = text.format(**values)
        return text.encode('ascii', 'xmlcharrefreplace')

delete_report_from_db('invoice_followup_report')
report_sxw.report_sxw('report.invoice_followup_report', 'account.invoice',
                      'addons/bt_followup/report/invoice_followup_report.mako',
                      parser=invoice_followup_report)
