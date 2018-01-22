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
from datetime import datetime, timedelta
import tools
from pc_connect_master.utilities.date_utilities import get_number_of_natural_days
from openerp.tools import DEFAULT_SERVER_DATETIME_FORMAT
import logging
logger = logging.getLogger(__name__)


ACCEPTED_PRODUCT_TYPES = ['product']


class product_product_ext(osv.Model):
    _inherit = 'product.product'

    def write(self, cr, uid, ids, values, context=None):
        ''' The product can not be saved if there are any validation errors
            (if the product_state is different than 'draft')
        '''

        # Something regarding the product images gave problems if we sent a list to write().
        if type(ids) is not list:
            ids = [ids]
        ret = []
        for prod_id in ids:
            ret.append(super(product_product_ext, self).write(cr, uid, prod_id, values, context))

            product = self.browse(cr, uid, prod_id, context)
            errors_list = []
            if product.type in ACCEPTED_PRODUCT_TYPES:
                if product.product_state != 'draft':
                    errors_list += self._validate_product(cr, uid, prod_id, context)
                errors_list += self._check_error_states(cr, uid, prod_id, context)

            if errors_list:
                raise osv.except_osv(_("Validation error."),
                                     _("Some errors happened while validating the product:\n {0}").format(errors_list))
        return ret

    def action_draft(self, cr, uid, ids, context=None):
        ''' Sets the state to 'draft'.
        '''
        if context is None:
            context = {}
        if not isinstance(ids, list):
            ids = [ids]
        to_write = {'product_state': 'draft',
                    'action_date': fields.datetime.now(),
                    }

        current_product_state = self.browse(cr, uid, ids, context)[0].product_state
        if current_product_state == 'deactivated':
            to_write.update({'moved_manually_to_draft': True,
                             'webshop_state': ''})
        elif current_product_state == 'validated':
            to_write.update({'moved_manually_to_draft': True})

        return self.write(cr, uid, ids, to_write, context)

    def action_validated(self, cr, uid, ids, context=None):
        ''' Sets the state to 'validated'.
        '''
        if context is None:
            context = {}
        return self.write(cr, uid, ids, {'product_state': 'validated',
                                         'action_date': fields.datetime.now(),
                                         'webshop_state': '',
                                         }, context)

    def action_in_production(self, cr, uid, ids, context=None):
        ''' Sets the state to 'in_production'.
        '''
        if context is None:
            context = {}
        return self.write(cr, uid, ids, {'product_state': 'in_production',
                                         'target_state': 'active',  # This field is now in pc_connect_master.
                                         'action_date': fields.datetime.now(),
                                         'webshop_state': 'on_sale',
                                         }, context)

    def action_deactivated(self, cr, uid, ids, context=None):
        ''' Sets the state to 'deactivated'.
        '''
        if context is None:
            context = {}
        return self.write(cr, uid, ids, {'product_state': 'deactivated',
                                         'webshop_state': '',
                                         'action_date': fields.datetime.now(),
                                         }, context)

    def action_end_of_life(self, cr, uid, ids, context=None):
        ''' Sets the state to 'end_of_life'.
        '''
        if context is None:
            context = {}
        return self.write(cr, uid, ids, {'product_state': 'end_of_life',
                                         'target_state': 'inactive',  # This field is now in pc_connect_master.
                                         'action_date': fields.datetime.now(),
                                         'webshop_state': 'not_visible',
                                         }, context)

    def product_product_ids_draft(self, cr, uid, ids, *args):
        ''' Returns the ids of all the products which are in state 'draft'.
        '''
        logger.debug("product_product_ids_draft")
        ids = self.search(cr, uid, [('type', 'in', ACCEPTED_PRODUCT_TYPES), ('id', 'in', ids), ('target_state', '=', 'draft')])
        return ids

    def product_product_ids_validated(self, cr, uid, ids, *args):
        ''' Returns the ids of all the products which are in state 'validated'.
        '''
        logger.debug("product_product_ids_validated")
        ids = self.search(cr, uid, [('type', 'in', ACCEPTED_PRODUCT_TYPES), ('id', 'in', ids), ('target_state', '=', 'validated')])
        return ids

    def product_product_ids_in_production(self, cr, uid, ids, *args):
        ''' Returns the ids of all the products which are in state 'in production'.
        '''
        ids = self.search(cr, uid, [('type', 'in', ACCEPTED_PRODUCT_TYPES), ('id', 'in', ids), ('target_state', '=', 'in_production')])
        return ids

    def product_product_ids_end_of_life(self, cr, uid, ids, *args):
        ''' Returns the ids of all the products which are in state 'end of life'.
        '''
        ids = self.search(cr, uid, [('type', 'in', ACCEPTED_PRODUCT_TYPES), ('id', 'in', ids), ('target_state', '=', 'end_of_life')])
        return ids

    def product_product_ids_deactivated(self, cr, uid, ids, *args):
        ''' Returns the ids of all the products which are in state 'deactivated'.
        '''
        ids = self.search(cr, uid, [('type', 'in', ACCEPTED_PRODUCT_TYPES), ('id', 'in', ids), ('target_state', '=', 'deactivated')])
        return ids

    def _validate_requirements_end_of_life_and_deactivated(self, cr, uid, ids, context=None):
        ''' Returns True if the product validates OK according to the validation rules of US 8.21,
            regarding the end-of-life process and its deactivation.
        '''
        if context is None:
            context = {}

        sale_order_obj = self.pool.get('sale.order')
        sale_order_line_obj = self.pool.get('sale.order.line')
        purchase_order_obj = self.pool.get('purchase.order')
        purchase_order_line_obj = self.pool.get('purchase.order.line')
        stock_picking_obj = self.pool.get('stock.picking')
        stock_move_obj = self.pool.get('stock.move')
        stock_production_lot_obj = self.pool.get('stock.production.lot')
        stock_warehouse_orderpoint_obj = self.pool.get('stock.warehouse.orderpoint')

        errors = []

        for product in self.browse(cr, uid, ids, context=context):

            # Checks that no sale orders in state different than
            # 'done' or 'cancel' contain this product.
            sale_order_ids = sale_order_obj.search(cr, uid, [
                ('state', 'not in', ('done', 'cancel')),
            ], context=context)
            sale_order_line_ids = sale_order_line_obj.search(cr, uid, [
                ('order_id', 'in', sale_order_ids),
                ('product_id', '=', product.id),
            ], context=context)
            sale_ids = list(set([
                x['order_id'][0]
                for x in sale_order_line_obj.read(
                    cr, uid, sale_order_line_ids, ['order_id'],
                    context=context)]))
            if sale_ids:
                errors.append(
                    _("-ERROR: Sale orders that are not in "
                      "state 'done' nor 'cancel' and that contain this "
                      "product: {0}.").format(
                        ', '.join(map(str, sale_ids))))

            # Checks that no open purchase orders in state different than
            # 'done' or 'cancel' contain this product.
            purchase_order_ids = purchase_order_obj.search(cr, uid, [
                ('state', 'not in', ('done', 'cancel')),
            ], context=context)
            purchase_order_line_ids = purchase_order_line_obj.search(cr, uid, [
                ('order_id', 'in', purchase_order_ids),
                ('product_id', '=', product.id),
            ], context=context)
            purchase_ids = list(set([
                x['order_id'][0]
                for x in purchase_order_line_obj.read(
                    cr, uid, purchase_order_line_ids, ['order_id'],
                    context=context)]))
            if purchase_ids:
                errors.append(
                    _("-ERROR: Purchase orders that are not in "
                      "state 'done' nor 'cancel' and that contain this "
                      "product: {0}.").format(
                        ', '.join(map(str, purchase_ids))))

            # Checks that no deliveries in state different than
            # 'done' or 'cancel' contain this product.
            stock_picking_out_ids = stock_picking_obj.search(cr, uid, [
                ('state', 'not in', ('done', 'cancel')),
            ], context=context)
            stock_move_ids = stock_move_obj.search(cr, uid, [
                ('picking_id', 'in', stock_picking_out_ids),
                ('product_id', '=', product.id),
            ], context=context)
            picking_ids = list(set([
                x['picking_id'][0]
                for x in stock_move_obj.read(
                    cr, uid, stock_move_ids, ['picking_id'],
                    context=context)]))
            if picking_ids:
                errors.append(
                    _("-ERROR: Stock pickings that are not in "
                      "state 'done' nor 'cancel' and that contain this "
                      "product: {0}.").format(
                        ', '.join(map(str, picking_ids))))

            # Checks that no stock is present in the warehouse.
            if product.qty_available > 0:
                errors.append(_("-ERROR: This product has a 'quantity on hand' grater than zero ({0} units are available)").format(product.qty_available))
            lot_ids = stock_production_lot_obj.search(cr, uid, [('product_id', '=', product.id)], context=context)
            for lot_id in lot_ids:
                lot = stock_production_lot_obj.browse(cr, uid, lot_id, context=context)
                if lot.stock_available > 0:
                    errors.append(_("-ERROR: Lot {0} with ID={1} contains units of this product.").format(lot.ref, lot_id))

            # Checks that no orderpoints are set for this product.
            orderpoint_ids = stock_warehouse_orderpoint_obj.search(cr, uid, [('active', '=', True),
                                                                             ('product_id', '=', product.id)],
                                                                   context=context)
            for orderpoint_id in orderpoint_ids:
                orderpoint = stock_warehouse_orderpoint_obj.browse(cr, uid, orderpoint_id, context=context)
                errors.append(_("-ERROR: Orderpoint {0} with ID={1} is active for this product.").format(orderpoint.name, orderpoint_id))

        return errors

    def test_requirements_end_of_life_and_deactivated(self, cr, uid, ids, *args):
        ''' Returns true if all the ids fulfill the requirements to pass to
            the states 'end_of_life' or 'deactivated'.
        '''
        logger.debug("test_requirements_end_of_life_and_deactivated")
        for product_id in ids:
            errors_list = self._validate_requirements_end_of_life_and_deactivated(cr, uid, [product_id])
            if len(errors_list) > 0:
                return False
        return True

    def __test_product_target_state(self, cr, uid, ids, target_state):
        logger.debug("__test_product_target_state")
        for product_obj in self.browse(cr, uid, ids):
            if product_obj.target_state != target_state:
                return False
        return True

    def test_product_is_active(self, cr, uid, ids, *args):
        logger.debug("test_product_is_active")
        return self.__test_product_target_state(cr, uid, ids, 'active')

    def test_product_is_inactive(self, cr, uid, ids, *args):
        logger.debug("test_product_is_inactive")
        return self.__test_product_target_state(cr, uid, ids, 'inactive')

    def test_transition_draft_to_validated_can_be_done_automatically(self, cr, uid, ids, *args):
        ''' The transition can not be done automatically if it was set to draft manually.
        '''
        logger.debug("test_transition_draft_to_validated_can_be_done_automatically")
        for product_obj in self.browse(cr, uid, ids):
            if product_obj.moved_manually_to_draft:
                return False
        return True

    def test_trans_end_of_life_to_deactivated_signal(self, cr, uid, ids, *args):
        return self.test_waiting_time_endoflife_to_deactivated(cr, uid, ids, *args) and \
            self.test_requirements_end_of_life_and_deactivated(cr, uid, ids, *args) and \
            self.test_general_validation(cr, uid, ids, *args)

    def test_general_validation(self, cr, uid, ids, *args):
        ''' Returns true if the product passes all the items in the validation checklist.
        '''
        logger.debug("test_general_validation")
        success = True

        if type(ids) is not list:
            ids = [ids]

        for product_id in ids:
            errors_list = self._validate_product(cr, uid, [product_id])
            if len(errors_list) > 0:
                success = False
                break
        return success

    def test_can_go_to_draft(self, cr, uid, ids, *args):
        ''' A product can only go back to draft if either:
            - The product was not submitted to YellowCube.
            - The product was submitted to YellowCube but its state was set as 'deactivated'.
        '''
        logger.debug("test_can_go_to_draft")
        product = self.browse(cr, uid, ids)[0]
        return (not product.last_changeflag_submitted) or \
               (product.last_changeflag_submitted.upper() == 'D')

    def test_waiting_time_endoflife_to_deactivated(self, cr, uid, ids, context=None):
        ''' Checks that the mandatory time between the states 'end of life' to 'deactivated' has passed.
        '''
        if not isinstance(ids, list):
            ids = [ids]
        configuration_data = self.pool.get('configuration.data').get(cr, uid, [])
        time_between_states = configuration_data.clocking_product_lifecycle_from_endoflife_to_deactivated
        uom = configuration_data.clocking_product_lifecycle_from_endoflife_to_deactivated_uom

        # TODO: The checking of the UOM should be done in a more user-friendly way.
        if time_between_states and uom and (uom in ('days', 'hours')):
            time_between_states = float(time_between_states)
            action_date_str = self.browse(cr, uid, ids)[0].action_date
            action_date = datetime.strptime(action_date_str, DEFAULT_SERVER_DATETIME_FORMAT)
            now_str = fields.datetime.now()

            if uom == 'hours':
                difference_secs = tools.get_difference_time_str(action_date_str, now_str)
                time_between_states_secs = time_between_states * 60.0 * 60.0
                if time_between_states_secs >= difference_secs:
                    return False

            # If time is measured in days, then only weekdays are considered.
            else:  # elif uom == 'days':
                num_natural_days = get_number_of_natural_days(action_date, time_between_states, 'forward')
                if (action_date + timedelta(days=num_natural_days)) >= datetime.now():
                    return False

        return True

    
    def onchange_target_state(self, cr, uid, ids, target_state, context=None):
        logger.debug("onchange_target_state")

    def update_workflow(self, cr, uid, ids, context=None):
        ''' Wrapper for method assign_workflow so that it can be called from a button.
        '''
        return self.assign_workflow(cr, uid, context=context)

    def assign_workflow(self, cr, uid, context=None):
        ''' Assigns the workflow to every product which does not have it yet, and
            sets its state in the first one ('draft').
        '''
        if context is None:
            context = {}

        wkf_obj = self.pool.get('workflow')
        wkf_activity_obj = self.pool.get('workflow.activity')
        wkf_instance_obj = self.pool.get('workflow.instance')
        wkf_workitem_obj = self.pool.get('workflow.workitem')

        WORKFLOW_NAME = 'wkf_product_lifecycle'

        # Checks if the workflow exists.
        workflow_id = wkf_obj.search(cr, uid, [('name', '=', WORKFLOW_NAME)], limit=1, context=context)
        if not workflow_id:
            raise osv.except_osv(_('Workflow name error'), _("There is not any workflow with the name '{0}'.").format(WORKFLOW_NAME))
        else:
            workflow_id = workflow_id[0]

        # Caches the workflow's instances related to this workflow.
        workflow_instances_ids = wkf_instance_obj.search(cr, uid, [('res_type', '=', 'product.product'),
                                                                   ('wkf_id', '=', workflow_id),
                                                                   ], context=context)

        # Caches the ID of the first state (draft)
        draft_activity_id = wkf_activity_obj.search(cr, uid, [('wkf_id', '=', workflow_id), ('name', '=', 'draft')], limit=1, context=context)
        if not draft_activity_id:
            raise osv.except_osv(_("Workflow's activity name error"), _("There is not any activity in the workflow with the name 'draft'."))
        else:
            draft_activity_id = draft_activity_id[0]

        domain = []
        if 'active_ids' in context:
            domain = [('id', 'in', context['active_ids'])]
        if 'product_template_active_ids' in context:
            domain = [('product_tmpl_id', 'in', context['product_template_active_ids'])]
        domain.append(('type', 'in', ACCEPTED_PRODUCT_TYPES))

        # Goes through all the products.
        product_ids = self.search(cr, uid, domain, context=context)

        current_product_it = 0
        total_number_of_products = len(product_ids)
        for product_id in product_ids:

            current_product_it += 1
            if current_product_it % 1000 == 0:
                logger.debug("PC_PRODUCT_LIFECYCLE: {0}/{1} products lifecycles have been updated.".format(current_product_it, total_number_of_products))
            # Checks if the product has a workflow associated to it.
            has_workflow_instance = wkf_instance_obj.search(cr, uid, [('id', 'in', workflow_instances_ids),
                                                                      ('res_id', '=', product_id),
                                                                      ], context=context, limit=1, count=True)

            if not has_workflow_instance:
                # If the product does not have a workflow associated to it, creates one.
                workflow_instance_id = wkf_instance_obj.create(cr, uid, {'wkf_id': workflow_id,
                                                                         'uid': uid,
                                                                         'res_id': product_id,
                                                                         'res_type': 'product.product',
                                                                         'state': 'active',
                                                                         }, context)
                # Once the product has been associated a workflow, then we put it in the first state: draft.
                wkf_workitem_obj.create(cr, uid, {'act_id': draft_activity_id,
                                                  'inst_id': workflow_instance_id,
                                                  'state': 'complete',
                                                  }, context)

        logger.debug("PC_PRODUCT_LIFECYCLE: {0}/{0} products lifecycles have been updated.".format(total_number_of_products, total_number_of_products))

    def _check_default_code_rules(self, cr, uid, ids):
        ''' Checks that no other product shares the same default_code, unless it's
            in state 'deactivated'.
        '''
        context = {}
        codes = []
        for product in self.browse(cr, uid, ids, context):
            if product.product_state != 'deactivated':
                codes.append(product.default_code)
        product_ids_count = self.search(cr, uid, [('product_state', '!=', 'deactivated'),
                                                  ('default_code', 'in', codes),
                                                  ('id', 'not in', ids)],
                                        context=context, count=True)
        return (product_ids_count == 0)

    def _validate_product(self, cr, uid, ids, context=None):
        ''' Returns True if the product validates OK according to the validation rules of US 8.21.
        '''
        if context is None:
            context = {}

        if type(ids) is not list:
            ids = [ids]

        product_uom_obj = self.pool.get('product.uom')
        product_category_obj = self.pool.get('product.category')

        errors = []

        # Gets the different configuration data.
        config_data = self.pool.get('configuration.data').get(cr, uid, [])
        price_is_required = config_data.product_lifecycle_force_products_to_have_price
        weight_is_required = config_data.product_lifecycle_force_products_to_have_weight
        name_min_length = config_data.product_lifecycle_name_min_length
        name_max_length = config_data.product_lifecycle_name_max_length
        default_code_min_length = config_data.product_lifecycle_default_code_min_length
        default_code_max_length = config_data.product_lifecycle_default_code_max_length

        ids = self.search(cr, uid, [('id', 'in', ids), ('type', 'in', ACCEPTED_PRODUCT_TYPES)], context=context)

        for product in self.browse(cr, uid, ids, context):

            # Field 'name' must be set and have 1..128 chars.
            if not(product.name and (name_min_length <= len(product.name) <= name_max_length)):
                errors.append(_("-ERROR: Name is not set, or it is set but has a length different than {0}..{1}.").format(name_min_length, name_max_length))

            # Field 'default_code' must be set, and must be unique among those products which are not in
            # state 'deactivated'.
            if not(product.default_code and self._check_default_code_rules(cr, uid, [product.id]) and (default_code_min_length <= len(product.default_code) <= default_code_max_length)):
                errors.append(_("-ERROR: Reference is not set, or it is set but its value is not unique, or it has a length different than {0}..{1}").format(default_code_min_length, default_code_max_length))

            # Field 'categ_id' must be set to an existing product.category.
            if not(product.categ_id and product_category_obj.search(cr, uid, [('id', '=', product.categ_id.id)], context=context)):
                errors.append(_("-ERROR: Pricing/Primary Category is not set, or it is set but its value is not a valid one."))

            # Field 'sale_ok' must be either True or False.
            if product.sale_ok is None:
                errors.append(_("-ERROR: 'Can be Sold' must be either True or False, not NULL."))

            # Field 'type' must be set, and its value must be one of ('product', 'consu', 'service')
            if not(product.type and (product.type in ('product', 'consu', 'service'))):
                errors.append(_("-ERROR: Product Type is not set, or it is set but its value is not one of ('product', 'consu', 'service')."))

            # Field uom_id must be set to an existing product.uom.
            if not(product.uom_id and product_uom_obj.search(cr, uid, [('id', '=', product.uom_id.id)], context=context)):
                errors.append(_("-ERROR: Unit of Measure is not set, or it is set but its value is not a valid one."))

            # Field uom_po_id must be set to an existing product.uom.
            if not(product.uom_po_id and product_uom_obj.search(cr, uid, [('id', '=', product.uom_po_id.id)], context=context)):
                errors.append(_("-ERROR: Purchase Unit of Measure is not set, or it is set but its value is not a valid one."))

            # Fields 'list_price', 'weight', and 'weight_net' must be set to a value greater than zero.
            # In case the product is a service and the field 'product_lifecycle_force_services_to_have_price' is set False, 'list_price'
            # is allowed to be 0.0
            if price_is_required and not(product.list_price and product.list_price > 0):
                errors.append("-ERROR: Sale price is not set, or it is set but its value is not greater than zero.")
            if weight_is_required:
                if not(product.weight and product.weight > 0):
                    errors.append("-ERROR: Weight is not set, or it is set but its value is not greater than zero.")
                if not(product.weight_net and product.weight_net > 0):
                    errors.append("-ERROR: Weight net is not set, or it is set but its value is not greater than zero.")

            # Field 'weight' must be greater or equal than the field 'weight_net'.
            if (product.type != 'service') and (product.weight < product.weight_net):
                errors.append(_("-ERROR: Weight is lower than Weight Net."))

            # Field 'track_production' must be checked if 'track_incoming' or 'track_outgoing' are set.
            if not product.track_production and (product.track_incoming or product.track_outgoing):
                errors.append(_("-ERROR: Field 'track_production' must be checked if 'track_incoming' or 'track_outgoing' are set."))

            # Field 'track_incoming' must be checked if 'track_production' or 'track_outgoing' are set.
            if not product.track_incoming and (product.track_production or product.track_outgoing):
                errors.append(_("-ERROR: Field 'track_incoming' must be checked if 'track_production' or 'track_outgoing' are set."))

            # Field 'track_outgoing' must be checked if 'track_incoming' or 'track_production' are set.
            if not product.track_outgoing and (product.track_incoming or product.track_production):
                errors.append(_("-ERROR: Field 'track_outgoing' must be checked if 'track_incoming' or 'track_production' are set."))

            errors_states = self._check_error_states(cr, uid, ids, context)
            errors = errors + errors_states

        return errors

    def _check_error_states(self, cr, uid, ids, context=None):
        if context is None:
            context = {}

        errors = []

        if type(ids) is list:
            for prod_id in ids:
                t_err = self._check_error_states(cr, uid, prod_id, context)
                for err in t_err:
                    errors.append('{0}: {1}'.format(prod_id, err))
            return errors

        # Here, ids is not a list, but an integer.
        product = self.browse(cr, uid, ids, context=context)

        # Checks that field 'state' has the correct value unless we have
        # set the flag in the configuration to allow free values on it.
        conf = self.pool.get('configuration.data').get(cr, uid, [], context)
        if not conf.plc_allow_free_change_of_webshop_state:

            # Stores the allowed values of webshop_state for any
            # given possible value of product_state.
            allowed_values = {
                'draft': set([False, None, '']),
                'validated': set([False, None, '']),
                'in_production': set(['on_sale', 'visible', 'not_visible',
                                      'not_visible_conditional']),
                'deactivated': set([False, None, '']),
                'end_of_life': set([False, None, '', 'on_sale', 'visible',
                                    'not_visible', 'not_visible_conditional']),
            }

            webshop_state = product.webshop_state
            product_state = product.product_state
            if webshop_state not in allowed_values[product_state]:
                errors.append(_(
                    "-ERROR: Webshop state can not be '{0}' if Target State "
                    "is '{1}'.").format(webshop_state, product_state))

        return errors

    def _stock_moves_exist(self, cr, uid, ids, field, arg, context=None):
        ''' Used in the functional field. Returns true if the product has any stock moves.
        '''
        stock_move_obj = self.pool.get('stock.move')
        logger.debug("_stock_moves_exist")
        res = {}
        for product_id in ids:
            res[product_id] = bool(stock_move_obj.search(cr, uid, [('product_id', '=', product_id),
                                                                   ('state', '!=', 'cancel')]
                                                         , context=context, limit=1, count=True))
        return res
    
    def _product_state_validation(self, cr, uid, ids, field, arg, context=None):
        ''' Used in the functional field. Returns the validation errors for a product.
        '''
        res = {}
        for product in self.browse(cr, uid, ids, context=context):
            if product.type not in ACCEPTED_PRODUCT_TYPES:
                res[product.id] = _('This product type does not uses the lifecycle.')
            else:

                errors_validation = product._validate_product()

                errors_requirements_eol_deactivated = []
                if product.product_state in ('in_production', 'end_of_life'):
                    errors_requirements_eol_deactivated = product._validate_requirements_end_of_life_and_deactivated()
                    if (product.product_state == 'end_of_life') and (not product.test_waiting_time_endoflife_to_deactivated()):
                        errors_validation.append(_("-Because of clocking, it is not possible to pass from state 'end of life' to state 'deactivated' yet."))
                    if errors_requirements_eol_deactivated:
                        errors_validation += (["Regarding passing to states 'end of life' or 'deactivated':"] + errors_requirements_eol_deactivated)

                if errors_validation:
                    res[product.id] = '\n'.join(errors_validation)
                else:
                    res[product.id] = _('No errors were found in the validation.')
        return res

    _columns = {
        'stock_moves_exist': fields.function(_stock_moves_exist, type='boolean', store=False, readonly=True),
        'moved_manually_to_draft': fields.boolean('The stock was manually set to draft.'),

        'product_state_validation': fields.function(_product_state_validation, type='text', store=False, readonly=True),

        # Controls the alarming and the possibility to change from one state to another.
        'action_date': fields.datetime("Timestamp of the workflow's state", readonly=True),
    }

    _defaults = {
        'moved_manually_to_draft': False,
        'action_date': fields.datetime.now(),
    }

    # default_code can be reused between products as long as just one of them is in a state different
    # than 'deactivated'.
    _sql_constraints = [
        ('uniq_default_code',
         'check(1=1)',  # Overrides the unique(default_code) constraint defined in magento_openerp_connector/product_sequence.
         'The reference must be unique'),
    ]
    _constraints = [
        (_check_default_code_rules,
         "Reference field is duplicated with another product which is not in state 'deactivated'.",
         ['default_code'])
    ]
    
    def demo_clean_products_data(self, cr, uid, context=None):
        for product_without_code in self.search(cr, uid, [
            ('default_code', '=', '/')
        ], context=context):
            self.write(cr, uid, product_without_code, {
                'default_code': 'demo/%s' % product_without_code,
            }, context=context)
        for product_without_weight in self.search(cr, uid, [
            ('weight', '=', 0)
        ], context=context):
            self.write(cr, uid, product_without_weight, {
                'weight': 1,
                'weight_net': 1,
            }, context=context)

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
