# -*- coding: utf-8 -*-
##############################################################################
#
#    Copyright (c) 2016 brain-tec AG (http://www.braintec-group.com)
#    All Right Reserved
#
#    See LICENSE file for full licensing details.
##############################################################################
from openerp.tests import TransactionCase
import logging
_logger = logging.getLogger(__name__)


class TestBase(TransactionCase):

    def setUp(self):
        super(TestBase, self).setUp()
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
