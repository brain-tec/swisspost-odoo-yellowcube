# -*- coding: utf-8 -*-
##############################################################################
#
#    Copyright (c) 2016 brain-tec AG (http://www.braintec-group.com)
#    All Right Reserved
#
#    See LICENSE file for full licensing details.
##############################################################################
from openerp import models, fields, api
import logging
_logger = logging.getLogger(__name__)


class StockConnectorTransport(models.Model):
    _name = 'stock_connector.transport'
    _description = 'Data Transport'

    name = fields.Char()
    version = fields.Selection(selection='select_versions',
                               required=True, default=False)

    @api.model
    def select_versions(self):
        """
        Version key is the model name associated with the transport

        :return: list of version that can be used
        """
        return []

    def get_transport(self):
        return self.env[self.version]
