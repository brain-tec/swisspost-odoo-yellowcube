# b-*- encoding: utf-8 -*-
##############################################################################
#
#    Copyright (c) 2014 brain-tec AG (http://www.braintec-group.com)
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
#############################################################################
import test_res_partner_rules
import test_product_product_rules
import test_sale_order_rules
import test_account_invoice_rules
import test_stock_picking_in_rules
import test_stock_picking_out_rules
import test_stock_picking_rules

checks = [test_res_partner_rules,
          test_product_product_rules,
          test_sale_order_rules,
          test_account_invoice_rules,
          test_stock_picking_in_rules,
          test_stock_picking_out_rules,
          test_stock_picking_rules,
          ]
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: