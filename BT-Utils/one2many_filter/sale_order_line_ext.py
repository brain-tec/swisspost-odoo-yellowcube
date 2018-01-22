# b-*- encoding: utf-8 -*-
##############################################################################
#
#    Copyright (c) 2014 brain-tec AG (http://www.brain-tec.ch)
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
from generic import make_safe
from openerp.tools.translate import _
from bt_helper.log_rotate import get_log
logger = get_log('DEBUG')

class sale_order_line_ext(osv.osv):

    _inherit = 'sale.order.line'
    _order = "is_discount asc,order_id desc, order_sequence, sequence, id"
    
    

    _columns = {
        'order_sequence': fields.text('Order sequence'),
        'is_discount': fields.boolean('Discount'),
    }
    _defaults = {
        'order_sequence': '',
        'is_discount': True,
    }

    
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
