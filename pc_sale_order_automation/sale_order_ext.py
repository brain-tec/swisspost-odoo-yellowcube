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

from openerp.osv import osv, fields, orm
import netsvc
from openerp.tools.translate import _
from openerp.tools \
    import DEFAULT_SERVER_DATE_FORMAT, DEFAULT_SERVER_DATETIME_FORMAT
from openerp.tools.safe_eval import safe_eval
from openerp.addons.connector.session import ConnectorSession
from openerp.addons.connector.queue.job import job
from openerp.addons.pc_connect_master.utilities.others import \
    format_exception
from openerp.addons.pc_log_data.log_data import write_log
from openerp.addons.pc_connect_master.utilities.date_utilities \
    import get_next_day_datetime, get_hours_minutes_from_float
from datetime import datetime, timedelta
import pytz
import os
from StockMoveInstruction \
    import goods_are_available, backorder_has_to_be_created
import logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


JOB_DELAYED_MESSAGE = 'Job delayed'


class SaleOrderAutomationResult:
    def __init__(self):
        self.message = ''
        self.next_state = False
        self.next_state_time = 0
        self.error = False
        self.delay = False

    def __iadd__(self, other):
        """ Overloads the += operator.
        """
        if other.message:
            self.message = '{0}{1}{2}'.\
                format(self.message, os.linesep,
                       other.message)  # Messages are appended.
        self.next_state = other.next_state  # Overridden.
        self.next_state_time = other.next_state_time  # Overridden.
        self.error = self.error or other.error  # Propagated.
        self.delay = self.delay or other.delay  # Propagated.
        return self


@job
def automate_sale_order_process(
        session, model_name, record_id, state,
        next_state_time=0, backorder_id=0):
    """ Sale Order Automation """
    ctx = session.context.copy()
    automation_result = session.pool.get(model_name).automate_sale_order(
        session.cr, session.uid, record_id, state, next_state_time,
        backorder_id, ctx)

    if automation_result.error:
        raise Warning('{0}\n{1}'.format(automation_result.error,
                                        automation_result.message))

    # If the job has to be delayed, then the next state will be again
    # the one that caused the delay.
    if automation_result.delay:
        automation_result.next_state = state

    if not automation_result.next_state:
        message = _('Finished automated process.')
    else:
        if type(next_state_time) is str:
            next_state_time = 0

        # The following states do not allow an override of the scheduled date.
        # Otherwise we can do it.
        if state not in (
            'saleorder_check_inventory_for_quotation',
            'saleorder_draft',
            'deliveryorder_assignation_direct',
        ):
            next_state_time = 0
            automation_result.next_state_time = 0
        # We arrive to the following states directly without waiting.
        if automation_result.next_state in ('do_multi_parcel_deliveries'):
            next_state_time = 0
            automation_result.next_state_time = 0

        job_priority = session.pool.get('sale.order').get_soa_priority(
            session.cr, session.uid, record_id, context=ctx)

        automate_sale_order_process.delay(
            session, 'sale.order', record_id, automation_result.next_state,
            next_state_time, backorder_id,
            eta=automation_result.next_state_time or next_state_time,
            priority=job_priority)

        message = \
            _('Moving to state: {0}').format(automation_result.next_state)
        if type(automation_result.message) is str:
            message = '{0}\n\n{1}'.format(automation_result.message, message)
    logger.debug("Sale order automation ID={0}: {1}".format(
        record_id, message.replace('\n', '\\n')))
    return message


class sale_order_ext(osv.Model):
    _inherit = 'sale.order'

    def write(self, cr, uid, ids, values, context=None):
        """ Checks the sale.order's automation flag.
        """
        if 'automate_sale_order_process' in values:
            automate = values['automate_sale_order_process']
            if automate:
                self.enable_saleorder_automation(
                    cr, uid, ids, context=context)
            else:
                self.disable_saleorder_automation(
                    cr, uid, ids, context=context)

        return super(sale_order_ext, self).\
            write(cr, uid, ids, values, context=context)

    def create(self, cr, uid, values, context=None):
        """ Checks the sale.order's automation flag and tries
            to guess the webshop reference number.
        """
        # The webshop reference number is sent attached to the name of the
        # sale order, separated from it by a dash character. So, if we find
        # a dash in the name of the sale order, it is likely (although not
        # sure) that it is the webshop reference number.
        if values.get('name', ''):
            sale_order_name = values['name']
            last_dash_index = sale_order_name.rfind('-')
            if last_dash_index:
                possible_webshop_ref = sale_order_name[last_dash_index+1:]
                if possible_webshop_ref:  # We strip the '-'
                    values.update({
                        'possible_webshop_ref': possible_webshop_ref,
                    })

        id_ = super(sale_order_ext, self).\
            create(cr, uid, values, context=context)

        if values.get('automate_sale_order_process', False):
            self.enable_saleorder_automation(cr, uid, id_, context=context)

        return id_

    def copy(self, cr, uid, ids, defaults={}, context=None):
        """ Copied sale.orders are not automated, by default.
        """
        _defaults = {'automate_sale_order_process': False,
                     'automate_sale_order_process_fired': False,
                     }
        _defaults.update(defaults)
        return super(sale_order_ext, self).\
            copy(cr, uid, ids, _defaults, context=context)

    def test_ignore_invoice_exceptions(self, cr, uid, ids):
        """ This is a new transition in the workflow added so that invoices
            which are associated to a sale.order, when cancelled, do not
            stop the workflow of a sale.order in the state invoice_except
            waiting for a manual intervention of the user (something that we
            try to minimise here).
                Workflows have no context, that's why it's missing.
        """
        conf = self.pool.get('configuration.data').get(cr, uid, [])
        return conf.soa_ignore_inv_excep

    def get_soa_priority(self, cr, uid, ids, context=None):
        """ By default the priority of a sale order is its ID, this way
            the ones that were newer come first.
        """
        if context is None:
            context = {}
        if not isinstance(ids, list):
            ids = [ids]

        order = self.browse(cr, uid, ids[0], context=context)
        priority = order.id
        # if order.stock_type_id and order.stock_type_id.route in ('c+c', 'c+r'):
        #     priority -= 1000  # We prioritise C+C & C+R.

        return priority

    def test_ignore_shipping_exceptions(self, cr, uid, ids):
        """ This is a new transition in the workflow added so that pickings
            which are associated to a sale.order, when cancelled, do not
            stop the workflow of a sale.order in the state shipping_except
            waiting for a manual intervention of the user (something that we
            try to minimise here).
                Workflows have no context, that's why it's missing.
        """
        conf = self.pool.get('configuration.data').get(cr, uid, [])
        return conf.soa_ignore_ship_excep

    def automate_sale_order(self, cr, uid, ids, state, next_state_time,
                            backorder_id, context=None):
        """ This is the scheduler which makes the sale.order move
            through the steps of the Sale Order Automation (SOA).
        """
        if context is None:
            context = {}
        if type(ids) is not list:
            ids = [ids]

        try:
            order = self.browse(cr, uid, ids[0], context=context)

            if not order.is_dropship():
                # If the sale.order doesn't require dropship then we have to
                # take care to obtain the goods from the warehouses associated
                # to the shops indicated in the sale.order; otherwise we
                # risk taking quantities that are not reserved for us.
                context.update({'shop': order.shop_id.id})

            soa_info = SaleOrderAutomationResult()

            logger.debug("Automating sale.order with ID={0}.".format(order.id))

            if order.state == 'cancel':
                # The sale.order was cancelled before.
                soa_info.message = \
                    _("Sale order was cancelled, and will be ignored.")
                soa_info.next_state = False

                log_msg = _("Transition from state {0} ignored, "
                            "as sale order is Cancelled.").format(state)
                write_log(self, cr, uid, 'sale.order', order.name, order.id,
                          log_msg, True, soa_info.message)

            elif state == 'saleorder_check_inventory_for_quotation':
                order.check_if_check_inventory_for_quotation(soa_info)

            elif state == 'saleorder_checkcredit':
                order.check_if_credit_check(soa_info)

            elif state == 'saleorder_draft':
                order._process_workflow_saleorder_draft_to_sent(soa_info)

            elif state == 'saleorder_sent':
                order._process_workflow_saleorder_sent_to_router(soa_info)

            elif state == 'deliveryorder_assignation_one':
                order.do_assignation_one(soa_info)

            elif state == 'deliveryorder_assignation_direct':
                order.do_assignation_direct(backorder_id, soa_info)

            elif state == 'deliveryorder_assignation_dropship':
                order.do_assignation_dropship(soa_info)

            elif state == 'do_multi_parcel_deliveries':
                # We may skip this step from any of the three possible
                # previous ones (_one, _direct and _dropship) if the
                # packaging is not activated.
                order.check_doing_multi_parcel_deliveries(soa_info)

            elif state == 'print_deliveryorder_in_local':
                order._print_deliveryorder_in_local(soa_info)

            elif state == 'invoice_open':
                order.invoice_open_routing(backorder_id, soa_info)

            elif state == 'print_invoice_in_local':
                # This is the last step of the SOA in the new code.
                # The name is kept because of historical reasons, but
                # it also prints 'remotely' the invoice (or, best said,
                # prepares it to be printed remotely by the scheduler which
                # does this).
                soa_info.message = 'Prints the invoices and finishes the SOA.'
                order._print_invoice_in_local(soa_info)
                order._print_invoice_in_remote(backorder_id, soa_info)

            elif state == 'print_in_remote':
                # This ELIF is here just for backwards compatibility, only
                # for those jobs that already existed in this state when
                # the deployment was done. It can be removed a few days/weeks
                # after the new code has been deployed on all the servers.
                order._print_invoice_in_remote(backorder_id, soa_info)

            elif state == 'finish_saleorder_automation':
                # This ELIF is here just for backwards compatibility, only
                # for those jobs that already existed in this state when
                # the deployment was done. It can be removed a few days/weeks
                # after the new code has been deployed on all the servers.
                order._finish_saleorder_automation(soa_info)

            else:
                raise Exception(
                    _("Option '{0}' is not allowed "
                      "for the sale.order automation.").format(state))

            write_log(
                self, cr, uid, 'sale.order', order.name,
                order.id,
                _('Successful transition from state {0}').format(state), True,
                soa_info.message)

        except Exception as e:
            exception_msg = \
                _("An error happened while updating a sale.order "
                  "record with ID={0}\n{1}").format(
                    order.id, format_exception(e))
            soa_info.error = exception_msg
            # We attempt to repeat the current state.
            soa_info.next_state = state
            logger.exception(exception_msg)
            write_log(
                self, cr, uid, 'sale.order', order.name, order.id,
                _('Exception'), False, exception_msg)

        return soa_info

    def has_unique_webshop_reference(self, cr, uid, ids, context=None):
        """ This checks whether the sale.order must be rejected because of
            the existence of any other sale.order which has the same webshop
            reference, which means that the webshop sent by mistake two
            times the same sale.order.
                In order to prevent it, and if we have indicated in the
            configuration that we want to control this, then we check if
            the sale order has a webshop reference set and if the flag for
            the manual validation was not set. If those conditions apply,
            then we search to know if the webshop ref is unique, and if
            it is not then it logs an issue.
        """
        if context is None:
            context = {}
        if type(ids) is not list:
            ids = [ids]

        configuration_data = self.pool.get('configuration.data').\
            get(cr, uid, [], context=context)
        project_issue_obj = self.pool.get('project.issue')

        webshops_references_are_unique = True
        if configuration_data.block_duplicated_quotations_from_webshop:
            for order in self.browse(cr, uid, ids, context=context):
                if not order.manually_force_validation and \
                        order.possible_webshop_ref:
                    search_domain = [
                        ('possible_webshop_ref',
                         '=', order.possible_webshop_ref),
                        ('id', '!=', order.id),
                        ('state', 'not in', ('draft', 'cancel')),
                    ]
                    exist_sale_orders_with_same_webshop_ref = self.search(
                        cr, uid, search_domain, count=True, limit=1,
                        context=context)

                    if exist_sale_orders_with_same_webshop_ref:
                        webshops_references_are_unique = False
                        issue_subject = \
                            _('Duplicated Webshop Reference for '
                              'Sale Order {0}').format(order.name)
                        issue_msg = \
                            _('The sale order {0} (with ID={1}) '
                              'has as the webshop reference {2},'
                              'which is already used in '
                              'other sale orders.').format(
                                order.name, order.id,
                                order.possible_webshop_ref)

                        project_issue_obj.create_issue(
                            cr, uid, 'sale.order', order.id, issue_msg,
                            issue_subject=issue_subject,
                            tags=['sale.order', 'duplicated-webshop-ref'],
                            create=True,  reopen=True, context=context)

        return webshops_references_are_unique

    def do_credit_check(self, cr, uid, ids, context=None):
        """ Returns whether a sale.order requires to make a credit check.

            A sale order requires to do a credit check if it does not
            have a stock.type set, or it has it and it requires a credit check,
            AND also the payment method requires a credit check.
        """
        if context is None:
            context = {}
        if type(ids) is not list:
            ids = [ids]

        order = self.browse(cr, uid, ids[0], context=context)
        stock_type = order.stock_type_id or False

        return (not stock_type or stock_type.credit_check) and \
            order.payment_method_id.credit_check

    def check_if_credit_check(self, cr, uid, ids, soa_info, context=None):
        """ This checks whether the sale.order must be rejected because of the
            partner lacking credit worthiness.

            If it is rejected, it must remain in state 'draft'. We do this
            using a side sale.order exception.
        """
        if context is None:
            context = {}
        if type(ids) is not list:
            ids = [ids]

        order = self.browse(cr, uid, ids[0], context=context)
        stock_type = order.stock_type_id or False

        if (not stock_type) or stock_type.credit_check:
            rejected = self.is_sale_order_rejected_because_of_creditworthiness(
                cr, uid, ids[0], context=context)

            if rejected:
                soa_info.error = True
                soa_info.message = \
                    _("Sale.order was rejected because of "
                      "the credit-worthiness check.")
            else:
                soa_info.message = \
                    _("Sale.order was NOT rejected because of "
                      "the credit-worthiness check.")

        else:
            soa_info.message = _("Credit check skipped because of stock.type.")

        if soa_info.error:
            soa_info.next_state = 'saleorder_checkcredit'
        else:
            soa_info.next_state = 'saleorder_draft'
        return True

    def is_sale_order_rejected_because_of_creditworthiness(
            self, cr, uid, ids, context=None):
        """ This checks whether the sale.order must be rejected.
            If it is rejected, it must remain in state 'draft'.
        """
        if context is None:
            context = {}
        if type(ids) is not list:
            ids = [ids]

        project_issue_obj = self.pool.get('project.issue')

        order = self.browse(cr, uid, ids[0], context=context)

        # We update the sale.order. Some modules (e.g. stage_discount)
        # require a 'manual' updating.
        super(sale_order_ext, self).button_dummy(cr, uid, ids, context=context)

        error_message = ''
        try:
            # If the payment method requires to check the creditworthiness,
            # we need to check if we still have credit.
            if order.payment_method_id.credit_check:
                result = order.check_credit()
                if not result['decision']:
                    error_message = '{0}\n{1}\n{2}'.format(
                        error_message,
                        _("The credit of the sale order is not allowed."),
                        result['description'])

                    context['mail_thread_no_duplicate'] = True
                    project_issue_obj.create_issue(
                        cr, uid, 'sale.order', order.id, error_message,
                        issue_subject=_("Negative result of credit check"),
                        tags=['sale.order', 'credit check false'],
                        create=True, reopen=False, context=context)
                    del context['mail_thread_no_duplicate']

        except Exception as e:
            logger.error(format_exception(e))
            raise

        if error_message:
            logger.debug("Negative credit check on sale order #{0} {1} "
                         "with payment method {2}".format(
                order.id, order.name, order.payment_method_id))
            is_rejected = True
        else:
            is_rejected = False

        return is_rejected

    def check_if_check_inventory_for_quotation(
            self, cr, uid, ids, soa_info, context=None):
        """ Checks if we have enough items to start the filling of the order,
            but only if the stock.type associated to the delivery method
            of the sale.order asks for it, or if there is no stock.type
            associated to the delivery method.

            Also checks (always) that the differnt units of measure are all
            in the same group: sale.order.line's UOM, product's UOM and
            product's purchase's UOM. We do this to prevent future problems
            in the SOA, specially in the case of the dropship in which
            we have to generate a purchase from procurements which end up
            in a supplier invoice the lines of which has to be compared with
            those of the customer invoice.

            Also checks (always) that the products have set taxes for
            customer-taxes and supplier-taxes which are mirrored (same amount
            but with/without taxes).

            Also checks (only if the stock.route is of type 'direct' that the
            products can be sent using the delivery methods available);
            otherwise it raises.
        """
        if context is None:
            context = {}
        if type(ids) is not list:
            ids = [ids]

        conf_data = self.pool.get('configuration.data').get(cr, uid, [],
                                                            context=context)

        soa_info.next_state = 'saleorder_checkcredit'

        order = self.browse(cr, uid, ids[0], context=context)
        picking_policy = order.get_picking_policy()

        do_availability_check = False
        if picking_policy == 'direct':
            message = \
                _("Skipped the inventory check because the picking policy "
                  "is 'direct'.")
        elif picking_policy == 'one' or order.stock_type_id.availability_check:
            do_availability_check = True
            message = \
                _("Checks if there are items to start filling the order.")
        else:
            message = \
                _("Skipped the inventory check because of the stock type or "
                  "the picking type being 'one'.")

        soa_info.message = message
        if do_availability_check:
            order._check_inventory_for_quotation(soa_info)

        if conf_data.soa_check_uoms:
            order._check_consistent_uoms(soa_info)

        if conf_data.soa_check_taxes:
            order._check_taxes_on_product(soa_info)

        if order.stock_type_id and \
           order.stock_type_id.route == 'regular':
            order._check_available_delivery_methods(soa_info)

        # If the next step is to check the credit, but we know we
        # don't need to check the credit, then we move a step forward
        # in the automation.
        if soa_info.next_state == 'saleorder_checkcredit' and \
           not order.do_credit_check():
            soa_info.next_state = 'saleorder_draft'

        return True

    def _check_taxes_on_product(self, cr, uid, ids, soa_info, context=None):
        """ Checks that the products have set taxes for
            customer-taxes and supplier-taxes which are mirrored (same amount
            but with/without taxes).
        """
        if context is None:
            context = {}
        if type(ids) is not list:
            ids = [ids]

        tax_obj = self.pool.get('account.tax')
        order_line_obj = self.pool.get('sale.order.line')
        module_obj = self.pool.get('ir.module.module')

        order = self.browse(cr, uid, ids[0], context=context)

        # Do we have the module stage_discount installed?
        stage_discount_is_installed = bool(module_obj.search(cr, uid, [
            ('name', '=', 'stage_discount'),
            ('state', '=', 'installed'),
        ], count=1, limit=1, context=context))

        domain_search_lines = [
            ('order_id', '=', order.id),
            ('tax_id', '!=', False),
        ]
        if stage_discount_is_installed:
            domain_search_lines.append(('is_discount', '=', False))

        # Checks the taxes on the lines that have a tax.
        line_ids = order_line_obj.search(cr, uid, domain_search_lines,
                                         context=context)

        for line in order_line_obj.browse(cr, uid, line_ids, context=context):
            product = line.product_id

            customer_taxes_ids = \
                set([tax.id for tax in product.taxes_id])
            supplier_taxes_ids = \
                set([tax.id for tax in product.supplier_taxes_id])

            # Each tax on the line has to be listed as a customer tax on
            # the product, and has to have its mirror supplier tax.
            if line.tax_id[0].id not in customer_taxes_ids:
                soa_info.error = True
                soa_info.message = \
                    _("The tax indicated in the sale.order.line with ID={0} "
                      "is not set as customer tax on the product with "
                      "ID={1}").format(line.id, product.id)

            mirror_tax_ids = tax_obj.search(cr, uid, [
                ('type_tax_use', 'in', ('purchase', 'all')),
                ('price_include', '=', False),
                ('type', '=', line.tax_id[0].type),
                ('amount', '=', line.tax_id[0].amount),
                ('active', '=', True),
            ], context=context)
            if not mirror_tax_ids:
                soa_info.error = True
                soa_info.message = \
                    _("No tax of the same type to be applied on purchases or "
                      "all, with the tax NOT included on the price, was found "
                      "for sale.order.line with ID={0} and product with "
                      "ID={1}").format(line.id, product.id)
            elif len(set(mirror_tax_ids) & supplier_taxes_ids) == 0:
                soa_info.error = True
                soa_info.message = \
                    _("No equivalent tax to the customer invoice tax was "
                      "found on the product with ID={0} placed on the "
                      "sale.order.line with ID={1}").format(product.id,
                                                            line.id)

        return True

    def _check_available_delivery_methods(self, cr, uid, ids, soa_info,
                                          context=None):
        """ Check the delivery methods for all the lines of the
            sale order, and tries to set an alternative method for
            each line if the provided one is not valid. If this is not
            possible, then it alarms with an issue, sets a message in the
            chat of the sale.order, and stops the job of the SOA.

            The algorithm to check for a delivery method is as follows:
            for each line of the sale order:
                if the product has a list of valid delivery methods, then:
                    if the carrier of the sale.order is a valid method for the
                    product of the line, then it's ok, otherwise tries to find
                    an alternative method, by searching a new delivery method
                    which is in the intersection of delivery methods valid for
                    the product, and the alternative ones set on the carrier
                    of the sale.order. If no one is found, then logs & alarms.
                else if the product's category has a list of valid delivery
                methods, then:
                    repeates the process above, but instead of searching
                    on the product, searches on the category.
        """
        if context is None:
            context = {}
        if not isinstance(ids, list):
            ids = [ids]

        err_msg = _("There is no valid delivery method alternative for "
                    "this {obj_type} and the requested delivery method - "
                    "please review the list of alternatives, the list "
                    "of allowed delivery methods or change the "
                    "requested delivery method on the picking and "
                    "requeue the automation job")

        order = self.browse(cr, uid, ids[0], context=context)

        errors = []

        carrier_id = order.carrier_id.id

        for line in order.order_line:
            prod = line.product_id
            prod_template = prod.product_tmpl_id
            prod_categ = prod_template.categ_id

            if prod.yc_allowed_delivery_method_ids:
                # If the product has any delivery methods set, then
                # we try to use them with our product.
                delivery_method_is_allowed = \
                    prod_template.is_delivery_method_allowed(carrier_id)

                if not delivery_method_is_allowed:
                    # We try to use one of the alternative carriers, to
                    # try to send this item.
                    alt_carrier_id = \
                        prod_template.find_alternative_carrier(carrier_id)
                    if alt_carrier_id:
                        line.write({'alt_carrier_id': alt_carrier_id})
                    else:
                        error_msg = \
                            'Product {0} (ID={1}) on sale.order.line ' \
                            'with ID={2} belonging to sale.order ' \
                            'with ID={3}: {4}'.format(
                                prod, prod.id, line.id, order.id,
                                err_msg.format(obj_type='product'))
                        errors.append(error_msg)

                # else:
                #     pass  # The line is fine and can be sent as is.

            elif prod_categ.yc_allowed_delivery_method_ids:

                # If the product doesn't have any delivery methods set,
                # then we look for the ones defined on its category.
                delivery_method_is_allowed = \
                    prod_categ.is_delivery_method_allowed(carrier_id)

                if not delivery_method_is_allowed:
                    # We try to use one of the alternative carriers, to
                    # try to send this item.
                    alt_carrier_id = \
                        prod_categ.find_alternative_carrier(carrier_id)
                    if alt_carrier_id:
                        line.write({'alt_carrier_id': alt_carrier_id})
                    else:
                        error_msg = \
                            'Product {0} (ID={1}) on sale.order.line ' \
                            'with ID={2} belonging to sale.order ' \
                            'with ID={3}: {4}'.format(
                                prod, prod.id, line.id, order.id,
                                err_msg.format(obj_type='category'))
                        errors.append(error_msg)

                # else:
                #     pass  # The line is fine and can be sent as is.

            # else:
            #     pass  # The line is fine and can be sent as is.

        if errors:
            error_message = "\n".join(errors)

            # This will make the SOA to stop and make the job fail.
            soa_info.error = True
            soa_info.message = error_message

            # This will log an issue for the sale.order.
            self.pool.get('project.issue').create_issue(
                cr, uid, 'sale.order', order.id, error_message,
                tags=['sale', 'sale-exception'], context=context)

            # This will add a message in the chatter of the sale.order.
            self.message_post(cr, uid, order.id, body=error_message,
                              context=context)

        return True

    def _check_consistent_uoms(self, cr, uid, ids, soa_info, context=None):
        """ Checks that the differnt units of measure are all
            in the same group: sale.order.line's UOM, product's UOM and
            product's purchase's UOM.
        """
        if context is None:
            context = {}
        if type(ids) is not list:
            ids = [ids]

        order = self.browse(cr, uid, ids[0], context=context)

        for line in order.order_line:
            if hasattr(line, 'is_discount') and line.is_discount:
                continue

            product = line.product_id
            product_uom_category = product.uom_id.category_id.id

            if (line.product_uom.category_id.id != product_uom_category) or \
               (product.uom_po_id.category_id.id != product_uom_category):
                soa_info.error = True
                soa_info.message = '{0}\n{1}'.format(
                    soa_info.message,
                    _("Product with ID={0} on sale.order.line with ID={1} "
                      "had UOMs which were not in the same group.".format(
                        product.id, line.id)))

        return True

    def _check_inventory_for_quotation(
            self, cr, uid, ids, soa_info, context=None):
        """ Checks if we have enough items to start the filling of the order.
        :param cr: 
        :param uid: 
        :param ids: 
        :param context: 
        :return: 
        """
        if context is None:
            context = {}
        if type(ids) is not list:
            ids = [ids]

        product_uom_obj = self.pool.get('product.uom')
        conf_data_obj = self.pool.get('configuration.data')

        order = self.browse(cr, uid, ids[0], context=context)
        picking_policy = order.get_picking_policy()

        picking_policy_direct_delay = True
        picking_policy_one_delay = False

        # We first store how many products we have, because
        # a product may be used in more than one sale.order.line.
        # The quantity for each product is stored in the UOM for that product.
        # We only consider products of type 'product'.
        product_qty = {}
        for line in order.order_line:
            product = line.product_id
            if (product.type == 'product') and (product not in product_qty):
                product_qty[product] = 0
            if product.type == 'product':
                product_qty[product] += product_uom_obj._compute_qty_obj(
                    cr, uid, line.product_uom, line.product_uom_qty,
                    product.uom_id)

        # We check if we have enough quantities to fulfill this product,
        # otherwise we delay the sale.order.
        for product in product_qty:
            requested_qty = product_qty[product]

            # This is like the virtual_available, but without considering
            # the incoming quantities (because we can not trust that they
            # will arrive).
            actual_qty = product.qty_available + product.outgoing_qty

            # If picking_policy is 'one' we must have enough quantities for
            # all the products.
            if picking_policy == 'one' and actual_qty < requested_qty:
                picking_policy_one_delay = True
                break

            # If picking policy is 'direct', we only need at least one product
            # not to delay the quotation.
            elif picking_policy == 'direct':
                if actual_qty > 0:
                    picking_policy_direct_delay = False
                    break

        if (picking_policy == 'one' and picking_policy_one_delay) or \
           (picking_policy == 'direct' and picking_policy_direct_delay):
            config_data = conf_data_obj.get(cr, uid, [], context=context)

            soa_info.delay = True
            soa_info.next_state_time = get_next_day_datetime(
                cr, uid, 0, 0, config_data.support_timezone,
                config_data.get_open_days_support())

        return True

    def _process_workflow_saleorder_draft_to_sent(
            self, cr, uid, ids, soa_info, context=None):
        """ Changes the sale order from state 'draft' to 'sent'
        """
        if context is None:
            context = {}
        if type(ids) is not list:
            ids = [ids]

        sale_order_line_obj = self.pool.get('sale.order.line')

        order = self.browse(cr, uid, ids[0], context=context)

        soa_info.next_state = 'saleorder_sent'
        soa_info.message = \
            _("Changes a sale order from state 'draft' to 'sent'.")

        # We are going to test the exceptions defined in the module
        # sale_exceptions
        if not order.test_exceptions() and not order.ignore_exceptions:
            raise Exception('\n'.join([sale_exception.name
                                       for sale_exception in
                                       order.exceptions_ids]))

        # First checks if, according to the clocking or the stock.type, we
        # we have to wait for a sale.order to age.
        next_state_time = False
        if not order.stock_type_id or order.stock_type_id.consider_aging:
            # If the sale.order doesn't have a stock.type set, or it has
            # one but requires to consider the aging, we see if, according
            # to the clocking of the sale.order, we have to wait for it to age.
            next_state_time = self.__clocking_process_saleorder_draft_to_sent(
                cr, uid, ids, context)

        if next_state_time:
            soa_info.message = JOB_DELAYED_MESSAGE
            soa_info.delay = True
            soa_info.next_state_time = next_state_time

        else:
            signal = 'quotation_sent'
            err_msg = 'Unknown error'

            # Checks if the sale order must be rejected.
            if order.main_exception_id:
                signal = None
                err_msg = order.main_exception_id.name
                raise Warning(err_msg)

            success = self._process_workflow_saleorder_draft_to_sent_before(
                cr, uid, ids, signal, context)

            if success:

                # If the sale.order is going to be a dropshipping, then
                # all its sale.order lines must have its procurement method
                # set to be 'on order' and the delivery lead time to zero.
                if order.is_dropship():
                    order_line_ids = [line.id for line in order.order_line]
                    order_line_values = {
                        'type': 'make_to_order',
                        'delay': 0,
                    }
                    sale_order_line_obj.write(
                        cr, uid, order_line_ids, order_line_values,
                        context=context)

                    # For the dropships, care must be taken to ensure that
                    # the parents for the suppliers have a fiscal position
                    # set which allows a mapping between the taxes of the
                    # sale.order. It'll raise if the check fails.
                    try:
                        cr.execute("SAVEPOINT check_fiscal_position_mapping")
                        order.check_fiscal_position_mapping()
                    except Exception as e:
                        soa_info.error = str(e)
                        err_msg = str(e)
                        success = False

                        cr.execute("ROLLBACK TO SAVEPOINT "
                                   "check_fiscal_position_mapping")
                    else:
                        cr.execute("RELEASE SAVEPOINT "
                                   "check_fiscal_position_mapping")

                    # For each sale.order.line it fills its fields
                    # product_uop and product_uop_qty with the unit of
                    # purchase order, and its converted quantity, for
                    # that product & line, to ease a possible future comparison
                    # between the lines of a purchase and a sale order if
                    # dropship.
                    sale_order_line_obj.compute_purchase_uom(
                        cr, uid, [l.id for l in order.order_line],
                        context=context)

                if success:
                    wf_service = netsvc.LocalService('workflow')
                    wf_service.trg_validate(
                        uid, 'sale.order', order.id, signal, cr)

                    order.write({'order_policy': 'manual'})

            if success:
                success = self._process_workflow_saleorder_draft_to_sent_after(
                    cr, uid, ids, signal, context)

            if not success:
                raise Warning(err_msg)

        return True

    def _process_workflow_saleorder_draft_to_sent_before(self, cr, uid, ids,
                                                         signal, context=None):
        """ CAN BE overridden by subclasses to add code to be executed BEFORE
            the sale order (quotation) passes from state 'draft' to 'sent'.
                The parameter 'signal' indicates the signal to send to the
            workflow, of None if the sale.order must be stopped.
                Returns whether it had success or not.
        """
        if context is None:
            context = {}
        if type(ids) is not list:
            ids = [ids]

        # If any of the lines of the sale order is sent without the
        # description set, it takes it from the name of the product,
        # and adds it.
        for sale_order in self.browse(cr, uid, ids, context=context):
            for order_line in sale_order.order_line:
                if not order_line.name:
                    order_line.write({
                        'name': '[{0}] {1}'.format(
                            order_line.product_id.default_code,
                            order_line.product_id.name)})

        return True

    def _process_workflow_saleorder_draft_to_sent_after(self, cr, uid, ids,
                                                        signal, context=None):
        """ CAN BE overridden by subclasses to add code to be executed AFTER
            the sale order (quotation) passes from state 'draft' to 'sent'.
                The parameter 'signal' indicates the signal to send to the
            workflow, of None if the sale.order must be stopped.
                Returns whether it had success or not.
        """
        return True

    def _process_workflow_saleorder_sent_to_router(
            self, cr, uid, ids, soa_info, context=None):
        """ Changes a sale order from state 'sent' to 'router'.
            From 'router' it is sent automatically to the states 
            'wait_invoice' and 'wait_ship'
        """
        if context is None:
            context = {}
        if type(ids) is not list:
            ids = [ids]

        order = self.browse(cr, uid, ids[0], context=context)

        conf_data = self.pool.get('configuration.data').get(
            cr, uid, [], context=context)

        soa_info.message = \
            _("Changes a sale order from state 'sent' to 'router'.")

        # Keeps a copy of the invoice policy to be used at the moment of
        # creating the invoice.
        self.write(
            cr, uid, order.id, {'invoice_policy': conf_data.invoice_policy},
            context=context)

        # At this point, just a picking has been created for the sale.order.
        # In next steps of the SOA we'll end up splitting the pickings
        # into several ones, if needed.
        wf_service = netsvc.LocalService('workflow')
        wf_service.trg_validate(
            uid, 'sale.order', order.id, 'order_confirm', cr)

        # The procurements for products which are services won't be confirmed
        # automatically until the MRP scheduler runs, but we may not want to
        # wait so much, so at this step (which is when the procurements have
        # been created in state draft) we run completely the procurements
        # associated to the sale.order that are for service products.
        order.run_service_procurements()

        # The next step in the SOA depends on the stock type
        # and the picking policy.
        if order.is_dropship():
            soa_info.next_state = 'deliveryorder_assignation_dropship'
        else:
            picking_policy = order.get_picking_policy()
            if picking_policy == 'one':
                soa_info.next_state = 'deliveryorder_assignation_one'
            else:  # if picking_policy == 'direct':
                soa_info.next_state = 'deliveryorder_assignation_direct'

        return True

    def get_picking_policy(self, cr, uid, ids, context=None):
        """ Gets the picking policy for a sale.order, which depends on
            the values set on the configuration and on the stock.type
            associated to the delivery.carrier of the sale.order. 
            
            The algorithm is as follows:
            1. It first checks on the stock.type of the carrier, and returns
               the picking policy set there, unless it's set to resort to
               the value set on the configuration, and in that case we move
               to step 2.
            2. It checks on the picking policy set on the configuration, and
               returns the value set there, unless it's set to resort to the
               value set by the web-shop, which is the value set on the 
               sale order, and in that case we move to step 3.
            3. It returns the picking policy set on the sale.order, which
               must be set because it's a mandatory field.
        """
        if context is None:
            context = {}
        if type(ids) is not list:
            ids = [ids]

        order = self.browse(cr, uid, ids[0], context=context)

        picking_policy = order.stock_type_id.forced_picking_policy
        if (not picking_policy) or (picking_policy == 'keep'):
            picking_policy = self.pool.get('configuration.data').\
                get(cr, uid, [], context=context).default_picking_policy
            if picking_policy == 'keep':
                picking_policy = order.picking_policy

        return picking_policy

    def check_fiscal_position_mapping(self, cr, uid, ids, context=None):
        """ As a safe vest, we make sure the partner on the sale order
            has a fiscal position set which allows a mapping between the
            existing taxes in all the lines, so that we can map the taxes
            from the sale order into taxes for the purchase which can be used
            later in the taxes for the supplier invoices.

            If we don't stop the SOA here, there will be a missmatch between
            he purchase and the invoice it comes from.
        """
        if context is None:
            context = {}

        error_messages = []
        for order in self.browse(cr, uid, ids, context=context):
            fiscal_position = order.partner_shipping_id.get_fiscal_position()

            if not fiscal_position:
                error_messages.append(
                    _("Partner with ID={0} of order with ID={1} "
                      "does not have a fiscal position.").
                        format(order.partner_id.id, order.id))
            else:
                taxes_mapped = \
                    set([mapping.tax_src_id.id
                         for mapping in fiscal_position.tax_ids])

                for order_line in order.order_line:
                    for tax in order_line.tax_id:
                        if tax.id not in taxes_mapped:
                            error_messages.append(
                                _("Tax with ID={0} on sale.order.line with "
                                  "ID={1} belonging to purchase with ID={2} "
                                  "is not mapped by fiscal position "
                                  "with ID={3}").format(tax.id, order_line.id,
                                                        order.id,
                                                        fiscal_position.id))
        if error_messages:
            raise orm.except_orm(
                _('Errors regarding the fiscal position.'),
                _('The following errors were found regarding the '
                  'fiscal positions: {0}').format('\n'.join(error_messages)))

        return True

    def do_assignation_one(self, cr, uid, ids, soa_info, context=None):
        """ If we just want to send an order directly, we attempt to
            send it. If there are no enough goods to fulfill the order,
            the job will fail.
        """
        if context is None:
            context = {}
        if type(ids) is not list:
            ids = [ids]

        conf_data = self.pool.get('configuration.data').get(
            cr, uid, [], context=context)

        soa_info.message = _("Does the assignation 'one'.")
        soa_info.next_state = 'do_multi_parcel_deliveries'

        move_obj = self.pool.get('stock.move')
        picking_obj = self.pool.get('stock.picking')

        # Does the split of pickings if it has to.
        self._split_pickings(cr, uid, ids, context=context)

        # Because of the possible new pickings created, we re-browse the order.
        order = self.browse(cr, uid, ids[0], context=context)
        for delivery in order.picking_ids:
            instructions = delivery.compute_instructions_for_assignation()

            if backorder_has_to_be_created(instructions):
                # If we need to create a back-order then we have to
                # raise and make the job fail, because the
                # assignation-one requires to send the picking
                # as a whole.
                products_missing = set()
                for instr in instructions:
                    if instr.move_option == 'wait':
                        move = move_obj.browse(
                            cr, uid, instr.stock_move_id, context)
                        products_missing.add(
                            "{0} (ID={1})".format(move.product_id.name,
                                                  move.product_id.id))

                exception_title = \
                    _("The picking can not be created because "
                      "some products are missing")
                exception_msg = \
                    _("The following products are missing quantities: "
                      "{0}").format('\n'.join(list(products_missing)))
                raise orm.except_orm(exception_title, exception_msg)

            else:
                delivery.apply_instructions(instructions)
                if delivery.state == 'draft':
                    picking_obj.draft_force_assign(
                        cr, uid, [delivery.id], context)
                delivery.action_confirm()
                if delivery.state == 'confirmed':
                    picking_obj.action_assign(cr, uid, [delivery.id], context)

        # Checks if we can shortcut the state do_multi_parcel_deliveries
        # and go to the next one, in the case that is the next expected state.
        if soa_info.next_state == 'do_multi_parcel_deliveries' and \
                not conf_data.packaging_enabled:
            soa_info.next_state = 'print_deliveryorder_in_local'

        return True

    def _split_pickings(self, cr, uid, ids, context=None):
        """ TODO.
        """
        if context is None:
            context = {}
        if not isinstance(ids, list):
            ids = [ids]

        move_obj = self.pool.get('stock.move')
        order_line_obj = self.pool.get('sale.order.line')
        picking_obj = self.pool.get('stock.picking')
        sequence_obj = self.pool.get('ir.sequence')

        for order in self.browse(cr, uid, ids, context=context):
            # For the picking split: if all the moves can be sent
            # on the same picking which is already created (which can only
            # happen if the carrier of the sale.order this picking came
            # from is compatible with the products of all the moves --- which
            # in turn is something we checked and collected on the first step
            # of the SOA) then we do nothing; BUT if a picking split has to
            # be done, then we create the pickings here first.
            alt_carrier_needed = bool(order_line_obj.search(cr, uid, [
                ('order_id', '=', order.id),
                ('alt_carrier_id', '!=', False),
            ], limit=1, count=True, context=context))
            if alt_carrier_needed:
                # We may be lucky and all the other goods just need a different
                # carrier, and in that case it would be as easy as changing the
                # carrier of the picking for the new one. But this is only
                # possible if all the lines go to the same carrier:
                alt_carrier_first_line_id = order.order_line[0].alt_carrier_id.id
                num_lines_having_first_carrier = order_line_obj.search(
                    cr, uid, [
                        ('order_id', '=', order.id),
                        ('alt_carrier_id', '=', alt_carrier_first_line_id),
                    ], count=True, context=context)
                if num_lines_having_first_carrier == len(order.order_line):
                    # We were lucky and all the lines go to the same
                    # alternative carrier, thus we just change the carrier
                    # of the pickings of the order.
                    picking_ids = [picking.id for picking in order.picking_ids]
                    picking_obj.write(cr, uid, picking_ids, {
                        'carrier_id': order.order_line[0].alt_carrier_id.id
                    }, context=context)
                else:
                    # We need to split the picking into several pickings.

                    # We first determine how many pickings we WILL have:
                    # normally as many pickings as different alternative
                    # carriers we have *plus one* (for the carrier of the
                    # sale order), but if all the lines have an alternative
                    # carrier  set, then we have to re-use the original picking
                    # and just change its delivery carrier, thus we WILL have
                    # as many pickings as different alternative carriers (and
                    # that's it --- so: *plus zero*).
                    all_lines_require_alt_carrier = True
                    carriers = {}
                    for line in order.order_line:
                        alt_carrier = line.alt_carrier_id
                        if alt_carrier:
                            carriers.setdefault(alt_carrier, []).append(
                                line.id)
                        else:
                            all_lines_require_alt_carrier = False

                    # At this point of the automation, it is guaranteed that
                    # we have just one picking per sale.order.
                    picking = order.picking_ids[0]
                    num_carrier = 1
                    for carrier, line_ids in carriers.iteritems():

                        if all_lines_require_alt_carrier and \
                                        num_carrier == len(carriers):
                            # If it's the last carrier and all the lines need
                            # to go with a carrier different than that of the
                            # sale order, then we simply change it for this
                            # latter case, this way avoiding to create an
                            # extra picking to simply remove the one that would
                            # result in an empty one (without moves).
                            picking.write({'carrier_id': carrier.id})

                            # Nothing to do with the lines here, since the
                            # ones that remain on the picking are the ones that
                            # go with the reamining carrier. We can assure this
                            # because we have left this one for the last.

                        else:
                            new_picking_name = sequence_obj.get(
                                cr, uid, 'stock.picking.{0}'.format(
                                    picking.type))
                            new_picking_id = picking_obj.copy(
                                cr, uid, picking.id, {
                                    'name': new_picking_name,
                                    'move_lines': False,
                                    'state': 'draft',
                                    'carrier_id': carrier.id,
                                }, context=context)

                            move_ids = move_obj.search(cr, uid, [
                                ('sale_line_id', 'in', line_ids),
                            ], context=context)
                            move_obj.write(cr, uid, move_ids, {
                                'picking_id': new_picking_id,
                            }, context=context)

                            new_picking = picking_obj.browse(
                                cr, uid, new_picking_id, context=context)
                            if new_picking.state == 'draft':
                                picking_obj.draft_force_assign(
                                    cr, uid, [new_picking.id], context)
                            new_picking.action_confirm()

                        num_carrier += 1

        return True

    def do_assignation_direct(
            self, cr, uid, ids, backorder_id, soa_info, context=None):
        """ Does the 'direct' assignation, in which a sale.order doens't have
            to be completely fullfilled, i.e. backorders can be created if
            it is not 100% sent in a picking.
        """
        if context is None:
            context = {}
        if type(ids) is not list:
            ids = [ids]

        picking_obj = self.pool.get('stock.picking')

        conf_data = self.pool.get('configuration.data').get(
            cr, uid, [], context=context)

        soa_info.message = _("Does the assignation 'direct'.")

        order = self.browse(cr, uid, ids[0], context=context)

        # If, for some reason, we end up with a sale order which has all its
        # pickings in state delivered (i.e. done), then we end up the sale
        # order automation for this sale order, because everything
        # has already been done.
        num_pickings_in_done_or_cancel = picking_obj.search(cr, uid, [
            ('sale_id', '=', order.id),
            ('state', 'in', ('done', 'cancel')),
        ], count=True, context=context)
        if num_pickings_in_done_or_cancel == len(order.picking_ids):
            soa_info.message = _(
                "All deliveries done for sale order with ID={0}, "
                "terminating the sale order automation.").format(order.id)
            soa_info.next_state = False

        else:
            # Does the split of pickings if it has to.
            self._split_pickings(cr, uid, ids, context=context)

            # We re-browse the order just in case the splitting of the pickings
            # had created new pickings.
            order = self.browse(cr, uid, ids[0], context=context)

            if backorder_id:
                picking_ids = [backorder_id]

                # It can happen that the back-order has been cancelled
                # and in this case we abort the job.
                delivery = picking_obj.browse(cr, uid, backorder_id, context)
                if delivery.state == 'cancel':
                    soa_info.next_state = False
                    # The list of pickings to consider is cleared out.
                    picking_ids = []

            else:
                # We only enter here the first time, otherwise it would fail
                # (because only the first time it happens that all the
                # pickings of a sale.order need to be processed). The
                # alternative is doing a search.
                picking_ids = [picking.id for picking in order.picking_ids]

            for delivery in picking_obj.browse(cr, uid, picking_ids, context):
                instructions = delivery.compute_instructions_for_assignation()

                if delivery.state == 'assigned':
                    # If the picking is in state assigned, that means that we
                    # can send it, thus we move to the next state.
                    soa_info.next_state = 'do_multi_parcel_deliveries'

                elif not goods_are_available(instructions):
                    # If there are no goods available it means that all the
                    # stock moves would go to the backorder, thus it means
                    # that we have to requeue the current picking with the
                    # hope that in the future we'll be able to satisfy at
                    # least a part of the picking.
                    hour_backorder, minutes_backorder = \
                        get_hours_minutes_from_float(
                            conf_data.execute_only_after_time_for_backorders)
                    soa_info.next_state = 'deliveryorder_assignation_direct'
                    soa_info.next_state_time = get_next_day_datetime(
                        cr, uid, hour_backorder, minutes_backorder,
                        conf_data.support_timezone,
                        conf_data.get_open_days_support())

                elif backorder_has_to_be_created(instructions):
                    new_picking, original_picking = delivery.create_backorder(
                        instructions)

                    # If a new picking was created that means that we have a
                    # back-order, which in v7 is the original picking,
                    # and is the picking with the goods that are
                    # not yet available.
                    picking_obj.draft_force_assign(cr, uid, [new_picking.id])
                    new_picking.action_confirm()
                    picking_obj.action_assign(cr, uid, [new_picking.id],
                                              context)

                    # If the method has not epayment, it saves the products
                    # that are pending in back-orders at the moment of
                    # creating the picking which can be sent.
                    new_picking.store_backorder_products()

                    # For the original picking (the back-order one) it
                    # creates a new job to be executed the next natural day,
                    # with the hope that we will have the goods available
                    # in that case.
                    session = ConnectorSession(cr, uid)

                    hour_backorder, minutes_backorder = \
                        get_hours_minutes_from_float(
                            conf_data.execute_only_after_time_for_backorders)
                    next_state_time = get_next_day_datetime(
                        cr, uid, hour_backorder, minutes_backorder,
                        conf_data.support_timezone,
                        conf_data.get_open_days_support())

                    automate_sale_order_process.delay(
                        session, 'sale.order', order.id,
                        'deliveryorder_assignation_direct',
                        next_state_time=next_state_time,
                        backorder_id=original_picking.id,
                        eta=next_state_time, priority=order.get_soa_priority())

                    # We move to the next state in the automation.
                    soa_info.next_state = 'do_multi_parcel_deliveries'

                else:
                    # We could assign all the goods to the original
                    # picking, therefore we move forward in
                    # the automation.
                    delivery.apply_instructions(instructions)
                    if delivery.state == 'draft':
                        picking_obj.draft_force_assign(
                            cr, uid, [delivery.id], context)
                    delivery.action_confirm()
                    if delivery.state == 'confirmed':
                        picking_obj.action_assign(cr, uid, [delivery.id],
                                                  context)
                        soa_info.next_state = 'do_multi_parcel_deliveries'

        # Checks if we can shortcut the state do_multi_parcel_deliveries
        # and go to the next one, in the case that is the next expected state.
        if soa_info.next_state == 'do_multi_parcel_deliveries' and \
                not conf_data.packaging_enabled:
            soa_info.next_state = 'print_deliveryorder_in_local'

        return True

    def do_assignation_dropship(self, cr, uid, ids, soa_info, context=None):
        """ Does the assignation for the deliveries if we have a dropshipping.
        """
        if context is None:
            context = {}
        if type(ids) is not list:
            ids = [ids]

        wf_service = netsvc.LocalService("workflow")
        purchase_obj = self.pool.get('purchase.order')
        proc_obj = self.pool.get('procurement.order')

        conf_data = self.pool.get('configuration.data').get(
            cr, uid, [], context=context)

        order = self.browse(cr, uid, ids[0], context=context)

        # The purchase orders created have to be merged & validated
        # so that they can generate a picking.
        # We merge only those purchases coming from the order (that we know
        # for sure because of the new field added)
        proc_ids = proc_obj.search(
            cr, uid, [('sale_id', '=', order.id)], context=context)
        purchase_ids = [proc.purchase_id.id
                        for proc
                        in proc_obj.browse(cr, uid, proc_ids, context=context)]

        if not all(purchase_ids):
            # If no purchase were found we'll end up having an error.
            # The cause is usually an error on the procurement, so we inform
            # about it and return.
            proc_errors = []
            for proc in proc_obj.browse(cr, uid, proc_ids, context=context):
                if proc.message:
                    proc_errors.append(
                        "Proc ID={0}. Error {1} on product {2} "
                        "(ID={3})".format(proc.id, proc.message,
                                          proc.product_id.name,
                                          proc.product_id.id))
            error_msg = "Procurements with IDs = {0} did not create all the " \
                        "purchases needed. Errors found: " \
                        "{1}".format(','.join(map(str, proc_ids)),
                                     '\n'.join(proc_errors))
            soa_info.error = True
            soa_info.message = error_msg
            soa_info.next_state = 'deliveryorder_assignation_dropship'
            return False

        purchase_merge_obj = self.pool.get('purchase.order.group')
        purchase_merge_id = purchase_merge_obj.create(
            cr, uid, {}, context=context)
        context['active_ids'] = purchase_ids
        ret = purchase_merge_obj.merge_orders(
            cr, uid, purchase_merge_id, context=context)
        del context['active_ids']

        # ret['domain'] has a domain of the type ('id', 'in', [x,y,z]),
        # being x,y,z the IDs of the new purchase created. Thus we have to
        # get them the following ugly way.
        new_purchase_ids = safe_eval(ret['domain'])[0][-1]

        # Also, if no purchases were merged, then no new purchase was created,
        # so we have to add the already existing purchases to the list.
        # All this taking into account that purchases  that were merged are
        # cancelled, so we have to filter them.
        non_merged_purchases_ids = purchase_obj.search(
            cr, uid, [('id', 'in', purchase_ids), ('state', '!=', 'cancel')])
        new_purchase_ids.extend(non_merged_purchases_ids)

        # Links the purchase orders to the sale order which originated them
        # indirectly because of its procurement orders.
        order.write({'purchase_dropship_ids': [(6, False, new_purchase_ids)]})

        # Changes the partner of the purchase to be the shipping address
        # of the sale order it comes from.

        # Also makes the invoicing policy to depend on the purchase and not
        # on the picking.in for the case of C+C, and to depend on the picking
        # for the case of C+R (because we don't want an invoice in that case)
        # and for the case of Regular (since it's the default behaviour anyway
        # and this way the user can select not to generate an invoice).
        if order.stock_type_id.route == 'c+c':
            invoice_method = 'order'
        else:  # if order.stock_type_id.route in ('regular', 'c+r'):
            invoice_method = 'picking'
        purchase_obj.write(cr, uid, new_purchase_ids,
                           {'partner_id': order.partner_shipping_id.id,
                            'invoice_method': invoice_method,
                            }, context=context)

        # Validates the purchase orders to create the picking in.
        for new_purchase_id in new_purchase_ids:
            wf_service.trg_validate(
                uid, 'purchase.order', new_purchase_id, 'purchase_confirm', cr)

        # Checks if we can shortcut the state do_multi_parcel_deliveries
        # and go directly to the next one.
        if conf_data.packaging_enabled:
            soa_info.next_state = 'do_multi_parcel_deliveries'
        else:
            soa_info.next_state = 'print_deliveryorder_in_local'

        return True

    def create_supplier_invoice_from_customer_invoice(
            self, cr, uid, ids, context=None):
        """ Creates an invoice which is equal to the (only, in this case)
            invoice associated to the sale.order, for the Click & Collect
            scenario.
        """
        if context is None:
            context = {}
        if type(ids) is not list:
            ids = [ids]

        wf_service = netsvc.LocalService('workflow')
        inv_obj = self.pool.get('account.invoice')

        invoice_ids = inv_obj.search(
            cr, uid, [('sale_ids', 'in', ids)], context=context)
        for inv in inv_obj.browse(cr, uid, invoice_ids, context=context):
            supplier_inv_id = inv.copy_to_supplier_invoice()

            # We validate the invoice so that it's opened.
            wf_service.trg_validate(
                uid, 'account.invoice', supplier_inv_id, 'invoice_open', cr)

        return True

    def invoice_open_routing(
            self, cr, uid, ids, backorder_id, soa_info, context=None):
        """ Opens an invoice and, if it is C+C, then it  creates also the
            supplier invoice.
        """
        if context is None:
            context = {}
        if type(ids) is not list:
            ids = [ids]

        order = self.browse(cr, uid, ids[0], context=context)

        if order.stock_type_id.route == 'c+r':
            # C+R doesn't have an invoice, so we do nothing and finish
            # here the automation.
            soa_info.next_state = False
            soa_info.message = _("Click & Reserve does not have an invoice so "
                                 "everything is done and the SOA finishes.")
            self.write(cr, uid, order.id, {'automation_finished': True,
                                           }, context=context)

        else:
            order.saleorder_invoice_open(backorder_id, soa_info)
            soa_info.next_state = 'print_invoice_in_local'
            soa_info.message = \
                _("Creates an invoice for the sale order and validates it.")

            if order.stock_type_id.route == 'c+c':
                # C+C has also an incoming invoice, with the same
                # data than the customer invoice.
                order.create_supplier_invoice_from_customer_invoice()
                soa_info.message = "{0}{1}{2}".\
                    format(soa_info.message, os.linesep,
                           _("Creates a supplier invoice."))

        return True

    def saleorder_invoice_open(
            self, cr, uid, ids, backorder_id, soa_info, context=None):
        """ Creates an invoice associated to the sale.order,
            and validates it so that it's on state 'open'.
        """
        if context is None:
            context = {}
        if type(ids) is not list:
            ids = [ids]

        stock_picking_obj = self.pool.get('stock.picking')
        account_invoice_obj = self.pool.get('account.invoice')
        wf_service = netsvc.LocalService('workflow')

        # Stores the invoices associated to the sale order.
        invoice_ids = []

        order = self.browse(cr, uid, ids[0], context=context)

        if not order.invoice_policy or \
           order.invoice_policy == 'order' or \
           order.payment_method_id.epayment:

            if backorder_id:
                # If this is a back-order, we do nothing
                # (since the invoice is completely filled in).
                pass

            else:
                # We invoice the full sale.order,
                # and open the invoice in state draft.
                wf_service.trg_validate(
                    uid, 'sale.order', order.id, 'manual_invoice', cr)

                # Gets all the invoices corresponding to this sale.order.
                invoice_ids = account_invoice_obj.search(
                    cr, uid, [('sale_ids', 'in', order.id)], context=context)
                if not invoice_ids:
                    raise Warning(
                        "No invoices found for sale.order with ID={0}".
                        format(order.id))

                # Prepares the taxes, the rounding, and opens the invoice.
                account_invoice_obj.prepare_and_open_invoice(
                    cr, uid, invoice_ids, context=context)

        elif order.invoice_policy == 'delivery' \
                and not order.payment_method_id.epayment:
            # In this case, the invoice has been created with all the items.
            # However, what we want is that the invoice for the first picking
            # contains only the items on that picking, and all the services
            # and discounts that are on the sale.order. Later on, on the next
            # pickings, only the elements of that picking (which is _not_ the
            # first one) are contained on that invoice.

            if not backorder_id:
                # It's the first picking...

                # Finds the pickings which are not a back-order.
                picking_ids = []
                for picking in order.picking_ids:
                    if not picking.backorder_id:
                        # Since it's the first picking, just one of the
                        # two won't have a back-order.
                        picking_ids.append(picking.id)
                if len(picking_ids) < 1:
                    raise Warning(
                        _("There should be at least one picking linked to a "
                          "sale order with ID={0} which does not have a "
                          "back-order, but there are {1}: {2}").format(
                            order.id, len(picking_ids), ','.join(picking_ids)))

                add_discount_lines_from_order, skip_service_lines = True, False

            else:
                # If its's NOT the first picking...

                # We take the pickings which are still to be
                # invoiced.
                picking_ids = stock_picking_obj.search(
                    cr, uid, [('sale_id', '=', order.id),
                              ('invoice_state', '!=', 'invoiced'),
                              ('state', '=', 'assigned'),
                              ], context=context)

                add_discount_lines_from_order, skip_service_lines = False, True

            logger.debug(_("Invoicing the pickings with IDs={0}").
                         format(','.join(map(str, picking_ids))))

            # Call to the workflow, so that the sale.order enters into
            # its sub-workflow (but only if we are not there yet).
            reuse_existing_draft_invoice = False
            if order.order_policy == 'manual' and order.state != 'progress':
                # If we call the signal manual_invoice, it'll create a draft
                # invoice, that we don't need (because we create ours)...
                # and if we don't call it, the state in the workflow is
                # disconnected from the state of the sale.order, thus e.g.
                # if the order is paid and delivered, it won't traverse to
                # the state 'done'. So we need to create the 'draft' invoice,
                # and then delete it, but doing so makes the workflow of the
                # sale.order don't have the state 'invoice', which means that
                # it will never move to 'done' once its invoices are paid (and
                # also its pickings are delivered). So, what do we do? Calling
                # the signal is the only way to make sure the workflow is in
                # its correct state, and in this one specially since it enters
                # into the sub-workflow to create the invoice; the other
                # option is to do the SQL which does this for us... which is
                # ugly. So we have to call the signal... and deal with the
                # 'draft' invoice created by reusing it.

                wf_service.trg_validate(
                    uid, 'sale.order', order.id, 'manual_invoice', cr)
                reuse_existing_draft_invoice = True

            # We create an invoice which contains all the lines from the
            # picking.
            for picking in stock_picking_obj.browse(cr, uid, picking_ids,
                                                    context=context):
                context.update({
                    'do_not_generate_shipping_invoice_line': True,
                    'reuse_draft_invoice': reuse_existing_draft_invoice,
                })
                invoice_id = account_invoice_obj.create_invoice_from_picking(
                    cr, uid, [], picking, add_discount_lines_from_order,
                    skip_service_lines, context=context)
                del context['do_not_generate_shipping_invoice_line']
                del context['reuse_draft_invoice']

                # Prepares the taxes, the rounding, and opens the invoice.
                if invoice_id:
                    account_invoice_obj.prepare_and_open_invoice(
                        cr, uid, invoice_id, context=context)
                    invoice_ids.append(invoice_id)

        # If the method has not epayment, it saves the products that were
        # pending in back-orders at the moment of creating the invoice.
        # if not sale_order.payment_method_id.epayment:
        # (update: should be done on all payment methods)
        account_invoice_obj.store_backorder_products(
            cr, uid, invoice_ids, context=context)

        return True

    def _print_invoice_in_local(self, cr, uid, ids, soa_info, context=None):
        """ Prints the invoice associated to a given sale order,
            which must be in state 'open', and links it as an attachment
            to the invoice.
        """
        if context is None:
            context = {}
        if type(ids) is not list:
            ids = [ids]

        order = self.browse(cr, uid, ids[0], context=context)

        result_ok = order.print_and_attach_invoice_report()

        if result_ok:
            # For each invoice printed, we mark it as being ready to be sent
            # by email to the partner but only if its BVR was not printed
            # (i.e. only if it was printed with XXXs --- see t7051).
            for invoice in order.invoice_ids:
                if invoice.is_printed() and not invoice.show_bvr():
                    invoice.write({'send_invoice_to_partner': 'to_send'})

        soa_info.error = not result_ok
        return True

    def _print_invoice_in_remote(self, cr, uid, ids, backorder_id, soa_info, context=None):
        """ Makes the remote printing of the invoices.
        """
        if context is None:
            context = {}
        if type(ids) is not list:
            ids = [ids]

        for sale_order in self.browse(cr, uid, ids, context=context):
            for invoice in sale_order.invoice_ids:
                if invoice.check_send_invoice_to_docout():
                    invoice.mark_invoice_to_be_sent_to_docout()

        if not backorder_id:
            # Back-orders finish their automation also, but the flag set on
            # their associated sale.order to indicate that their automation
            # has finished will be set by the job which is not associated
            # to the back-order.
            self.write(cr, uid, ids, {'automation_finished': True},
                       context=context)

        # We end the automation at this step.
        #
        # Special case: Back-orders end their automation at this
        # step also. We have delayed its stop at this step (previously
        # it was in the previous 'print_invoice_in_local') since
        # we may need to mark the new invoice to be sent to the
        # doc-out (if needed).
        soa_info.next_state = False

        return True

    def _do_multi_parcel_deliveries(
            self, cr, uid, ids, soa_info, context=None):
        """ Makes the multi-parcel delivery. For every picking, it determines
            the number of packages needed to pack its content.
            Two possibilities:
            1) The carrier set on the sale.order is marked as being used for
               bulk-freight: in this case, the picking will be sent as
               bulk freight without taking into account any other
               consideration.
            2) The carrier set on the sale.order is not marked as being used
               for bulk-freight: in this case, depending on the quantity of
               packages needed for each picking, sends it as a bulk-freight
               or as packages.
        """
        if context is None:
            context = {}
        if type(ids) is not list:
            ids = [ids]

        order = self.browse(cr, uid, ids[0], context=context)

        soa_info.message = _("Do the multi-parcel deliveries.")

        picking_out_obj = self.pool.get('stock.picking.out')

        conf = self.pool.get('configuration.data').\
            get(cr, uid, [], context=context)

        stock_picking_out_domain = [('sale_id', 'in', ids),
                                    ('state', '=', 'assigned'),
                                    ]
        picking_out_ids = picking_out_obj.search(
            cr, uid, stock_picking_out_domain, context=context)

        # Case 1: If the carrier has been marked as being used for
        # bulk-freight, then we use it as bulk-freight directly, without
        # making a distinction depending on the number of packages to be
        # sent and related-configuration.
        if order.carrier_id.pc_freight_shipping:
            picking_out_obj.write(
                cr, uid, picking_out_ids, {'uses_bulkfreight': True},
                context=context)

        # Case 2: Otherwise, we have to consider each picking individually
        # and count the packages needed for each one, and depending on that
        # send that picking as bulk-freight or not.
        else:
            for stock_picking in picking_out_obj.browse(cr, uid,
                                                        picking_out_ids,
                                                        context=context):
                num_packages_needed = stock_picking.compute_num_packages()

                if num_packages_needed > conf.packaging_parcel_limit:
                    # We'll send it through bulk freight,
                    # so we change the delivery carrier of the picking to use
                    # the one for bulk freight.

                    # First we search for an explicit mapping, and if none is
                    # found then we use the mapping to be used by default,
                    # if any; if no mapping nor a default carrier is defined,
                    # we raise.
                    carrier_for_bulk_freight = \
                        order.carrier_id.get_carrier_for_bulk_freight()
                    if not carrier_for_bulk_freight:
                        carrier_for_bulk_freight = \
                            conf.packaging_carrier_bulk_freight_id or False

                    if carrier_for_bulk_freight:
                        stock_picking.write({
                            'carrier_id': carrier_for_bulk_freight.id,
                            'uses_bulkfreight': True,
                        })
                    else:
                        raise orm.except_orm(
                            _('No Carrier Defined for Bulk Freight'),
                            _('No carrier delivery was found nor defined in '
                              'the configuration for a bulk freight sending.'))

                else:
                    # We'll split the picking into packages.
                    stock_picking.assign_packages()

        return True

    def check_doing_multi_parcel_deliveries(
            self, cr, uid, ids, soa_info, context=None):
        """ Checks if the sale.order has to do multi-parcel deliveries.
        """
        if context is None:
            context = {}
        if type(ids) is not list:
            ids = [ids]

        conf_data = self.pool.get('configuration.data').\
            get(cr, uid, [], context=context)

        order = self.browse(cr, uid, ids[0], context=context)

        soa_info.message = _("Check doing multi-parcel deliveries.")
        soa_info.next_state = 'print_deliveryorder_in_local'

        if conf_data.packaging_enabled:
            order._do_multi_parcel_deliveries(soa_info)

        return True

    def _print_deliveryorder_in_local(self, cr, uid, ids, soa_info,
                                      picking_id=0, context=None):
        """ Prints the delivery orders associated to a given sale order,
            which must be in state 'open'.
        
            If picking_id == 0, then we print all the delivery orders
            associated to the current sale.order. Otherwise we just print
            the picking with the provided ID (provided that it also belongs
            to the current sale.order).
        """
        if context is None:
            context = {}
        if type(ids) is not list:
            ids = [ids]

        order = self.browse(cr, uid, ids[0], context=context)

        soa_info.message = \
            _("Prints the delivery orders associated to a given sale order")
        soa_info.next_state = 'invoice_open'

        success = order.print_deliveryorder_in_local_before(picking_id)
        success = \
            success and order.print_deliveryorder_in_local_main(picking_id)
        success = \
            success and order.print_deliveryorder_in_local_after(picking_id)

        soa_info.error = not success
        return True

    def print_deliveryorder_in_local_before(
            self, cr, uid, sale_order_id, picking_id=0, context=None):
        """ CAN BE overridden by subclasses to provide code to be executed
            BEFORE the printing & attachment of the delivery slip is done.

            MUST return whether the operation had success or not.

            If picking_id == 0, then we print all the delivery orders
            associated to the current sale.order. Otherwise we just print
            the picking with the provided ID (provided that it also belongs
            to the current sale.order).
        """
        return True

    def print_deliveryorder_in_local_main(
            self, cr, uid, sale_order_id, picking_id=0, context=None):
        """ Prints & attaches the report defined in this module.

            If picking_id == 0, then we print all the delivery orders
            associated to the current sale.order. Otherwise we just print
            the picking with the provided ID (provided that it also belongs
            to the current sale.order).
        """
        return super(sale_order_ext, self).\
            print_and_attach_deliveryorder_report(
                cr, uid, sale_order_id, picking_id, context)

    def print_deliveryorder_in_local_after(
            self, cr, uid, sale_order_id, picking_id=0, context=None):
        """ CAN BE overridden by subclasses to provide code to be executed
            AFTER the printing & attachment of the delivery slip is done.

            MUST return whether the operation had success or not.

            If picking_to_print == 0, then we print all the delivery orders
            associated to the current sale.order. Otherwise we just print
            the picking with the provided ID (provided that it also belongs
            to the current sale.order).
        """
        return True

    def _finish_saleorder_automation(
            self, cr, uid, ids, soa_info, context=None):
        """ NOTICE THAT this method is here just for backwards compatibility,
            and to avoid touching the database while deploying the new version
            of the software. In other words: only jobs which are already in
            this state will arrive here, since new jobs created will end
            its automation in the previous step.
            So this method can be removed a few days / weeks after the
            new code is deployed on all the servers.

            Finishes the sale order automation.

            Note that, because of a back-order, there may be some
            jobs pending in other states.

            We have finished it if we arrived to this state, which means
            that the invoice was printed, and also the delivery slip (at least
            the first one in the case of having back-orders).
        """
        if context is None:
            context = {}
        if type(ids) is not list:
            ids = [ids]

        soa_info.message = _("Finishes the sale.order automation.")
        soa_info.next_state = False

        self.write(cr, uid, ids[0], {'automation_finished': True,
                                     }, context=context)

        return True

    def __clocking_process_saleorder_draft_to_sent(self, cr, uid, ids,
                                                   context=None):
        """ - If the support is opened and the sale order is old enough to
              leave state draft, then it's changed. If not, nothing happens.
            - THE EXCEPTION is that if the support is opened but its
              soft-closing time has passed, then the sale order is allowed
              to move to the next state without considering its aging.

              It returns the datetime of the next attempt to execute the job,
              or False if it can be executed as soon as possible.
        
        :param cr: 
        :param uid: 
        :param ids: 
        :param context: 
        :return: 
        """
        if context is None:
            context = {}
        if type(ids) is not list:
            ids = [ids]

        next_state_time = False

        sale_order = self.browse(cr, uid, ids[0], context=context)
        conf = self.pool.get('configuration.data').\
            get(cr, uid, [], context=context)

        # We store the amount of time to age, and its unit.
        aging_value = conf.sale_order_min_age_in_draft_value
        sale_order_min_age_in_draft_uom = conf.sale_order_min_age_in_draft_uom
        aging_timedelta = timedelta(0)
        if sale_order_min_age_in_draft_uom == 'hours':
            aging_timedelta = timedelta(hours=aging_value)
        elif sale_order_min_age_in_draft_uom == 'days':
            aging_timedelta = timedelta(days=aging_value)
        else:
            raise orm.except_orm(_('Bad Unit of Measurement.'),
                                 _('Bad UOM (Unit of Measurement) indicated '
                                   'for the aging of the sale orders.'))

        # Gets the current time to make the comparison, taking into account
        # the support's time-zone.
        now = datetime.now(pytz.timezone(conf.support_timezone))

        # If we are open now, and we are within the 'fast' time-frame,
        # we just process the sale.order without taking aging into account.
        if self.__support_is_open_now(
                cr, uid, ids, conf, now, conf.support_soft_end_time,
                conf.support_end_time, context):
            next_state_time = False

        # If we are open now, but we are outside the 'fast' time-frame,
        # we may take into account the aging of the sale.order.
        elif self.__support_is_open_now(cr, uid, ids, conf, now,
                                        conf.support_start_time,
                                        conf.support_soft_end_time, context):

            # If we do not have aging, then we process the order right now.
            if not aging_value:
                next_state_time = False

            # On the contrary, if we have aging activated,
            # we must check if it already passed.
            else:
                # We get the *real* creation date of the sale order
                # according to our time-zone.
                sale_order_age_date = datetime.strptime(
                    sale_order.create_date, DEFAULT_SERVER_DATETIME_FORMAT).\
                    replace(tzinfo=pytz.utc).\
                    astimezone(pytz.timezone(conf.support_timezone))
                sale_order_age_date += aging_timedelta

                # If we arrived to the time limit, process it.
                if now >= sale_order_age_date:
                    next_state_time = False

                # If we did not yet arrived, set the next execution date to
                # be whatever happens first: the arrival to the next 'fast'
                # time-frame or the finish of its aging.
                else:
                    # Gets the hours and minutes of the 'fast' time-frame.
                    # Since Odoo stores hours:minutes as floats, we have to
                    # do some math tricks here in order to extract
                    # those fields.
                    support_soft_closing_hour = int(conf.support_soft_end_time)
                    support_soft_closing_min = \
                        int((conf.support_soft_end_time % 1) * 60.0)
                    support_soft_closing_date = \
                        now.replace(hour=support_soft_closing_hour,
                                    minute=support_soft_closing_min,
                                    second=0, microsecond=0)

                    # We set the closing hour as what happens before: either
                    # the real time according to the aging, or to the
                    # next soft-closing time.
                    sale_order_next_state_time = \
                        min(sale_order_age_date, support_soft_closing_date)

                    # We store the date as UTC+0 since jobs use this
                    # time-zone to work.
                    next_state_time = sale_order_next_state_time.astimezone(
                        pytz.timezone('Etc/UTC'))

        # If we are not open now, we must not process the sale.order yet,
        # but set its next execution date as soon as the support opens again.
        else:
            open_days_support = conf.get_open_days_support(context=context)
            support_is_opened_today = open_days_support[now.weekday()]

            # Sets the opening hour of the support for today
            # (even if it does not open today).
            start_hour_support = int(conf.support_start_time)
            start_minute_support = int((conf.support_soft_end_time % 1) * 60.0)
            next_time_to_open = now.replace(
                hour=start_hour_support, minute=start_minute_support,
                second=0, microsecond=0).astimezone(pytz.timezone('Etc/UTC'))

            if support_is_opened_today and (now < next_time_to_open):
                # If support is going to open today, but has not yet opened,
                # return its opening time + the aging.
                next_state_time = (next_time_to_open + aging_timedelta).\
                    astimezone(pytz.timezone('Etc/UTC'))

            else:
                # If not, return the opening time of the next day
                # (which may be closed) + the aging.
                next_state_time = \
                    (next_time_to_open + aging_timedelta + timedelta(1)).\
                        astimezone(pytz.timezone('Etc/UTC'))

        return next_state_time

    def __support_is_open_now(self, cr, uid, ids, config_data, now, open_time,
                              closing_time, context=None):
        """ Receives a datetime object encoding the current date and
            returns if that weekday & hour the support is opened.
        """
        support_is_open = False

        # Checks if the support staff is working today.
        open_days_support = config_data.get_open_days_support(context=context)
        support_is_opened_today = open_days_support[now.weekday()]

        # If the support opens today, checks if we are within the
        # opening & closing hours.
        if support_is_opened_today:
            # Converts the hour to a decimal number.
            current_hour = now.hour + now.minute / 60.0
            if open_time <= current_hour <= closing_time:
                support_is_open = True

        return support_is_open

    def enable_saleorder_automation(self, cr, uid, ids, context=None):
        """ Initiates the automation of a sale.order.
            This method must be called each time the field
            automate_sale_order is checked (set to True).
        """
        if context is None:
            context = {}
        if type(ids) is not list:
            ids = [ids]

        sale_order = self.browse(cr, uid, ids[0], context=context)

        # Automation must only be fired if the order had the field set before.
        if sale_order.automate_sale_order_process_fired:
            return False
        else:
            self.write(cr, uid, sale_order.id, {
                'automate_sale_order_process_fired': True})
            session = ConnectorSession(cr, uid)
            automate_sale_order_process.delay(
                session, 'sale.order', sale_order.id,
                'saleorder_check_inventory_for_quotation',
                priority=sale_order.get_soa_priority())

        return True

    def disable_saleorder_automation(self, cr, uid, ids, context=None):
        """ Method intended to deal with the case in which the
            sale.order's automation is deactivated, or is intended to be
            deactivated, through the user interface.
        """
        return True

    def cron_check_old_draft_sale_orders(self, cr, uid, context=None):
        """ This is an alarming scheduler. It alarms if a sale.order has
            been in state 'draft' for too much time,
            and logs an issue about it.
        """
        if context is None:
            context = {}

        project_issue_obj = self.pool.get('project.issue')

        config_data = self.pool.get('configuration.data').\
            get(cr, uid, [], context=context)

        max_age_in_draft_value = config_data.sale_order_max_age_in_draft_value
        max_age_in_draft_uom = config_data.sale_order_max_age_in_draft_uom

        # If we do not specify an alarming age, we return.
        if max_age_in_draft_value and max_age_in_draft_uom:

            # Gets the border date-time in which the quotation had to be
            # created; if created before that border date-time, then we
            # must alarm.
            now_str = fields.datetime.now()
            now = datetime.strptime(now_str, DEFAULT_SERVER_DATETIME_FORMAT)
            if max_age_in_draft_uom == 'hours':
                order_age_date = \
                    now - timedelta(hours=max_age_in_draft_value)
            elif max_age_in_draft_uom == 'days':
                order_age_date = \
                    now - timedelta(days=max_age_in_draft_value)
            order_age_date = datetime.strftime(
                order_age_date, DEFAULT_SERVER_DATETIME_FORMAT)

            # Logs an issue over each of those quotations.
            old_quotat_ids = self.search(
                cr, uid, [('state', '=', 'draft'),
                          ('create_date', '<', order_age_date),
                          ], context=context)
            for order in self.browse(cr, uid, old_quotat_ids, context=context):
                alarm_message = _('Sale Order {0} (ID={1}) is more than "'
                                  '{2} {3} old since it was created.').\
                    format(order.name, order.id,
                           max_age_in_draft_value, max_age_in_draft_uom)
                project_issue_obj.create_issue(
                    cr, uid, 'sale.order', order.id, alarm_message,
                    tags=['sale', 'sale-exception'], context=context)

        return True

    def _prepare_order_line_procurement(self, cr, uid, order, line, move_id, date_planned, context=None):
        """ Overridden so that the procurement.order will keep track of the
            order which originated it.
        """
        res = super(sale_order_ext, self)._prepare_order_line_procurement(
            cr, uid, order, line, move_id, date_planned, context=context)
        res.update({'sale_id': order.id})
        return res

    def run_service_procurements(self, cr, uid, ids, context=None):
        """ Runs until the end the procurements associated to products
            which are services, to avoid the SOA wait for the execution of the
            MRP scheduler.
        """
        if context is None:
            context = {}
        if not isinstance(ids, list):
            ids = [ids]

        proc_obj = self.pool.get('procurement.order')
        wf_service = netsvc.LocalService('workflow')

        for sale_id in ids:
            proc_ids = proc_obj.search(cr, uid, [
                ('sale_id', '=', sale_id),
                ('product_id.type', '=', 'service'),
                ('state', 'in', ('draft', 'confirmed')),
            ], context=context)
            for proc in proc_obj.browse(cr, uid, proc_ids, context=context):
                if proc.state == 'draft':
                    proc_obj.action_confirm(cr, uid, proc.id, context=context)
                if proc.state == 'confirmed':
                    wf_service.trg_validate(uid, 'procurement.order',
                                            proc.id, 'button_check', cr)

        return True

    def check_all_invoices_created_and_paid(self, cr, uid, ids):
        """ This is for a workflow, so we have no context here.

            This checks that all the invoices associated to a sale.order
            are paid & are associated to a picking of the sale.order.
        """
        if not isinstance(ids, list):
            ids = [ids]

        invoice_obj = self.pool.get('account.invoice')

        for order in self.browse(cr, uid, ids):
            # We only check if the invoice_policy is set to 'delivery' since
            # in that case we are using the sale.order's workflow as if
            # the order_policy was set to 'picking', but being 'manual'
            # actually since we don't want to create the invoice after the
            # picking being delivered, but before, when we validate the order.
            if order.invoice_policy == 'delivery':

                # All the invoices must be paid and have a picking set.
                invoice_ids = []
                for invoice in order.invoice_ids:
                    invoice_ids.append(invoice.id)
                    if invoice.state != 'paid':
                        return False
                    if not invoice.picking_id:
                        return False

                # All the pickings must be associated to an invoice.
                for picking in order.picking_ids:
                    if not bool(invoice_obj.search(cr, uid, [
                        ('picking_id', '=', picking.id),
                        ('id', 'in', invoice_ids),
                    ], count=True, limit=1)):
                        return False

        return True

    _columns = {
        'possible_webshop_ref': fields.char(
            'Possible webshop reference number', select=True,
            help='Yhe webshop reference number is sent attached to the name '
                 'of the sale order, separated from it by a dash character. '
                 'So, if we find a dash in the name of the sale order, it is '
                 'likely (although not sure) that it is the webshop '
                 'reference number.'),
        'manually_force_validation':
            fields.boolean('Manually force validation of sale order'),
        'automate_sale_order_process':
            fields.boolean('Automate Sale Order Process'),
        'automate_sale_order_process_fired':
            fields.boolean('Automate Sale Order Process Was Fired'),
    }

    _defaults = {
        'possible_webshop_ref': False,
        'manually_force_validation': False,
        'automate_sale_order_process': False,
        'automate_sale_order_process_fired': False,
    }

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
