# b-*- encoding: utf-8 -*-
#
#
#    Copyright (c) 2015 brain-tec AG (http://www.braintec-group.com
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

from openerp.osv import fields, osv
from openerp.tools.translate import _
from openerp.tools import DEFAULT_SERVER_DATETIME_FORMAT
import datetime


class followup_errors(osv.Model):
    ''' This class is intended to be used as a log of error which were caused because of
        some kind of follow-up problem related to a particular invoice.
    '''
    _name = 'followup.errors'

    def create_error_entry(self, cr, uid, ids, invoice_id, error_message, context=None):
        ''' Logs an error and timestamps it.
        '''
        if context is None:
            context = {}

        datetime_now_str = datetime.datetime.now().strftime(DEFAULT_SERVER_DATETIME_FORMAT)
        self.create(cr, uid, {'date': datetime_now_str,
                              'invoice_id': invoice_id,
                              'error_message': error_message,
                              }, context=context)

        return True

    def remove_errors(self, cr, uid, ids, invoice_ids, context=None):
        ''' Removes any previous errors that are logged corresponding to the invoices received.
        '''
        if context is None:
            context = {}

        errors_ids = self.search(cr, uid, [('invoice_id', 'in', invoice_ids)], context=context)
        self.unlink(cr, uid, errors_ids, context=context)
        return True

    _columns = {
        'date': fields.datetime('Date', help='Date in which the error happened.'),
        'invoice_id': fields.many2one('account.invoice', 'Invoice', ondelete='cascade'),
        'error_message': fields.text('Error Message'),
    }

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
