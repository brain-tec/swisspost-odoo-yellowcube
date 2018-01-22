# -*- coding: utf-8 -*-
#
#    Copyright (c) 2017 brain-tec AG (http://www.braintec-group.com)
#    All Right Reserved
#
#    See LICENSE file for full licensing details.
from openerp.tests.common import SingleTransactionCase
from openerp import SUPERUSER_ID


class APITestCase(SingleTransactionCase):
    def _api_call(self, *args, **kwargs):
        return self.connect_transport_api.api_call(*args, **kwargs)

    def setUp(self):
        super(APITestCase, self).setUp()

    @classmethod
    def setUpClass(cls):
        super(APITestCase, cls).setUpClass()

        connect_transport_api = cls.registry('connect.transport.api')

        cls.profile = connect_transport_api.search(cls.cr, SUPERUSER_ID, [])[0]
        cls.external_uid = connect_transport_api.read(
            cls.cr, SUPERUSER_ID, cls.profile, ['external_user_id']
        )['external_user_id'][0]
        cls.connect_transport_api = connect_transport_api.browse(
            cls.cr, cls.external_uid, cls.profile)

        cls.cr.commit()

    @classmethod
    def tearDownClass(cls):
        super(APITestCase, cls).tearDownClass()
