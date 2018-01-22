# b-*- encoding: utf-8 -*-
##############################################################################
#
#    Copyright (c) 2016 brain-tec AG (http://www.braintec-group.com)
#    All Right Reserved
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
###############################################################################

from openerp.osv import osv, fields
from openerp.addons.pc_generics import generics


@generics.has_mako_header()
class purchase_order_ext(osv.Model):

    _inherit = 'purchase.order'

    def print_quotation(self, cr, uid, ids, context=None):
        """ Overridden so that we use the report defined on the configuration for purchases,
            or the default one if no one is defined there.
        """
        res = super(purchase_order_ext, self).print_quotation(cr, uid, ids, context=context)

        conf_data = self.pool.get('configuration.data').get(cr, uid, [], context=context)
        purchase_order_report_name = conf_data.report_purchase_order.report_name
        if purchase_order_report_name:
            res['report_name'] = purchase_order_report_name
        return res

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
