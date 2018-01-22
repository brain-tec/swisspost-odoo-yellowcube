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
import v8_api
import openerp
from openerp.release import version_info
if not hasattr(openerp, 'api'):
    """
    This makes it possible to refer to some v8 decorators in v7. E.g.: @api.cr_uid_ids_context
    """
    setattr(openerp, 'api', v8_api)

import account_invoice_ext
import configuration_data_ext
import delivery_carrier_ext
import mapping_bur_transactiontypes
import product_product_ext
import product_product_ext_lot
import purchase_order_line_ext
import res_partner_ext
import sale_order_ext
import stock_connect_ext
import stock_connect_yellowcube
import stock_picking_ext
import stock_move_ext
import stock_return_picking_ext
import stock_warehouse_ext
import stock_production_lot_ext
import xml_abstract_factory
import yellowcube_art_xml_factory
import yellowcube_bar_xml_factory
import yellowcube_bur_xml_factory
import yellowcube_wab_xml_factory
import yellowcube_war_xml_factory
import yellowcube_wba_xml_factory
import yellowcube_wbl_xml_factory
import ir_module_module_ext
import wizard

if version_info[0] <= 7:
    import stock_picking_inout_ext

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: