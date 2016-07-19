# b-*- encoding: utf-8 -*-
##############################################################################
#
#    Copyright (c) 2015 brain-tec AG (http://www.brain-tec.ch)
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
from openerp.tools.translate import _
import logging
logger = logging.getLogger(__name__)


class res_partner_ext(osv.Model):
    _inherit = 'res.partner'

    def check_partner_ref_value(self, cr, uid, ids):
        for partner in self.browse(cr, uid, ids):
            if not partner.ref:
                partner.write({'ref': 'partner_{0}'.format(partner.id)})
        return True

    _columns = {
        'yc_supplier_no': fields.char('YC SupplierNo'),
    }

    _constraints = [
        (check_partner_ref_value, 'When possible, the partner reference must be set', ['ref'])
    ]

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
