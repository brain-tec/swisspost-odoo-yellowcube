# -*- coding: utf-8 -*-
##############################################################################
#
#    Copyright (c) 2016 brain-tec AG (http://www.braintec-group.com)
#    All Right Reserved
#
#    See LICENSE file for full licensing details.
##############################################################################
from openerp.tests import TransactionCase
from openerp.addons.stock_connector_yellowcube.models.backend_processor_ext\
    import CheckBackends
import logging
_logger = logging.getLogger(__name__)


class TestBase(TransactionCase):

    def setUp(self):
        super(TestBase, self).setUp()
        CheckBackends()
        # We create the basic backend
        self.backend = self.env['stock_connector.backend'].create({
            'name': 'Backend YC Test',
            'version': '0.1-yellowcube-1.0',
            # YC parameters
            'yc_parameter_depositor_no': '0000054321',
            'yc_parameter_partner_no': '0000300020',
            'yc_parameter_plant_id': 'Y004',
            'yc_parameter_receiver': 'YELLOWCUBE',
            'yc_parameter_sender': 'YCTest',
            'yc_parameter_operating_mode': 'T',
        })
        # We set a partner with very strange name an address
        self.partner_customer = self.browse_ref('base.res_partner_address_4')
        self.partner_customer.name += u'xçÇäÜ\u039B\u03A9x'
        self.partner_customer.city += u'xçÇäÜ\u039B\u03A9x'
        self.partner_customer.street += u'xçÇäÜ\u039B\u03A9x'
