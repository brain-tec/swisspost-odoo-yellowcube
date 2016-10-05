# -*- coding: utf-8 -*-
##############################################################################
#
#    Copyright (c) 2016 brain-tec AG (http://www.braintec-group.com)
#    All Right Reserved
#
#    See LICENSE file for full licensing details.
##############################################################################
from openerp import models, api
from .ycmockup_transport import YCMockupTransport


class StockConnectorYCMockupTransport(models.AbstractModel):
    _name = 'stock_connector_yellowcube_mockup.transport'

    @api.model
    def setup(self, backend):
        return YCMockupTransport(backend)
