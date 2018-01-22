# -*- coding: utf-8 -*-
#
#    Copyright (c) 2017 brain-tec AG (http://www.braintec-group.com)
#    All Right Reserved
#
#    See LICENSE file for full licensing details.

from openerp.osv.orm import Model
from openerp.osv import fields


class StockConnectFileExt(Model):
    _inherit = 'stock.connect.file'

    _columns = {
        'connect_transport_profile': fields.many2one('connect.transport.api',
                                           'Connect Transport Profile'),
    }
