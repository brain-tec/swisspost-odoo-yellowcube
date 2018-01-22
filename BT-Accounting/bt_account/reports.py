# b-*- encoding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (Ci 2004-2009 Tiny SPRL (<http://tiny.be>).
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

class bt_account_reports(osv.osv):
    _name='bt.account.reports'

    def __init__(self, pool, cr):
        super(bt_account_reports, self).__init__(pool, cr)
        
        # Update account general ledger
        sqlQuery = "UPDATE ir_act_report_xml \
            SET report_name='%s', report_file='%s', report_rml='%s' \
            WHERE report_name='%s' AND model='%s' AND report_file='%s'" % ('account.ledger_bt', 'bt_account/report/account_general_ledger.rml', 'bt_account/report/account_general_ledger.rml', 'account.general.ledger', 'account.account', 'account/report/account_general_ledger.rml')
        cr.execute(sqlQuery)

bt_account_reports()