# -*- coding: utf-8 -*-
##############################################################################
#
#    Copyright (c) 2016 brain-tec AG (http://www.braintec-group.com)
#    All Right Reserved
#
#    See LICENSE file for full licensing details.
##############################################################################
from openerp.tests import TransactionCase
from inspect import getargspec
import logging
_logger = logging.getLogger(__name__)


class TestTransport(TransactionCase):

    def setUp(self):
        super(TestTransport, self).setUp()
        self.backend = self.env['stock_connector.backend'].create({
            'name': 'test',
            'version': '0.1',
        })

    def test_install_transports(self):
        transport_obj = self.env['stock_connector.transport']
        installed = transport_obj.select_versions()

        if not installed:
            _logger.info('There are no transports to test. '
                         'Import this file in your own module test folder')

        for version, name in installed:
            transport = transport_obj.create({
                'name': name,
                'version': version,
            })
            instance = transport.get_transport().setup(self.backend)
            wrong_msg = "Transport '{0}' is incomplete".format(version)
            self.assertIsNotNone(instance, wrong_msg)
            instance_methods = [x for x in dir(instance)]
            for method_name, method_args in [
                ('test_connection', ['self']),
                ('send_file', ['self', 'connector_file']),
                ('get_file', ['self', 'filename']),
                ('remove_file', ['self', 'filename']),
                ('change_dir', ['self', 'path']),
                ('list_dir', ['self']),
                ('open', ['self']),
                ('close', ['self']),
                ('__enter__', ['self']),
                ('__exit__', ['self', 'exc_type', 'exc_val', 'exc_tb']),
            ]:
                self.assertIn(method_name, instance_methods,
                              ': '.join([wrong_msg, method_name]))
                method = getattr(instance, method_name)
                self.assertTrue(callable(method))
                self.assertEquals(method_args, getargspec(method).args)
