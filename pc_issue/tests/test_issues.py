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
from openerp.tests import common
from openerp.addons import pc_connect_master
import logging
logger = logging.getLogger(__name__)


class test_issues(common.TransactionCase):

    def obj_registry(self, pool):
        """
        This method simplifies calling methods with cr, uid and context
        """
        ret = self.registry(pool)

        class __method:

            def __init__(self, delegate, func):
                self.delegate = delegate
                self.func = func

            def __call__(self, *args, **kargs):
                return self.func(*args, **kargs)

            def ctx(self, *args, **kargs):
                if 'context' not in kargs:
                    kargs['context'] = self.delegate.context
                return self.func.__call__(self.delegate.cr, self.delegate.uid, *args, **kargs)

        for m in ['copy', 'browse', 'unlink', 'create', 'write', 'read', 'search']:
            f = getattr(ret, m)
            setattr(ret, m, __method(self, f))

        return ret

    def setUp(self):
        super(test_issues, self).setUp()

        self.context = {}

        self.sale_order_obj = self.obj_registry('sale.order')
        self.issue_obj = self.obj_registry('project.issue')
        self.exception_obj = self.obj_registry('sale.exception')
        self.tag_obj = self.obj_registry('project.category')

        self.sale_order_test1_id = self.ref('sale.sale_order_1')
        self.quotation_so_test1_id = self.sale_order_obj.copy.ctx(self.sale_order_test1_id)
        self.sale_exception_id = self.ref('pc_issue.excep_order_too_young')

    def tearDown(self):
        super(test_issues, self).tearDown()

    def _get_issues(self, table_name, res_id, tags=None, create=False, reopen=False, context=None):
        if not context:
            context = self.context
        return self.issue_obj.find_resource_issues(self.cr, self.uid, table_name, res_id, tags=tags, create=create, reopen=reopen, context=context)

    def test_create_exception_project(self):
        """
        This test creates and exception for the different tags, and checks they are assigned to a valid project
        """

        sale_order = self.sale_order_obj.browse.ctx(self.sale_order_test1_id)
        expected_issues = 0
        so_issues = self._get_issues('sale.order', sale_order.id)
        self.assertEqual(len(so_issues), expected_issues, 'No issues exist for this sale.order')
        tags_to_test = [x['name'] for x in self.tag_obj.read.ctx(self.tag_obj.search.ctx([]), ['name'])]

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

    def test_sale_order_exception(self):
        """
        Test if sale.exception creates an issue associated with a sale order
        """
        exception = self.exception_obj.browse.ctx(self.sale_exception_id)
        sale_order = self.sale_order_obj.browse.ctx(self.sale_order_test1_id)
        so_issues = self._get_issues('sale.order', sale_order.id)
        quotation = self.sale_order_obj.browse.ctx(self.quotation_so_test1_id)
        qo_issues = self._get_issues('sale.order', quotation.id)

        self.assertFalse(exception.active, 'Exception is deactivated at first')
        self.assertNotEqual(sale_order.state, 'draft', 'Checking SO not in draft')
        self.assertFalse(so_issues, 'No issues must exist for the sale.order')
        self.assertEqual(quotation.state, 'draft', 'Checking Quotation in draft')
        self.assertFalse(qo_issues, 'No issues must exist for the quotation')

        self.exception_obj.write.ctx(exception.id, {'active': True})
        quotation.write({'date_order': '1999-01-01'})
        self.sale_order_obj.detect_exceptions(self.cr, self.uid, [quotation.id], context=self.context)
        exception = self.exception_obj.browse.ctx(self.sale_exception_id)
        quotation = self.sale_order_obj.browse.ctx(self.quotation_so_test1_id)
        qo_issues = self._get_issues('sale.order', quotation.id)

        self.assertTrue(exception.active, 'Exception is activated now')
        self.assertGreater(len(qo_issues), 0, 'There are new issues in the quotation')

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
