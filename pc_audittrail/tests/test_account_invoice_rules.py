# b-*- encoding: utf-8 -*-
##############################################################################
#
#    Copyright (c) 2014 brain-tec AG (http://www.braintec-group.com)
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
from base_test import base_test
from openerp.osv import osv, fields
from openerp.tools.translate import _
from openerp.osv import orm


class test_account_invoice_rules(base_test):

    model = 'account.invoice'

    def test(self):
        self._test_check_model_rule()

    def create_element(self, vals):
        vals['account_id'] = self.ref('account.a_recv')
        vals['partner_id'] = self.ref('base.res_partner_1')
        return super(test_account_invoice_rules, self).create_element(vals)

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwid