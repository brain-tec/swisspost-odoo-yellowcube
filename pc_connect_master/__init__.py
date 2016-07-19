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

import sys
import base
sys.modules['addons.base'] = base

import account_invoice_ext
import company_support_config
import config_setting_ext
import configuration_data_ext
import delivery_carrier_ext
import gift_text_type
import ir_attachment_ext
import ir_cron_ext
import ir_cron_punchcard
import ir_filters_ext
import mail_thread_ext
import payment_method_ext
import product_product_ext
import product_template_ext
import product_uom_ext
import purchase_order_ext
import queue_job_ext
import queue_worker_ext
import report_file_exporter
import res_company_ext
import res_partner_bank_ext
import res_partner_ext
import res_partner_title_ext
import sale_order_ext
import sale_order_line_ext
import stock_move_ext
import stock_picking_ext
import stock_picking_in_ext
import stock_picking_out_ext
import stock_production_lot_ext
import stock_warehouse_ext
import utilities
import wizard

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
