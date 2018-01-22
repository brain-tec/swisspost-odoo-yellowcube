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
from openerp.osv import osv, fields
from openerp.tools.translate import _
from openerp.tests import common
from openerp.addons import pc_connect_master
from unittest2 import skipIf

UNDER_DEVELOPMENT = False
UNDER_DEVELOPMENT_TEXT = "Test was skipped because of being under development."


class test_issues(common.TransactionCase):

    def setUp(self):
        super(test_issues, self).setUp()

        self.context = {}

        self.sale_order_obj = self.registry('sale.order')
        self.issue_obj = self.registry('project.issue')
        self.exception_obj = self.registry('sale.exception')
        self.tag_obj = self.registry('project.category')

        self.sale_order_test1_id = self.ref('sale.sale_order_1')
        self.quotation_so_test1_id = self.sale_order_obj.copy(
            self.cr, self.uid, self.sale_order_test1_id, context=self.context)
        self.sale_exception_id = self.ref('pc_issue.excep_order_too_young')

    def tearDown(self):
        super(test_issues, self).tearDown()

    def _get_issues(self, table_name, res_id, tags=None, create=False, reopen=False, context=None):
        if not context:
            context = self.context
        return self.issue_obj.find_resource_issues(self.cr, self.uid, table_name, res_id, tags=tags, create=create, reopen=reopen, context=context)

    @skipIf(UNDER_DEVELOPMENT, UNDER_DEVELOPMENT_TEXT)
    def test_create_exception_project(self):
        """
        This test creates and exception for the different tags, and checks they are assigned to a valid project
        """
        cr, uid, ctx = self.cr, self.uid, self.context.copy()
        sale_order = self.sale_order_obj.browse(cr, uid, self.sale_order_test1_id, context=ctx)
        expected_issues = 0
        so_issues = self._get_issues('sale.order', sale_order.id)
        self.assertEqual(len(so_issues), expected_issues, 'No issues exist for this sale.order')
        tags_to_test = [x['name'] for x in self.tag_obj.read(cr, uid, [], ['name'], context=ctx)]

        # For each tag, we will open and create and issue
        for tag in tags_to_test:
            expected_issues += 1
            self._get_issues('sale.order', sale_order.id, [tag], create=True, reopen=True)

        # So, now we have an issue per tag
        so_issues = self._get_issues('sale.order', sale_order.id)
        self.assertEqual(len(so_issues), expected_issues, 'Issues must exist for this sale.order')

        # Next, we create issues with previous tags, and a new one, but no issues must be created
        for tag in tags_to_test:
            self._get_issues('sale.order', sale_order.id, [tag, 'no-existing-tag'], create=True, reopen=True)

        # So, now we have an issue per tag
        so_issues = self._get_issues('sale.order', sale_order.id)
        self.assertEqual(len(so_issues), expected_issues, 'Issues must exist for this sale.order')

    @skipIf(UNDER_DEVELOPMENT, UNDER_DEVELOPMENT_TEXT)
    def test_sale_order_exception(self):
        """ Test if sale.exception creates an issue associated with 
            a sale order.
        """

        # Gets a quotation, removes its carrier, and validates it. This will
        # raise an exception from those that we define.

        # Gets a quotation with no issues set and in state draft.
        quotation = self.sale_order_obj.browse(self.cr, self.uid,
                                               self.quotation_so_test1_id,
                                               self.context)
        qo_issues = self._get_issues('sale.order', quotation.id)
        self.assertEqual(quotation.state, 'draft',
                         'Checking Quotation in draft')
        self.assertFalse(qo_issues, 'No issues must exist for the quotation')

        # We remove the carrier_id from the quotation and we validate it.
        # This will result in an exception set on the quotation, and the
        # quotation be kept in draft.
        self.sale_order_obj.write(self.cr, self.uid, quotation.id,
                                  {'carrier_id': False}, self.context)
        self.sale_order_obj.action_button_confirm(self.cr, self.uid,
                                                  [quotation.id], self.context)

        quotation = self.sale_order_obj.browse(self.cr, self.uid,
                                               quotation.id, self.context)

        print 'QUOTATION ID', quotation.id

        self.assertEqual(quotation.state, 'draft',
                         'Checking Quotation in draft')
        self.assertGreater(len(quotation.exceptions_ids), 0,
                           'Checking an exception set on the quotation.')

        # The exception should have created an issue associated to the
        # quotation.
        qo_issues = self._get_issues('sale.order', quotation.id)
        self.assertGreater(len(qo_issues), 0,
                           'There should be new issues for the quotation')

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
