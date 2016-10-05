# -*- coding: utf-8 -*-
##############################################################################
#
#    Copyright (c) 2016 brain-tec AG (http://www.braintec-group.com)
#    All Right Reserved
#
#    See LICENSE file for full licensing details.
##############################################################################
from openerp import models, api, fields


class StockConnectorTransportExt(models.Model):
    _inherit = 'stock_connector.transport'

    sftp_password = fields.Char('Password')
    sftp_username = fields.Char('Username')
    sftp_rsa_key = fields.Text('RSA key')
    sftp_path = fields.Char('Path')

    @api.model
    def select_versions(self):
        """
        Version key is the model name associated with the transport

        :return: list of version that can be used
        """
        ret = super(StockConnectorTransportExt, self).select_versions()
        ret.append(('stock_connector_sftp.transport', 'Secure FTP'))
        return ret
