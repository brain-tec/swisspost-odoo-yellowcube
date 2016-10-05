# -*- coding: utf-8 -*-
##############################################################################
#
#    Copyright (c) 2016 brain-tec AG (http://www.braintec-group.com)
#    All Right Reserved
#
#    See LICENSE file for full licensing details.
##############################################################################
from openerp import models, api
from .sftp_transport import SFTPTransport


class StockConnectorSftpTransport(models.AbstractModel):
    _name = 'stock_connector_sftp.transport'

    @api.model
    def setup(self, backend):
        return SFTPTransport(backend)
