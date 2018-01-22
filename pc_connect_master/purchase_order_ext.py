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
##############################################################################

from openerp.osv import osv, fields
from openerp.addons.pc_connect_master.utilities.date_utilities import get_number_of_natural_days
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT, DEFAULT_SERVER_DATETIME_FORMAT
from openerp.tools.translate import _
from datetime import datetime, timedelta
import logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


class purchase_order_ext(osv.Model):
    _inherit = "purchase.order"
    _name = "purchase.order"

    def get_draft_invoices(self, cr, uid, ids, context=None):
        """ Returns a list of IDs corresponding to the invoices associated to
            the current purchase order which are on state draft. If none is found,
            then returns the empty list.

            Must receive just one ID. If a list of IDs is received,
            then it just takes the first one.
        """
        if context is None:
            context = {}
        if type(ids) is not list:
            ids = [ids]

        draft_invoice_ids = []

        purchase = self.browse(cr, uid, ids[0], context=context)
        for invoice in purchase.invoice_ids:
            if invoice.state == 'draft' and invoice.type == 'in_invoice':
                draft_invoice_ids.append(invoice.id)

        return draft_invoice_ids

    def button_dummy(self, cr, uid, ids, context=None):
        """ Overridden so that the scheduled date for each purchase order line is updated
            every time we 'update' (by clicking on 'update') a purchase order.
        """
        purchase_order_line_obj = self.pool.get('purchase.order.line')

        res = super(purchase_order_ext, self).button_dummy(cr, uid, ids, context)

        for purchase in self.browse(cr, uid, ids, context=context):
            for purchase_line in purchase.order_line:

                # Gets the supplier info for this product.
                supplier_info = False
                for supplier in purchase_line.product_id.seller_ids:
                    if supplier.name.id == purchase.partner_id.id:
                        supplier_info = supplier
                        break

                date_planned = purchase_order_line_obj._get_date_planned(cr, uid, supplier_info, purchase.date_order, context=context).strftime(DEFAULT_SERVER_DATETIME_FORMAT)
                purchase_line.write({'date_planned': date_planned})

        return res

    def wkf_send_rfq(self, cr, uid, ids, context=None):
        """ Overridden so that we can indicate which templates to use.
        """
        if context is None:
            context = {}

        # Gets the ID of the template to use.
        conf_data = self.pool.get('configuration.data').get(cr, uid, [], context=context)
        purchase_to_supplier_email_template_id = conf_data.purchase_to_supplier_email_template_id.id

        action_dict = super(purchase_order_ext, self).wkf_send_rfq(cr, uid, ids, context=context)
        action_dict['context']['default_template_id'] = purchase_to_supplier_email_template_id
        action_dict['context']['default_use_template'] = bool(purchase_to_supplier_email_template_id)

        return action_dict

    def _set_destination_location(self, cr, uid, ids, context=None):
        """ Sets the destination of the purchase orders to be the
            input location of its destination warehouse.
        """
        if context is None:
            context = {}
        if type(ids) is not list:
            ids = [ids]

        for purchase_order in self.browse(cr, uid, ids, context=context):
            input_location_of_warehouse = purchase_order.warehouse_id.lot_input_id
            if purchase_order.location_id != input_location_of_warehouse:
                self.write(cr, uid, purchase_order.id, {'location_id': input_location_of_warehouse.id}, context=context)
        return True

    def cron_merge_and_alarm_purchase_orders(self, cr, uid, context=None):
        """ Merges purchase orders from the same supplier AND
            alarms those purchase orders that should have been received but were not.
        """
        self._merge_purchase_orders(cr, uid, context)
        self._alarm_purchase_orders(cr, uid, context)
        return True

    def _alarm_purchase_orders(self, cr, uid, context=None):
        """ Alarms those purchase orders that should have been received but were not.
        """
        if context is None:
            context = {}

        issue_obj = self.pool.get('project.issue')

        configuration_data = self.pool.get('configuration.data').get(cr, uid, [], context=context)
        num_extra_days_to_wait = configuration_data.purchase_alarming_days or 0
        support_weekdays = configuration_data.get_open_days_support(context=context)
        now = datetime.now()
        today = datetime.today().date()

        # We filter also for the flag which stores if the purchase was alarmed to
        # avoid spamming the user every time this method is called.
        candidate_purchases_to_alarm_domain = [('alarmed_for_not_received', '=', False),
                                               ('state', '=', 'approved'),
                                               ('minimum_planned_date', '!=', False),
                                               ]

        candidate_purchases_to_alarm_ids = self.search(cr, uid, candidate_purchases_to_alarm_domain, context=context)
        for purchase in self.browse(cr, uid, candidate_purchases_to_alarm_ids, context=context):
            number_of_actual_days = get_number_of_natural_days(now, num_extra_days_to_wait, 'forward', support_weekdays)
            limit_date = (
            datetime.strptime(purchase.minimum_planned_date, DEFAULT_SERVER_DATE_FORMAT) + timedelta(
                days=number_of_actual_days)).date()
            if today > limit_date:
                alarm_message = _('Purchase Order with ID={0} should have been received, but was not.').format(
                    purchase.id)
                purchase.message_post(alarm_message, context=context)

                issue_ids = issue_obj.find_resource_issues(cr, uid, 'purchase.order', purchase.id,
                                                           tags=['purchase.order', 'procurements'],
                                                           create=True, reopen=True, context=context)
                for issue in issue_obj.browse(cr, uid, issue_ids, context=context):
                    issue.message_post(alarm_message, context=context)

                purchase.write({'alarmed_for_not_received': True})

        return True

    def _merge_purchase_orders(self, cr, uid, context=None):
        """ Merges purchase orders from the same supplier.
        """
        if context is None:
            context = {}

        not_merged_purchase_orders_domain = [('purchase_order_merged', '=', False),
                                             ('state', '=', 'draft'),
                                             ]

        # Sets the destination of the purchase orders.
        purchase_to_merge_ids = self.search(cr, uid, not_merged_purchase_orders_domain, context=context)
        self._set_destination_location(cr, uid, purchase_to_merge_ids, context)

        # Does the merge of the purchase orders.
        logger.debug("Purchase orders to merge: {0}".format(purchase_to_merge_ids))
        purchase_merged_dict = self.do_merge(cr, uid, purchase_to_merge_ids, context=context)
        purchase_merged_ids = []
        for new_puchase_merged in purchase_merged_dict:
            purchase_merged_ids.extend(purchase_merged_dict[new_puchase_merged])
        self.write(cr, uid, purchase_merged_ids, {'purchase_order_merged': True})
        logger.debug("Purchase orders merged: {0}".format(purchase_merged_ids))

        return True

    _columns = {
        # This field 'purchase_order_merged' was before named 'procurement_mail_sent, which
        # obviously (having a look at the code) was a confusing name.
        'purchase_order_merged': fields.boolean('Purchase Order Merged'),

        'alarmed_for_not_received': fields.boolean('Alarmed for Not Receiving It?',
                                                   help='Did the purchase order result in an alarm because of '
                                                   'not having received it an mount of days after the expected '
                                                   'delivery date was reached? You can set the amount of days '
                                                   'in the configuration.'),
    }

    _defaults = {
        'purchase_order_merged': False,
        'alarmed_for_not_received': False,
    }

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
