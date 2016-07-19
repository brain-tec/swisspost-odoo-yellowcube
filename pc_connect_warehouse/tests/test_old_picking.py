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
import anybox.testing.datetime
from datetime import datetime, timedelta
import time


class test_old_picking(common.TransactionCase):

    def setUp(self):
        common.TransactionCase.setUp(self)
        ctx = self.context = {}
        cr = self.cr
        uid = self.uid
        self.conf_obj = self.registry('configuration.data')
        self.issue_obj = self.registry('project.issue')
        self.pick_obj = self.registry('stock.picking')
        self.conf = self.conf_obj.get(cr, uid, [], ctx)
        # Set some values
        self.conf.write({'stock_picking_out_max_open_age': 2,
                         'stock_picking_out_max_open_age_uom': 'days'})
        self.warehouse0 = self.browse_ref('stock.warehouse0')
        self.issues = None
        self.outatime = False

    def tearDown(self):
        self.change_time()
        common.TransactionCase.tearDown(self)

    def change_time(self, **moment):
        if moment:
            self.outatime = True
            datetime.set_now(datetime.now() + timedelta(**moment))
        else:
            self.outatime = False
            datetime.real_now()
        logger.debug("Now is {0}".format(datetime.now()))

    def check_same_issues(self):
        cr, uid, ctx = self.cr, self.uid, self.context
        self.conf_obj.check_old_stock_picking_out(cr, uid, ctx)
        same_issues = self.issue_obj.search(cr, uid, [], context=ctx, order='id desc')
        self.assertEquals(self.issues, same_issues, 'No new issues had been created')

    def check_new_issues(self):
        cr, uid, ctx = self.cr, self.uid, self.context
        # Run the scheduler
        self.conf_obj.check_old_stock_picking_out(cr, uid, ctx)
        # Get all issues
        new_issues = self.issue_obj.search(cr, uid, [], context=ctx, order='id desc')
        # Compare with old issues
        self.assertNotEquals(self.issues, new_issues, 'New issues had been created')
        self.issues = new_issues

    def test_alarms(self):
        cr, uid, ctx = self.cr, self.uid, self.context
        # First, we create the issues
        self.check_new_issues()
        # Second, we check the code does not create new issues for old stock.picking
        self.check_same_issues()
        # Third, we create a very old picking, and check it
        self.change_time(days=-10)
        self.pick_obj.create(cr, uid, {'picking_type_id': self.warehouse0.in_type_id.id}, ctx)
        # In the past it is ok
        self.check_same_issues()
        self.change_time()
        # In the future it raises an issue
        self.check_new_issues()
        # But only once
        self.check_same_issues()


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
