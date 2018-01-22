# b-*- encoding: utf-8 -*-
##############################################################################
#
#    Copyright (c) 2017 brain-tec AG (http://www.braintec-group.com)
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

from osv import osv, fields
from openerp.tools.translate import _


class sale_order_check_credit_ext(osv.TransientModel):
    _inherit = 'sale.order.check_credit'

    def _do_credit_check_get_result(self, cr, uid, ids, context=None):
        """ Overridden so that it checks first that the credentials for Intrum
            are set.
        """
        conf = self.pool.get('configuration.data').get(
            cr, uid, [], context=context)
        if conf.check_intrum_credentials_are_set():
            result = super(sale_order_check_credit_ext, self).\
                _do_credit_check_get_result(cr, uid, ids, context=context)
        else:
            result = _('The credentials for Intrum are not set, so the '
                       'credit check can not proceed.')

        return result

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
