# -*- coding: utf-8 -*-
#
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
#

from openerp.osv import osv
from openerp.tools.translate import _
from openerp import netsvc
from openerp import pooler


class account_invoice_followup_handle(osv.osv_memory):

    """
    This wizard will process all pending to handle invoices
    """

    _name = "account.invoice.followup.handle"
    _description = "Handle Follow-up of the selected invoices"

    def do_multi_handle_followup(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        pool_obj = pooler.get_pool(cr.dbname)
        # data_inv = pool_obj.get('account.invoice').read(cr, uid,
        # context['active_ids'], ['state'], context=context)

        return pool_obj.get('account.invoice').do_handle_followup(cr, uid, ids, context=context)


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
