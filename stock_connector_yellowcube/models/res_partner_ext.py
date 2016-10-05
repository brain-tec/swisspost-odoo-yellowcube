# -*- coding: utf-8 -*-
##############################################################################
#
#    Copyright (c) 2016 brain-tec AG (http://www.braintec-group.com)
#    All Right Reserved
#
#    See LICENSE file for full licensing details.
##############################################################################
from openerp import models, fields


class ResPartnerExt(models.Model):
    _inherit = 'res.partner'

    yc_supplier_no = fields.One2many('stock_connector.binding', 'res_id',
                                     domain=[('res_model', '=', 'res.partner'),
                                             ('group', '=', 'yc_SupplierNo')],
                                     string='Supplier Number'
                                     )
