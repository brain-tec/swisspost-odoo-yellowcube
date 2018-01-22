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
from openerp.osv import osv, fields
from openerp.tools.translate import _

# from openerp.addons.audittrail.audittrail import audittrail_objects_proxy
from openerp.tests import common
from openerp.osv import orm
import logging
logger = logging.getLogger(__name__)
import unittest2
from openerp.osv import osv
from openerp.addons.audittrail.audittrail import audittrail_objects_proxy

# audittrail_objects_proxy()


class base_test(common.TransactionCase):
    def setUp(self):
        super(base_test, self).setUp()
        # audittrail_objects_proxy()

        self.context = {}
        self.model_obj = None
        self.audittrail_obj = self.registry('audittrail.rule')
        self.audittrail_log_obj = self.registry('audittrail.log')
        self.ir_model_obj = self.registry('ir.model')
        self.ir_model_id = None

        self.raise_errors = False
        self.errors = []

    def tearDown(self):
        super(base_test, self).tearDown()
        if self.errors:
            for error in self.errors:
                logger.error(error)
            raise

    def get_rule_id(self):
        cr, uid, ctx = self.cr, self.uid, self.context
        rule_ids = self.audittrail_obj.search(cr, uid, [('object_id', '=', self.ir_model_id)], context=ctx)
        if rule_ids:
            return rule_ids[0]
        vals = {
            'object_id': self.ir_model_id,
            'name': 'rule for {0}'.format(self.model),
        }
        return self.audittrail_obj.create(cr, uid, vals, context=ctx)

    def create_element(self, vals):
        return self.model_obj.create(self.cr, self.uid, vals, context=self.context)

    def modify_element(self, ids, vals):
        return self.model_obj.write(self.cr, self.uid, ids, vals, context=self.context)

    def destroy_element(self, ids):
        return self.model_obj.unlink(self.cr, self.uid, [ids], context=self.context)

    def check_search(self, domain):
        l = len(self.audittrail_log_obj.search(self.cr, self.uid, domain, context=self.context))
        msg = 'There must be some logs for domain {0}'.format(domain)
        if self.raise_errors:
            self.assertGreater(l, 0, msg)
        else:
            self.errors.append(msg)

    @unittest2.skip('Audittrail cannot be tested with odoo automatic tests.')
    def _test_check_model_rule(self):
        cr, uid, ctx = self.cr, self.uid, self.context

        self.assertEqual(type(osv.service), audittrail_objects_proxy, 'Audittrail must be the object proxy')

        self.assertIsNotNone(self.model, 'There must be a model defined')
        self.model_obj = self.registry(self.model)
        self.ir_model_id = self.ir_model_obj.search(cr, uid, [('model', '=', self.model)], context=ctx)[0]

        rule_id = self.get_rule_id()

        vals = {
            'log_read': True,
            'log_write': True,
            'log_unlink': True,
            'log_create': True,
            'log_action': True,
            'log_workflow': True,
            'user_id': [(6, None, [])]
        }
        if self.audittrail_obj.read(cr, uid, rule_id, ['state'], ctx)['state'] != 'draft':
            self.audittrail_obj.unsubscribe(cr, uid, [rule_id], ctx)
        self.audittrail_obj.write(cr, uid, rule_id, vals, context=ctx)
        self.audittrail_obj.subscribe(cr, uid, [rule_id], ctx)
        self.model_obj = self.registry(self.model)
        obj_id = self.create_element({'name': 'original_name'})
        self.check_search([('object_id', '=', self.ir_model_id), ('res_id', '=', obj_id), ('method', '=', 'create')])
        self.modify_element(obj_id, {'name': 'other_name'})
        self.check_search([('object_id', '=', self.ir_model_id), ('res_id', '=', obj_id), ('method', '=', 'write')])
        self.destroy_element(obj_id)
        self.check_search([('object_id', '=', self.ir_model_id), ('res_id', '=', obj_id), ('method', '=', 'unlink')])
        self.check_search([('object_id', '=', self.ir_model_id), ('res_id', '=', obj_id)])


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwid