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
from openerp.tools.translate import _


_DATE_SELECTION = [('days', 'Day(s)'),
                   ('weeks', 'Week(s)'),
                   ('months', 'Month(s)'),
                   ('years', 'Year(s)'),
                   ]


class configuration_data_ext(osv.Model):
    _inherit = 'configuration.data'

    _columns = {
        # Reports
        'report_account_invoice': fields.many2one('ir.actions.report.xml', "Invoice", domain=[('model', '=', 'account.invoice')]),
        'report_stock_picking': fields.many2one('ir.actions.report.xml', "Delivery", domain=[('model', '=', 'stock.picking.out')]),
        'report_purchase_order': fields.many2one('ir.actions.report.xml', "Purchase Order", domain=[('model', '=', 'purchase.order')]),

        'invoice_report_show_bvr_when_zero_amount_total': fields.boolean(
            'Print BVR if Amount Total is Zero?',
            help='If checked, it show the BVR always on invoices with '
                 'an amount of zero with only the field for the quantity '
                 'being blank (NOT voided, but empty).'),

        # Dates
        'post_default_expiration_block_time': fields.integer('Default Expiration Block Time'),
        'post_default_expiration_block_time_uom': fields.selection(_DATE_SELECTION, 'Default Expiration Block Time UOM'),
        'post_default_expiration_alert_time': fields.integer('Default Expiration Alert Time'),
        'post_default_expiration_alert_time_uom': fields.selection(_DATE_SELECTION, 'Default Expiration Alert Time UOM'),
        'post_default_expiration_accept_time': fields.integer('Default Expiration Accept Time'),
        'post_default_expiration_accept_time_uom': fields.selection(_DATE_SELECTION, 'Default Expiration Accept Time UOM'),

        # Payment method force
        'force_payment_term': fields.boolean('Force payment term based on Payment method'),
        'default_credit_limit': fields.float(string='Default Credit Limit',
                                             help='The global default credit limit applied to users with no credit limit set',
                                             required=True),
        'default_credit_limit_companies': fields.float(string='Default Credit Limit For Companies',
                                                       help='The global default credit limit applied to companies with no credit limit set',
                                                       required=True),

        # The email template to send the invoice to the partner.
        'invoice_to_partner_email_template_id': fields.many2one('email.template', 'Invoice to Partner Email Template', domain=[('model', '=', 'account.invoice')],
                                                                help='The email template for the email which sends the invoice to the partner.'),

        # The email template to send the purchase order to the supplier.
        'purchase_to_supplier_email_template_id': fields.many2one('email.template', 'Purchase Order to Supplier',
                                                                  domain=[('model', '=', 'purchase.order')],
                                                                  help='The email template for the email which sends the purchase order to the supplier.'),

        'purchase_alarming_days': fields.integer('Days from expected date to alarm',
                                                 help='Laboral days (according to the warehouse) to wait once the expected date '
                                                 'for a purchase order has been reached before an alarm is logged '
                                                 'over the purchase order.'),

        'purchase_schedule_date_consider_only_weekdays': fields.boolean('Make the Schedule Date consider only weekdays?',
                                                                        help='If checked, the Schedule Date of each line of a purchase order '
                                                                        'considers only the weekdays, i.e. it skips Saturdays and Sundays.'),

        'supplier_prefix_ref': fields.char('Supplier Prefix for Reference', help='Prefix that will be added to received reference in suppliers.'),

        'concurrent_access_requeue_num_minutes': fields.integer('Concurrent Access Requeue Max Minutes',
                                                                help='Stop requeueing a job automatically if it failed because of ' +
                                                                'a concurrent access and this amount of minutes passed since its creation.'),

        'ready_for_export_check_num_minutes': fields.integer('Ready for Export Max Minutes',
                                                             help="The number of minutes allowed between the creation of the picking "
                                                                  "and the moment in which we must alarm to indicate "
                                                                  "that too much time passed between the first check and the present moment."),

        'punchcards_limit': fields.integer('Max Number of Punchards', help='The maximum number of punchards to keep in the history of punchards.'),

        'keep_only_mister_and_madam_titles': fields.boolean("Keep Only 'Mister' and 'Madam' Titles for Contacts?",
                                                            help='If checked, when updating the modules only '
                                                                 'the titles Mister and Madam will be kept '
                                                                 'for res.partners of type contact.'),

        'default_picking_policy': fields.selection([('one', 'Force One Delivery'),
                                                    ('direct', 'Force Partial Deliveries'),
                                                    ('keep', 'According to Web-Shop'),
                                                    ], string='Global Picking Policy',
                                                   help="Whatever is set on this parameter will be set by default "
                                                        "in field 'picking_policy' of a sale.order when created, except "
                                                        "option 'keep', which means that the value indicated by the webshop "
                                                        "must be taken. It is just a default parameter, and can be "
                                                        "changed on the sale.order when editing it."),

        'open_backorder_alarming_age_days': fields.integer('Open Backorder Alarming Age (Days)',
                                                           help="Alarming threshold value which defines after how "
                                                                "many days an open back-order must be alarmed."),

        'execute_only_after_time_for_backorders': fields.float('Time for Execute Only After for Backorders', required=True,
                                                                 help='The time of the next day after which delayed backorders will be processed again.'),

        'illegal_lots_destination_id': fields.many2one('stock.location', 'Location for Illegal Lots', domain=[('scrap_location', '=', True)],
                                                       help='Location where illegal quantities are put. Must be a scraping location. '
                                                            'Here go quantities from lots which are from products which do not track_production, '
                                                            'or unlotted quantities from products which do track_production.'),

        'invoice_policy': fields.selection([('order', 'Invoice Ordered Quantities'),
                                            ('delivery', 'Invoice Delivered Quantities'),
                                            ], string='Invoicing Policy', required=True,
                                           help="Determines the invoicing policy, which will override the one defined on the sale order."),

        'gift_card_journal_id': fields.many2one(
            'account.journal', 'Journal for Gift-cards')
    }

    _defaults = {
        # dates
        'post_default_expiration_block_time': 10,
        'post_default_expiration_block_time_uom': 'Day(s)',
        'post_default_expiration_alert_time': 20,
        'post_default_expiration_alert_time_uom': 'Day(s)',
        'post_default_expiration_accept_time': 30,
        'post_default_expiration_accept_time_uom': 'Day(s)',
        'force_payment_term': True,
        'default_credit_limit': 1.0,
        'default_credit_limit_companies': 0.0,
        'concurrent_access_requeue_num_minutes': 10,
        'ready_for_export_check_num_minutes': 10,
        'punchcards_limit': 1000,
        'keep_only_mister_and_madam_titles': False,
        'default_picking_policy': 'one',
        'execute_only_after_time_for_backorders': 0.0,
        'purchase_alarming_days': 0,
        'purchase_schedule_date_consider_only_weekdays': False,
        'invoice_policy': 'order',
        'supplier_prefix_ref': 'LCHSUP-',
        'invoice_report_show_bvr_when_zero_amount_total': False,
    }

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
