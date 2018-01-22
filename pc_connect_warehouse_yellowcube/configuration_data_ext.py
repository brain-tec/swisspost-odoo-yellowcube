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

YC_CUSTOMER_ORDER_NO_NAME = [
    ('id', 'ID of Stock Picking'),
    ('extref', 'External Reference & Abrev. Delivery'),
    ('name', 'Name of Order & Name of Delivery'),
    ('order', 'Name of the Order'),
]


class configuration_data_ext(osv.Model):
    _inherit = 'configuration.data'

    _columns = {
        'yc_ignore_events_until_process_date': fields.boolean('Ignore Events Until Its Process Date Is Met?'),
        'yc_customer_order_no_mode': fields.selection(
            YC_CUSTOMER_ORDER_NO_NAME, string='CustomerOrderNo Mode',
            help="Option to chose how the external delivery reference used as "
                 "CustomerOrderNo in WAB/WAR and SupplierOrderNo in WBL/WBA "
                 "is calculated.\n"
                 "With 'ID of Stock Picking', the internal ID of the delivery "
                 "is used.\n"
                 "With 'External Reference & Abrev. Delivery', it's the last "
                 "part of the name of the sale / purchase order split by a "
                 "'-' (which is usually the web-shop or supplier reference), "
                 "which is only for outgoing deliveries concatenated with "
                 "the last 5 digits of the name of the delivery.\n"
                 "With 'Name of Order & Name of Delivery', for outgoing "
                 "deliveries it is the concatenation of the name of the sale "
                 "order and the name of the delivery, for incoming deliveries "
                 "it is just the name of the purchase order.\n"
                 "With 'Name of the Order', it is the name of the "
                 "associated sale/purchase order only (note: only viable if "
                 "no backorders or delivery splitting is used!)."),

        'mapping_bur_transactiontypes_ids': fields.one2many(
            'mapping_bur_transactiontypes', 'configuration_id', 
            string="Mapping from BUR-TransactionTypes",
            help="Configurable mapping from BUR-TransactionTypes to default "
                 "source and destination locations."),

        # Fields for the functionality which sends an email after receiving
        # the WAR file from the warehouse.
        'tracking_email_active': fields.boolean(
            "Email carrier reference to customer?",
            help="If this option is activated an email to the customer "
                 "containing the carrier reference is sent as the "
                 "confirmation of the delivery is received. To activate "
                 "this function, the email template to be used and the "
                 "carrier reference template must be configured too!"),
        'tracking_email_template_id': fields.many2one(
            "email.template", "Delivery email template",
            help="This is the template used to inform the customer about "
                 "the sent delivery. It will contain the carrier reference "
                 "if it is correctly configured."),
    }

    _defaults = {
        'yc_ignore_events_until_process_date': False,
        'yc_customer_order_no_mode': 'name',
    }

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
