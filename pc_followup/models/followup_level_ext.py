# b-*- encoding: utf-8 -*-
##############################################################################
#
#    Copyright (c) 2015 brain-tec AG (http://www.braintec-group.com)
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

import os
from datetime import timedelta, datetime
from openerp.osv import fields, osv
from openerp.tools.translate import _
from openerp.addons.pc_log_data.log_data import write_log
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT
from openerp.addons.bt_followup.account_invoice_ext import get_bank_account


class followup_level_ext(osv.osv):
    _inherit = 'followup.level'

    def get_followup_text_with_wildcards(self, cr, uid, ids, invoice_id, text,
                                         context=None):
        """ Returns the text with its wildcards substituted,
            using the language of the partner set on the invoice.

        """
        if context is None:
            context = {}

        invoice_obj = self.pool.get('account.invoice')

        invoice = invoice_obj.browse(cr, uid, invoice_id, context=context)
        context.update({'lang': invoice.partner_id.lang})

        followup_level = invoice.followup_level_id
        if not followup_level:
            return ''

        # Gets the format for dates according to the res.partner's language.
        partner_lang_date_format = invoice.partner_id.get_partner_date_format()

        text = text and text.replace(os.linesep, '<br />') or ''
        if text:
            num_days = followup_level.delay
            new_due_date = (datetime.strptime(
                invoice.date_due, DEFAULT_SERVER_DATE_FORMAT) + timedelta(
                num_days)).strftime(partner_lang_date_format)
            date_yesterday_str = (datetime.now() + timedelta(-1)).strftime(
                partner_lang_date_format)

            if '{yesterday}' in text:
                text = text.replace('{yesterday}', date_yesterday_str)

            if '{new_due_date}' in text:
                text = text.replace('{new_due_date}', str(new_due_date))

            if '{num_days}' in text:
                text = text.replace('{num_days}', str(num_days))

            if '{partner_firstname}' in text:
                text = text.replace(
                    '{partner_firstname}', invoice.partner_id.firstname or '')

            if '{partner_lastname}' in text:
                text = text.replace(
                    '{partner_lastname}', invoice.partner_id.lastname or '')

            if '{account_number}' in text:
                account_number = get_bank_account(self,
                    cr, uid, context=context)
                if account_number is None:
                    # This should never happen because the code which handles
                    # follow-ups prevents it to be executed if there
                    # is no bank account.
                    error_message = \
                        _('The company does not have a bank account defined.')
                    write_log(self, cr, uid, 'account.invoice', 'Follow-up',
                              invoice.id, 'Follow-up error',
                              False,  # False=error.
                              error_message)
                else:
                    text = text.replace(
                        '{account_number}', str(account_number))

        return text

    _columns = {
        'block_new_invoice': fields.boolean("Block new Invoices")
    }

    _defaults = {
        'block_new_invoice': False
    }

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
