# -*- coding: utf-8 -*-
##############################################################################
#
#    Copyright (c) 2016 brain-tec AG (http://www.braintec-group.com)
#    All Right Reserved
#
#    See LICENSE file for full licensing details.
##############################################################################
from openerp import models, fields


class ProductProductExt(models.Model):
    _inherit = 'product.product'

    yc_article_no = fields.\
        One2many('stock_connector.binding', 'res_id',
                 domain=[('res_model', '=', 'product.product'),
                         ('group', '=', 'YCArticleNo')],
                 string='YCArticleNo')
