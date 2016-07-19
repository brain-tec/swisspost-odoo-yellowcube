# b-*- encoding: utf-8 -*-
##############################################################################
#
#    Copyright (c) 2015 brain-tec AG (http://www.brain-tec.ch)
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
from openerp.osv import osv, fields
from openerp.tools.translate import _
import logging
logger = logging.getLogger(__name__)
from openerp.tests import common


class test_issue_log(common.TransactionCase):

    def setUp(self):
        super(test_issue_log, self).setUp()

        self.context = {'log_errors': False}
        self.connect = self.browse_ref('pc_connect_warehouse.demo_connection_1')
        self.issue_obj = self.registry('project.issue')
        self.sale_order_test1_id = self.ref('sale.sale_order_1')

    def tearDown(self):
        super(test_issue_log, self).tearDown()

    def test_issues(self):
        """
        This test checks that it is possible to log errors through the stock.connect.

        First, it checks that it creates the first issue for the stock.connect.

        Then, it creates a second log for a sale.order, so the error appears both in the stock.connect, and in the sale.order
        """
        cr, uid, ctx = self.cr, self.uid, self.context
        # First, we get the number of existing issues
        initial_issues = self.issue_obj.search(cr, uid, [], context=ctx)
        # Then, we create a message for no object.
        ret = self.connect.with_context(ctx).log_issue('test message using variables: {x} {log_errors}', x=314)
        new_issues = self.issue_obj.search(cr, uid, [], context=ctx)
        self.assertEqual(len(ret['issue_ids']), 1, 'Some issues where created')
        for x in ret['issue_ids']:
            self.assertIn(x, new_issues, 'The new issues had been created')
            self.assertNotIn(x, initial_issues, 'Those issues are not in the original issues')
        self.context['active_id'] = self.sale_order_test1_id
        self.context['active_model'] = 'sale.order'
        # Then, we create a message for a sale object.
        ret = self.connect.with_context(ctx).log_issue('test message for the model {active_model}')
        new_issues_2 = self.issue_obj.search(cr, uid, [], context=ctx)
        self.assertEqual(len(ret['issue_ids']), 2, 'Some issues where created')
        self.assertNotEqual(new_issues, new_issues_2, 'There are new issues')
        for x in ret['issue_ids']:
            self.assertIn(x, new_issues_2, 'The new issues had been created')
            self.assertNotIn(x, initial_issues, 'Those issues are not in the original issues')


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
