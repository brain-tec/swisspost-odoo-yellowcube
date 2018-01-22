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


from . import test_sale_order_automation
from . import test_assignations_one_and_direct
from . import test_soa_with_picking_split
from . import test_saleorder_invoice_open
import common

checks = [
    test_sale_order_automation,
    test_assignations_one_and_direct,
    test_soa_with_picking_split,
    test_saleorder_invoice_open,
]

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
