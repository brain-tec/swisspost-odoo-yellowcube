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
##############################################################################

from openerp.osv import osv, fields
from openerp.tools.translate import _


class configuration_data_ext(osv.Model):
    _inherit = 'configuration.data'

    _columns = {
        'yc_ignore_events_until_process_date': fields.boolean('Ignore Events Until Its Process Date Is Met?'),
        'yc_customer_order_no_mode': fields.selection([('id', 'ID of Stock Picking'),
                                                       ('name', 'Name of Order & Name of Delivery'),
                                                       ], string='CustomerOrderNo Mode',
                                                      help="Content of the CustomerOrderNo field for the WAB/WAR. "
                                                           "If 'ID of Stock Picking', then the internal ID of the database is used. "
                                                           "If 'Name of Order & Name of Purchase', then it is the concatenation of "
                                                           "the name of the sale/purchase order and the name of the delivery"),

        'mapping_bur_transactiontypes_ids': fields.one2many('mapping_bur_transactiontypes', 'configuration_id', string="Mapping from BUR-TransactionTypes",
                                                            help="Configurable mapping from BUR-TransactionTypes to default source and destination locations."),
    }

    _defaults = {
        'yc_ignore_events_until_process_date': False,
        'yc_customer_order_no_mode': 'name',
    }

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
