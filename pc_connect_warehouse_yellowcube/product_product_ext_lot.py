# b-*- encoding: utf-8 -*-
##############################################################################
#
#    Copyright (c) 2015 brain-tec AG (http://www.braintec-group.com)
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
##############################################################################
from openerp.osv import osv, fields


class product_product_ext_lot(osv.Model):
    _inherit = 'product.product'

    def check_product_lot_expiry_dates(self, cr, uid, locations_to_consider=None, context=None):
        ''' Overrides the main method to add 'YellowCube' to the locations to consider.
        '''
        if locations_to_consider is None:
            locations_to_consider = []
        if 'YellowCube' not in locations_to_consider:
            locations_to_consider.append('YellowCube')
        return super(product_product_ext_lot, self).check_product_lot_expiry_dates(cr, uid, locations_to_consider, context=context)

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
