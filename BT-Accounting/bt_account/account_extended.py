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

class account_extended(osv.osv):
    _inherit = 'account.move'        

    #hack jool: if period will be changed in account_move -> change period for account_move_line's
    def onchange_period(self, cr, user, ids, period_id, context=None):
        for move in self.browse(cr, user, ids, context=context):
            for line in move.line_id:
                cr.execute("update account_move_line set period_id = %s where id = %s" % (period_id,line.id))
        return True
    
    #hack jool: if date will be changed in account_move -> change date for account_move_line's
    def onchange_date(self, cr, user, ids, date, context=None):
        for move in self.browse(cr, user, ids, context=context):
            for line in move.line_id:
                cr.execute("update account_move_line set date = '%s' where id = %s" % (date,line.id))
        return True
    
account_extended()

class account_fiscalyear_ext(osv.osv):
    _inherit = 'account.fiscalyear'

    _order = "date_start desc, id"
    
account_fiscalyear_ext()

class account_period_ext(osv.osv):
    _inherit = 'account.period'

    _order = "date_start desc, special desc"
    
account_fiscalyear_ext()