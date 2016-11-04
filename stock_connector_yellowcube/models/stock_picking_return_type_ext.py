# -*- coding: utf-8 -*-
##############################################################################
#
#    Copyright (c) 2016 brain-tec AG (http://www.braintec-group.com)
#    All Right Reserved
#
#    See LICENSE file for full licensing details.
##############################################################################
from openerp import models, fields, api


class StockPickingReturnTypeExt(models.Model):
    _inherit = 'stock.picking.return_type'

    yc_code = fields.Char('YellowCube Code')

    @api.multi
    def name_get(self):
        ret = super(StockPickingReturnTypeExt, self).name_get()
        ret2 = []
        for result in ret:
            record_id = result[0]
            record = self.browse(record_id)
            name = result[1]
            if record.yc_code:
                name = '[%s] %s' % (record.yc_code, name)
            ret2.append((record_id, name))
        return ret2

    @api.model
    def name_search(self, name='', args=None, operator='ilike', limit=100):
        ret1 = super(StockPickingReturnTypeExt, self)\
            .name_search(name, args, operator, limit)
        domain = [
            '&',
            ('yc_code', operator, name),
            ('id', 'not in', [x[0] for x in ret1]),
        ]
        if args is not None:
            domain.extend(args)
        ids2 = self.search(domain)
        ret1.extend(self.browse(ids2.ids).name_get())
        print ret1
        return ret1
