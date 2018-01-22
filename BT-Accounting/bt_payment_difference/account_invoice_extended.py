##OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2009 Tiny SPRL (<http://tiny.be>).
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

from osv import osv, fields
from tools.translate import _
import decimal_precision as dp
import time

class account_invoice_extended(osv.osv):
    _inherit = 'account.invoice'

    def test_paid(self, cr, uid, ids, *args):
#        print 'TEST_PAID NEW'
#        print 'ids: ', ids
        #res = self.move_line_id_payment_get(cr, uid, ids)
        
        context=None
        ok = False
        #hack jool
        for invoice in self.browse(cr, uid, ids, context=context):
#            print 'invoice.residual: ', invoice.residual
            if invoice.state in ['open', 'paid'] and invoice.residual == 0:
                ok = True 
#        print 'ok: ', ok
#        print 'res: ', res
#        if not res:
#            return False
#        ok = True
#        for id in res:
#            cr.execute('select reconcile_id from account_move_line where id=%s', (id,))
#            print 'select reconcile_id from account_move_line where id=%s', (id,)
#            ok = ok and  bool(cr.fetchone()[0])
        return ok
    
    def confirm_paid(self, cr, uid, ids, context=None):
#         print 'CONFIRM_PAID NEW'
        res = super(account_invoice_extended, self).confirm_paid(cr, uid, ids, context=context)
        for inv_id, name in self.name_get(cr, uid, ids, context=context):
            message = _("Invoice '%s' is paid.") % name
            self.log(cr, uid, inv_id, message)
        return res
    
account_invoice_extended()
