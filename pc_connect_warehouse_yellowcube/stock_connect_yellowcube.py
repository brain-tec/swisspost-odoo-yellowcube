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
from openerp.tools import DEFAULT_SERVER_DATETIME_FORMAT
from openerp.addons.pc_connect_master.utilities.others import format_exception
import sys
from openerp.addons.pc_connect_warehouse.stock_event import EVENT_STATE_DONE, EVENT_STATE_DRAFT, EVENT_STATE_IGNORED
from openerp.addons.pc_connect_warehouse.stock_connect_file\
    import FILE_STATE_READY, FILE_STATE_DRAFT, FILE_STATE_DONE, FILE_STATE_CANCEL
from xml_abstract_factory import get_factory
from datetime import timedelta, datetime
from lxml import etree
from openerp import api, SUPERUSER_ID
from openerp.tools.safe_eval import safe_eval
import netsvc

import logging
logger = logging.getLogger(__name__)
if '--test-enable' in sys.argv:
    logger.setLevel(logging.DEBUG)
else:
    logger.setLevel(logging.INFO)


MAX_LEN_OUT_WBA_SUPPLIER_ORDER_NO = 20


class stock_connect_yellowcube(osv.Model):
    _name = "stock.connect.yellowcube"
    _inherit = 'stock.connect'

    def is_type_enabled(self, cr, uid, ids, name, context=None):
        ''' Indicates if a type of Yellowcube (e.g. ART, WAB, etc.) is enabled.
            It only considers the first three letters of the name, e.g. wab_req is wab.
        '''
        if context is None:
            context = {}
        if not isinstance(ids, list):
            ids = [ids]

        type_enabled = False

        stock_connect = self.pool['stock.connect'].browse(cr, uid, ids[0], context)

        # ART is special, since it has three flags to consider it, and just one of them has
        # to be activated in order to consider its type as being enabled.
        if name[:3].lower() == 'art':
            if stock_connect.yc_enable_art_file or stock_connect.yc_enable_art_multifile or stock_connect.yc_enable_art_ondemand:
                type_enabled = True

        # Considers the other types which are not art.
        else:
            field = 'yc_enable_{0}_file'.format(name[:3].lower())

            if hasattr(stock_connect, field):
                if getattr(stock_connect, field) is True:
                    type_enabled = True
            else:
                logger.error("Type '{0}' is not defined in stock.connect".format(name))

        if not type_enabled:
            logger.debug("Type '{0}' is not enabled in stock.connect".format(name))

        return type_enabled

    def _this(self, cr, uid, ids, context):
        if isinstance(ids, list):
            ids = ids[0]
        return self.browse(cr, uid, ids, context)

    @api.cr_uid_ids_context
    def _find_yc_import_file(self, cr, uid, ids, _type, context=None):
        """ Filters by those files which are of the indicated type and which are ready to be processed,
            i.e. in state draft and without an error.
        """
        file_obj = self.pool['stock.connect.file']
        this = self._this(cr, uid, ids, context)
        ret = file_obj.search(cr, uid,
                              [('stock_connect_id', '=', this.id),
                               ('type', 'in', [_type.upper(), _type.lower()]),
                               # ('binary_content', '=', True),
                               ('input', '=', True),
                               ('error', '!=', True),
                               ('state', '=', 'draft'),
                               ],
                              context=context,
                              order='name ASC')

        file_ids = file_obj.search(cr, uid,
                                   [('stock_connect_id', '=', this.id),
                                    ('type', 'in', [False, None, 0]),
                                    # ('binary_content', '=', True),
                                    ('input', '=', True),
                                    ('error', '!=', True),
                                    ('state', '=', 'draft'),
                                    ],
                                   context=context)
        # This strange query makes sure type is valid, ignoring namespaces
        search_text = 'Type>{0}</'.format(_type)
        file_fields_all = file_obj.read(cr, uid, file_ids, ['content', 'id'], context=context)
        for file_fields in file_fields_all:
            if search_text in file_fields['content']:
                # We think it is a file of that type, but it is better if the parser itself marks that file
                ret.append(file_fields['id'])
        return ret

    def _process_art_file(self, cr, uid, ids, missing_product_ids=None, context=None):
        if type(ids) is list:
            ids = ids[0]

        project_issue_obj = self.pool.get('project.issue')

        this = self.pool['stock.connect'].browse(cr, uid, ids, context)
        if not self.is_type_enabled(cr, uid, ids, 'art', context=context):
            return True
        ctx = context.copy()
        env = [self.pool, cr, uid]
        limit_date = datetime.now() - timedelta(hours=this.yc_hours_between_art_files)
        created_art_products = []
        file_obj = self.pool['stock.connect.file']

        art_domain = [
            ('stock_connect_id', '=', this.id),
            ('type', '=', 'art'),
            ('input', '=', False),
            '|',
            # Not yet send
            ('state', 'in', (FILE_STATE_READY, FILE_STATE_DRAFT)),
            '&',
            # Send but too old
            ('state', 'in', (FILE_STATE_DONE,)),
            ('create_date', '>',
             limit_date.strftime(DEFAULT_SERVER_DATETIME_FORMAT))
        ]
        stock_connect_file_ids = file_obj.search(cr, uid, art_domain, context=context)

        fields_to_read = ['create_date', 'model', 'related_ids', 'res_id', 'server_ack', 'state']
        stock_connect_file_fields_all = file_obj.read(cr, uid, stock_connect_file_ids, fields_to_read, context=context)
        for stock_connect_file_fields in stock_connect_file_fields_all:
            if datetime.strptime(stock_connect_file_fields['create_date'], DEFAULT_SERVER_DATETIME_FORMAT) > limit_date or stock_connect_file_fields['server_ack'] is False:
                if stock_connect_file_fields['model'] == 'stock.location':
                    complete = True
                    for p in missing_product_ids or []:
                        if ',product.product:{0},'.format(p) not in stock_connect_file_fields['related_ids']:
                            complete = False
                            break
                    if complete or not this.yc_enable_art_ondemand:
                        if stock_connect_file_fields['state'] == FILE_STATE_DONE:
                            logger.info("ART file exists, and submitted.")
                        else:
                            logger.info("ART file exists, and ready to submit.")
                        return True
                elif stock_connect_file_fields['model'] == 'product.product':
                    created_art_products.append(stock_connect_file_fields['res_id'])

        art_factory = get_factory(env, 'art', context=ctx)
        if not this.yc_enable_art_multifile:
            created_art_products = None
        elif this.yc_enable_art_ondemand and not missing_product_ids:
            logger.info("ART on demand activated. Not creating nothing automatically.")
            return True
        for warehouse in this.warehouse_ids:
            new_cr = self.pool.db.cursor()
            try:
                art_factory.generate_files([('id', '=', warehouse.lot_stock_id.id)],
                                           ignore_product_ids=created_art_products,
                                           force_product_ids=missing_product_ids,
                                           multifile=this.yc_enable_art_multifile)
            except Warning as w:
                ctx['warning'] = format_exception(w)
                self.pool.get('stock.connect').log_issue(cr, uid, ids, _('Error while processing ART file:\n{warning}'), context=ctx, exception=w)
                if context.get('yc_print_errors', True):
                    logger.error(format_exception(w))

            except Exception as e:
                error = '{0}\n{1}'.format(_('Error while processing ART file'), format_exception(e))
                project_issue_obj.create_issue(cr, uid, 'stock.connect', warehouse.id, error, context=context)
                logger.error('Exception: {0}'.format(error))
                self.pool.get('stock.connect').log_issue(new_cr, uid, ids, _('Error while processing ART file'), context=context, exception=e)
                raise

            finally:
                new_cr.commit()
                new_cr.close()

            # Right now, there is no difference between warehouses, so it is enough to create the ART file once.
            break

        return True

    def _process_bar_file(self, cr, uid, ids, context):
        this = self._this(cr, uid, ids, context)
        env = [self.pool, cr, uid]
        if not this.is_type_enabled('bar'):
            return True
        bar_file_ids = this._find_yc_import_file('BAR')
        if not bar_file_ids:
            return True

        project_issue_obj = self.pool.get('project.issue')
        file_obj = self.pool.get('stock.connect.file')
        product_obj = self.pool.get('product.product')
        stock_production_lot_obj = self.pool.get('stock.production.lot')

        fields_to_read = ['content', 'id']
        bar_file_fields_all = file_obj.read(cr, uid, bar_file_ids,
                                            fields_to_read, context=context)
        for bar_file_fields in bar_file_fields_all:
            error = False
            bar_file_id = bar_file_fields['id']

            new_cr = self.pool.db.cursor()
            try:
                ctx = context.copy()
                ctx['imported_products'] = None
                ctx['imported_lots'] = None
                bar_factory = get_factory(env, 'bar', context=ctx)
                if bar_factory.import_file(bar_file_fields['content']):
                    imported_products = []
                    imported_lots = []
                    if 'imported_products' in bar_factory.context:
                        imported_products = \
                            bar_factory.context['imported_products']
                    if 'imported_lots' in bar_factory.context:
                        imported_lots = bar_factory.context['imported_lots']

                    file_obj.write(cr, uid, bar_file_id,
                                               {'type': 'bar',
                                                'state': 'done',
                                                'info': str(imported_products),
                                               }, context=context)
                    if imported_products:
                        product_obj.write(cr,
                                          uid,
                                          imported_products,
                                          {'yc_last_bar_update':
                                           datetime.now().strftime(
                                            DEFAULT_SERVER_DATETIME_FORMAT)},
                                           context=ctx)
                    if imported_lots:
                        # Assuring there are no duplicated imported lots
                        # that might lead to wrong write as ids are duplicated
                        stock_production_lot_obj.write(cr,
                                          uid, list(set(imported_lots)),
                                          {'yc_last_bar_update':
                                          datetime.now().strftime(
                                          DEFAULT_SERVER_DATETIME_FORMAT)},
                                          context=ctx)
                else:
                    error = 'Not success'

            except Warning as w:
                self.pool.get('stock.connect').log_issue(cr, uid, ids,
                                        _('Error while processing BAR file'),
                                        file_id=bar_file_id, context=context,
                                        exception=w)
                project_issue_obj.create_issue(cr, uid, 'stock.connect.file',
                                        bar_file_id,
                                        _('Error while processing BAR file'),
                                        context=context)
                if context.get('yc_print_errors', True):
                    logger.error(format_exception(w))
                error = format_exception(w)

            except Exception as e:
                error = format_exception(e)
                project_issue_obj.create_issue(cr, uid, 'stock.connect.file',
                                               bar_file_id, error,
                                               context=context)
                logger.error('Exception: {0}'.format(error))
                if file_obj.search(new_cr, uid, [('id', '=', bar_file_id)],
                                   context=context):
                    file_obj.write(new_cr, uid, bar_file_id,
                                   {'error': True, 'info': error},
                                   context=context)
                else:
                    logger.error("Impossible to log error on unsaved "
                                 "BAR file!!! {0}".format(error))
                raise

            finally:
                new_cr.commit()
                new_cr.close()

            if error:
                file_obj.write(cr, uid, bar_file_id,
                               {'error': True, 'info': error},
                               context=context)

        return True

    def _process_file(self, cr, uid, ids, xml_type, context=None):
        env = [self.pool, cr, uid]
        this = self._this(cr, uid, ids, context)
        if not this.is_type_enabled(xml_type):
            return True
        file_ids = this._find_yc_import_file(xml_type.upper())
        if not file_ids:
            return True

        file_obj = self.pool.get('stock.connect.file')
        project_issue_obj = self.pool.get('project.issue')

        fields_to_read = ['content', 'id']
        stock_connect_file_fields_all = file_obj.read(cr, uid, file_ids, fields_to_read, context=context)
        for stock_connect_file_fields in stock_connect_file_fields_all:
            file_id = stock_connect_file_fields['id']
            try:
                ctx = context.copy()
                ctx['stock_connect_file_id'] = file_id
                factory = get_factory(env, xml_type.lower(), context=ctx)
                if factory.import_file(stock_connect_file_fields['content']):
                    info  = ''
                    if 'info' in factory.context:
                        info = factory.context['info']
                        
                    file_obj.write(cr, uid, file_id, {'type': xml_type.lower(),
                                                      'state': 'done',
                                                      'info': info,
                                                      }, context=context)
                else:
                    error = 'Not success while importing the contents of the ' \
                            'stock.connect.file with ID={0}'.format(file_id)
                    file_obj.write(cr, uid, file_id,
                                   {'error': True, 'info': error},
                                   context=context)

            except Warning as w:
                error = '{0} {1}'.format(_('Warning: Error while processing file.'), format_exception(w))
                project_issue_obj.create_issue(cr, uid, 'stock.connect.file', file_id, error, context=context)
                if context.get('yc_print_errors', True):
                    logger.error(error)
                file_obj.write(cr, uid, file_id, {'error': True, 'info': error}, context=context)

            except Exception as e:
                error = '{0} {1}'.format(_('Exception: Error while processing file.'), format_exception(e))
                logger.error(error)

                project_issue_obj.create_issue(cr, uid, 'stock.connect.file', file_id, error, context=context)
                file_obj.write(cr, uid, [file_id], {'error': True, 'info': error}, context=context)

                print 'error>>>' * 5
                print stock_connect_file_fields['content']
                print '<<<error' * 5
                return False

        return True

    def _confirm_pickings_by_wba(self, cr, uid, ids, context=None):
        """ Confirms the pickings by the WBA, depending on the value of the
            flag which sets as done the movement and the quantities found in
            the previous WBAs.
        """
        if context is None:
            context = {}
        if type(ids) is not list:
            ids = [ids]

        picking_in_obj = self.pool.get('stock.picking.in')
        stock_connect_obj = self.pool.get('stock.connect')
        project_issue_obj = self.pool.get('project.issue')
        warehouse_obj = self.pool.get('stock.warehouse')
        move_obj = self.pool.get('stock.move')

        self_stock_connect = \
            stock_connect_obj.browse(cr, uid, ids[0], context=context)

        # If this connection doesn't allow WBAs to confirm pickings, we do
        # nothing.
        if not self_stock_connect.yc_wba_confirm:
            return True

        # Computes the frontier for the security WBA-confirmation.
        wba_waiting_timestamp = datetime.now() - \
            timedelta(hours=self_stock_connect.yc_wba_confirm_time)
        wba_waiting_timestamp = wba_waiting_timestamp.strftime(
            DEFAULT_SERVER_DATETIME_FORMAT)

        # Gets the pickings which are associated to this connection.
        warehouse_ids = warehouse_obj.search(cr, uid, [
            ('stock_connect_id', '=', self_stock_connect.id),
        ], context=context)
        picking_in_ids = picking_in_obj.search(cr, uid, [
            ('state', 'in', ['confirmed', 'assigned']),
            ('purchase_id.warehouse_id', 'in', warehouse_ids),
            ], context=context)

        for picking_in in picking_in_obj.browse(cr, uid, picking_in_ids,
                                                context=context):

            # Only considers the pickings that have passed the security
            # time-gap for WBA-confirmation.
            picking_timestamp = \
                picking_in.yellowcube_last_confirmation_timestamp

            if picking_timestamp and picking_timestamp <= wba_waiting_timestamp:

                to_confirm = True

                for move_line in picking_in.move_lines:
                    # if yc_qty_done <= product_qty we will confirm, so
                    # if we found yc_qty_done > product_qty in one single line
                    # we won't confirm the picking in, if this happends we
                    # trigger an alarm.
                    if move_line.yc_qty_done > move_line.product_qty:
                        project_issue_obj.create_issue(
                            cr, uid, 'stock.move', move_line.id,
                            _('WBA cannot confirm an incoming picking if the '
                              'qty on one or more lines are bigger than '
                              'expected!'),
                            context=context)
                        to_confirm = False
                        break

                    if self_stock_connect.yc_wba_respect_eod_flag and not move_line.yc_eod_received \
                                                                  and move_line.yc_qty_done > 0:
                        # If at least one move that does have a confirmed qty
                        # doesn't have the flag for the end of delivery set, 
                        # then we won't confirm the picking.
                        # Because YellowCube will not confirm moves with no
                        # products at all, we ignore lines with no yc_qty_done!
                        # pickings with all positions having qty_done==0 and 
                        # EoD==false should not be affected, because there the 
                        # WBA picking_timestamp is not set at all...
                        to_confirm = False
                        break

                if to_confirm:
                    partials = {}
                    for move_line in picking_in.move_lines:
                        partial_key = 'move{0}'.format(move_line.id)
                        partials[partial_key] = {
                            'product_id': move_line.product_id.id,
                            'product_qty': move_line.yc_qty_done,
                            'product_uom': move_line.product_uom.id,
                            'prodlot_id': move_line.prodlot_id.id,
                        }

                    # We confirm the picking. If it doesn't completely fulfill
                    # the moves, and in that case we'll have a backorder.
                    backorder_id, picking_id = \
                        picking_in.wrapper_do_partial(partials)

                    # If the values are different it's because a backorder
                    # was created.
                    backorder_created = backorder_id and \
                                        (backorder_id != picking_id)
                    if backorder_created:
                        # The lines of the backorder reset the partial
                        # quantities. However the flag of yc_eod_received
                        # must be kept as in the original move.
                        backorder_line_ids = move_obj.search(cr, uid, [
                            ('picking_id', '=', backorder_id),
                        ], context=context)
                        move_obj.write(cr, uid, backorder_line_ids,
                                       {'yc_qty_done': 0.0}, context=context)

                    # If we need to create an invoice for the WBA, we do it.
                    if self_stock_connect.yc_wba_invoice_on_import:
                        picking_in_obj._create_invoice_on_wba(cr, uid,
                                                              picking_id,
                                                              context=context)

        return True

    def _cancel_backorders_by_connection(self, cr, uid, ids, context=None):
        """ Cancels the pickings by the WBA if the have passed the following
            check:
            - The option yc_wba_auto_cancel_backorder is active and
              the waiting time indicated in yc_wba_cancel_time has passed.
            - All the stock.moves have yc_qty_done == 0
            - It is a picking which is a backorder.
        """
        if context is None:
            context = {}
        if type(ids) is not list:
            ids = [ids]

        wf_service = netsvc.LocalService("workflow")
        move_obj = self.pool.get('stock.move')
        picking_in_obj = self.pool.get('stock.picking.in')
        stock_connect_obj = self.pool.get('stock.connect')
        warehouse_obj = self.pool.get('stock.warehouse')

        stock_connect = \
            stock_connect_obj.browse(cr, uid, ids[0], context=context)

        # Gets the pickings which are associated to this connection and which
        # are backorders.
        warehouse_ids = warehouse_obj.search(cr, uid, [
            ('stock_connect_id', '=', stock_connect.id),
        ], context=context)
        backorder_ids = picking_in_obj.search(cr, uid, [
            ('state', 'in', ['confirmed', 'assigned']),
            ('purchase_id.warehouse_id', 'in', warehouse_ids),
            ('backorder_id', '!=', False),
            ], context=context)

        for backorder in picking_in_obj.browse(cr, uid, backorder_ids,
                                               context=context):

            # Computes the frontier for the automatic cancelation.
            cancel_frontier_time = datetime.now() - \
                timedelta(hours=stock_connect.yc_wba_cancel_time)
            cancel_frontier_time = cancel_frontier_time.strftime(
                DEFAULT_SERVER_DATETIME_FORMAT)
            backorder_timestamp = \
                backorder.yellowcube_last_confirmation_timestamp

            # Checks the conditions to cancel the backorder.
            all_moves_qty_done_zero = move_obj.search(cr, uid, [
                ('picking_id', '=', backorder.id),
                ('yc_qty_done', '=', 0.0),
            ], count=True, context=context) == len(backorder.move_lines)
            cancelation_active = \
                bool(stock_connect.yc_wba_auto_cancel_backorder)
            timeout_reached = backorder_timestamp and \
                backorder_timestamp <= cancel_frontier_time
            cancel_backorder = all_moves_qty_done_zero and \
                cancelation_active and timeout_reached

            if cancel_backorder:
                picking_in_obj.action_cancel(cr, uid, [backorder.id],
                                             context=context)

                # If we cancel the back-order then the purchase is
                # kept as having an error in the shipping, thus
                # we need to 'manually' set is as being correct.
                wf_service.trg_validate(uid, 'purchase.order',
                                        backorder.backorder_id.purchase_id.id,
                                        'picking_ok', cr)

                # Also, we have to set the associated event
                # new_picking_state_cancel as ignored, since only
                # the manual cancels are considered for the WBA-0.
                backorder.backorder_id.set_event(
                    picking_state='cancel', event_state='ignore',
                    event_info=_('Ignored because of being '
                                 'cancelled by the flag '
                                 'yc_wba_auto_cancel_backorder.'))

    def get_fields_of_last_file_for_record(self, cr, uid, _id, model, item_id, fields_to_read, _type=None, context=None):
        file_obj = self.pool['stock.connect.file']
        domain = [
            ('stock_connect_id', '=', _id),
            ('state', '!=', 'cancel'),
            ('related_ids', 'ilike', ',{0}:{1},'.format(model, item_id or '')),
        ]
        if _type:
            domain.append(('type', '=', _type))
        res_ids = file_obj.search(cr, uid, domain, limit=1, order='id DESC', context=context)
        if res_ids:
            return file_obj.read(cr, uid, res_ids, fields_to_read, context=context)[0]
        else:
            return None

    def _process_stock_picking_cancel(self, cr, uid, ids, event_ids,
                                    context=None):
        """ Does the work expected when an event of state 'cancel' is
            processed. All the IDs of events stored in the event_ids must be
            of events in state 'cancel.
        """
        if context is None:
            context = {}
        if type(ids) is not list:
            ids = [ids]

        event_obj = self.pool.get('stock.event')
        connect_obj = self.pool.get('stock.connect')
        picking_obj = self.pool.get('stock.picking')

        events_processed_ids = []
        events_to_ignore_ids = []

        if isinstance(ids, list) and len(ids) > 1:
            # If we received a list of IDs instead of a single one, then we
            # call this function over each one of those IDs. This is to avoid
            # using an extra for-loop in the method I guess... The only reason
            # I keep using it this way to make this method consistent with the
            # more known _process_stock_picking_assigned.
            ret = []
            for stock_connect_id in ids:
                ret.extend(self._process_stock_picking_cancel(
                    cr, uid, stock_connect_id, event_ids, context=context))
            return ret

        connection = connect_obj.browse(cr, uid, ids[0], context=context)

        for event in event_obj.browse(cr, uid, event_ids, context=context):
            try:
                picking_id = event.res_id
                picking = picking_obj.browse(cr, uid, picking_id,
                                             context=context)

                if picking.type != 'in':
                    # Pickings which are not of type IN are ignored.
                    events_to_ignore_ids.append(event.id)

                else:
                    # If we set the redirection of the WBA then it's because
                    # we want to redirect them, thus we proceed.
                    if picking.backorder_id:
                        wba_type = 'wba-0'
                    else:
                        wba_type = 'wba-00'
                    events_processed_ids.extend(
                        self.create_outgoing_wba(
                            cr, uid, connection.id, event, wba_type,
                            context=context))

            except Exception:
                raise

        # Sets as ignored all those events which were found to be ignored.
        event_obj.write(cr, uid, events_to_ignore_ids,
                        {'state': EVENT_STATE_IGNORED,
                         'info': _('Event was ignored because it was not '
                                   'an input picking')},
                        context=context)

        # Sets as done all those events which were correctly processed.
        event_obj.write(cr, uid, events_processed_ids,
                        {'state': EVENT_STATE_DONE, 'info': ''},
                        context=context)

        return events_processed_ids

    def _process_stock_picking_done(self, cr, uid, ids, event_ids,
                                    context=None):
        """ Does the work expected when an event of state 'done' is processed.
            All the IDs of events stored in the event_ids must be of
            events in state 'done.
        """
        if context is None:
            context = {}
        if type(ids) is not list:
            ids = [ids]

        event_obj = self.pool.get('stock.event')
        connect_obj = self.pool.get('stock.connect')
        picking_obj = self.pool.get('stock.picking')

        events_processed_ids = []
        events_to_ignore_ids = []

        if isinstance(ids, list) and len(ids) > 1:
            # If we received a list of IDs instead of a single one, then we
            # call this function over each one of those IDs. This is to avoid
            # using an extra for-loop in the method I guess... The only reason
            # I keep using it this way to make this method consistent with the
            # more known _process_stock_picking_assigned.
            ret = []
            for stock_connect_id in ids:
                ret.extend(self._process_stock_picking_done(
                    cr, uid, stock_connect_id, event_ids, context=context))
            return ret

        connection = connect_obj.browse(cr, uid, ids[0], context=context)

        for event in event_obj.browse(cr, uid, event_ids, context=context):
            try:
                picking_id = event.res_id
                picking = picking_obj.browse(cr, uid, picking_id,
                                             context=context)

                if picking.type != 'in':
                    # Pickings which are not of type IN are ignored.
                    events_to_ignore_ids.append(event.id)

                else:
                    if connection.yc_wba_outgoing_redirect:
                        # If we set the redirection of the WBA then it's
                        # because we want to redirect them, thus we proceed.
                        events_processed_ids.extend(
                            self.create_outgoing_wba(
                                cr, uid, connection.id, event, 'outgoing-wba',
                                context=context))
                    else:
                        # Otherwise, we mark those records to be ignored.
                        events_to_ignore_ids.append(event.id)

            except Exception:
                raise

        # Sets as ignored all those events which were found to be ignored.
        event_obj.write(cr, uid, events_to_ignore_ids,
                        {'state': EVENT_STATE_IGNORED,
                         'info': _('Event was ignored because either it was '
                                   'not an input picking or no redirection '
                                   'was active for the Summary WBA.')},
                        context=context)

        # Sets as done all those events which were correctly processed.
        event_obj.write(cr, uid, events_processed_ids,
                        {'state': EVENT_STATE_DONE, 'info': ''},
                        context=context)

        return events_processed_ids

    def create_outgoing_wba(self, cr, uid, connection_id, event, wba_type,
                            context=None):
        """ Creates the three special, outgoing WBAs:
            - the Outgoing-WBA (formerly called Summary-WBA)
            - WBA-0
            - WBA-00

            An Outgoing WBA (formerly: Summarised WBA) is a special type
            of WBA which is like a summarised one, created for events
            of type 'done', this way:

            - Has mainly the same control reference and header data as the
              WBA received from YellowCube.
            - Has the SupplierOrderNo set to the one we got from the
              WBL (on the picking it is the Supplier Reference).
            - Is only one WBA (not a list).
            - Has all the lines from the validated picking in one file.
            - Has the EndOfDelivery flag set (“1”).

            A WBA-0 has the same structure of the Outgoing WBA with the
            difference that all the quantities are set to zero and the
            value of the EndOfDeliveryFlag changes. It is created
            for events of type 'cancel'.
        """
        if context is None:
            context = {}

        connect_file_obj = self.pool.get('stock.connect.file')
        event_obj = self.pool.get('stock.event')
        picking_in_obj = self.pool.get('stock.picking.in')
        issue_obj = self.pool.get('project.issue')
        connect_obj = self.pool.get('stock.connect')

        wba_timestamp = datetime.now().strftime('%Y%m%d%H%M%S')

        connection = \
            connect_obj.browse(cr, uid, connection_id, context=context)
        dest_connection = connection.yc_wba_outgoing_redirect

        events_processed_ids = []

        try:
            new_cr = self.pool.db.cursor()
            event_id = event.id

            # Checks first that the type of the WBA is within the set of the
            # allowed ones.
            if wba_type not in ('outgoing-wba', 'wba-0', 'wba-00'):
                raise Warning(_("Bad option for the type of WBA was "
                                "received: {0}").format(wba_type))

            picking_in = \
                picking_in_obj.browse(cr, uid, event.res_id, context=context)

            supplier_order_no = picking_in.purchase_id.partner_ref or ''
            if len(supplier_order_no) > MAX_LEN_OUT_WBA_SUPPLIER_ORDER_NO:
                supplier_order_no_trunc = \
                    supplier_order_no[:MAX_LEN_OUT_WBA_SUPPLIER_ORDER_NO]
                logger.debug("SupplierOrderNo for WBA by event with ID={0} "
                             "was truncated to {1} chars, from {2} "
                             "to {3}".format(event_id,
                                             MAX_LEN_OUT_WBA_SUPPLIER_ORDER_NO,
                                             supplier_order_no,
                                             supplier_order_no_trunc))
                supplier_order_no = supplier_order_no_trunc

            # Creates the 'outgoing'-wba. <WBA_List> & <WBA>
            outgoing_wba_list = etree.Element('WBA_List')
            outgoing_wba = self.create_element(outgoing_wba_list, 'WBA')

            # Creates the control reference part <ControlReference>
            control_reference = \
                self.create_element(outgoing_wba, 'ControlReference')
            self.create_element(control_reference, 'Type',
                                'WBA')
            self.create_element(control_reference, 'Sender',
                                dest_connection.yc_sender)
            self.create_element(control_reference, 'Receiver',
                                dest_connection.yc_receiver)
            self.create_element(control_reference, 'Timestamp',
                                wba_timestamp)
            self.create_element(control_reference, 'OperatingMode',
                                dest_connection.yc_operating_mode)
            self.create_element(control_reference, 'Version',
                                '1.0')

            # Starts with the content <GoodsReceipt>
            receipt = self.create_element(outgoing_wba, 'GoodsReceipt')
            goods_receipt_header = \
                self.create_element(receipt, 'GoodsReceiptHeader')
            self.create_element(goods_receipt_header, 'BookingVoucherID',
                                '{0:010d}'.format(picking_in.id))
            self.create_element(goods_receipt_header, 'BookingVoucherYear',
                                datetime.now().strftime('%Y'))

            supplier_no = picking_in.partner_id.yc_supplier_no or \
                          connection.yc_supplier_no
            self.create_element(goods_receipt_header, 'SupplierNo',
                                supplier_no)
            self.create_element(goods_receipt_header, 'SupplierOrderNo',
                                supplier_order_no)

            # Then the <GoodsReceiptList> has all the lines from
            # the target picking in one file.
            receipt_list = self.create_element(receipt, 'GoodsReceiptList')

            pos_no = 0
            for move in picking_in.move_lines:
                pos_no += 1
                product = move.product_id

                # Each move goes within its <GoodsReceiptDetail>.
                receipt_detail = \
                    self.create_element(receipt_list, 'GoodsReceiptDetail')

                self.create_element(receipt_detail, 'BVPosNo',
                                    '{0:04d}'.format(pos_no))
                self.create_element(receipt_detail, 'SupplierOrderPosNo',
                                    '{0:05d}'.format(move.yc_posno))

                self.create_element(receipt_detail, 'YCArticleNo',
                                    product.yc_YCArticleNo)
                self.create_element(receipt_detail, 'ArticleNo',
                                    product.default_code)

                if product.ean13:
                    self.create_element(receipt_detail, 'EAN', product.ean13)

                if move.prodlot_id.yellowcube_lot:
                    self.create_element(receipt_detail, 'YCLot',
                                        move.prodlot_id.yellowcube_lot)
                if move.prodlot_id:
                    self.create_element(receipt_detail, 'Lot',
                                        move.prodlot_id.name)

                self.create_element(receipt_detail, 'Plant',
                                    dest_connection.yc_plant_id)

                self.create_element(receipt_detail, 'StorageLocation',
                                    move.location_dest_id.name)

                # Sets the quantity, which is 0 for a WBA-0.
                qty_iso = move.product_uom.uom_iso
                if wba_type == 'outgoing-wba':
                    quantity_uom_value = '{0:0.3f}'.format(move.product_qty)
                    eod_flag = '1' if move.yc_eod_received else '0'
                elif wba_type == 'wba-0':
                    quantity_uom_value = '0'
                    eod_flag = '1'
                else:  # if wba_type == 'wba-00':
                    quantity_uom_value = '0'
                    eod_flag = '2'
                self.create_element(receipt_detail, 'QuantityUOM',
                                    quantity_uom_value,
                                    {'QuantityISO': qty_iso})

                # Sends the EndOfDeliveryFlag exactly as it is on the picking.
                self.create_element(receipt_detail,
                                    'EndOfDeliveryFlag', eod_flag)

            # We validate the WBA created according to the XSD, after
            # repairing it to add the namespaces if needed.
            env = [self.pool, cr, uid]
            wba_factory = get_factory(env, 'wba', context=context)
            summary_wba_list_str = wba_factory.xml_tools.xml_to_string(
                outgoing_wba_list, remove_ns=False, xml_declaration=False)
            outgoing_wba_list = wba_factory.xml_tools.open_xml(
                summary_wba_list_str, repair=True)

            errors = wba_factory.xml_tools.validate_xml(
                'wba', outgoing_wba_list, print_error=False)
            if errors:
                raise Warning('The Summary WBA created contains '
                              'errors: {0}'.format(errors))

            # Creates the new stock.connect.file, containing the
            # summary WBA.
            if wba_type == 'outgoing-wba':
                wba_name = 'WBA_{0}_{1}'.format(supplier_order_no,
                                                wba_timestamp)
            elif wba_type == 'wba-0':
                wba_name = 'WBA-0_{0}_{1}'.format(supplier_order_no,
                                                  wba_timestamp)
            else:  # if wba_type == 'wba-00':
                wba_name = 'WBA-00_{0}_{1}'.format(supplier_order_no,
                                                   wba_timestamp)

            summary_wba_id = connect_file_obj.create(cr, uid, {
                'name': wba_name,
                'warehouse_id': connection.warehouse_ids[0].id,
                'stock_connect_id': dest_connection.id,
                'state': 'ready',
                'type': 'wba',
                'input': False,
                'binary_content': False,
                'model': 'stock.connect.file',
                'is_summary': bool(wba_type == 'outgoing-wba'),
                'content': etree.tostring(outgoing_wba_list,
                                          pretty_print=True,
                                          xml_declaration=True,
                                          encoding="utf-8"),
            }, context=context)

            # If we arrived here we assume that no errors happened and that
            # the event was processed.
            events_processed_ids.append(event.id)

        except Warning as w:
            error_message = \
                _('Warning while processing event in state "done" on '
                  'stock.picking with '
                  'ID {0}: {1}').format(event.res_id,
                                        format_exception(w))
            # If an error happened, we optionally show the error
            # on the log, then create an issue associated to the
            # event and set the event as being errored.
            if context.get('yc_print_errors', True):
                logger.error(error_message)
            issue_obj.create_issue(cr, uid, 'stock.event',
                                   event.id, error_message,
                                   context=context)
            event_obj.write(cr, uid, event.id,
                            {'error': True, 'info': error_message},
                            context=context)

        except Exception as e:
            error_message = \
                _('Exception while processing event in state "done" on '
                  'stock.picking with '
                  'ID {0}: {1}').format(event.res_id,
                                        format_exception(e))

            # If an error happened, we optionally show the error
            # on the log, then create an issue associated to the
            # event and set the event as being errored.
            if context.get('yc_print_errors', True):
                logger.error(error_message)

            issue_obj.create_issue(new_cr, uid, 'stock.event',
                                   event.id, error_message,
                                   context=context)
            event_obj.write(new_cr, uid, event_id,
                            {'error': True, 'info': error_message},
                            context=context)
            raise

        finally:
            new_cr.commit()
            new_cr.close()

        return events_processed_ids

    def create_element(self, parent, name, value=None, attrib=None):
        node = etree.SubElement(parent, name, attrib=attrib)
        if value is not None:
            node.text = value
        return node

    def _process_stock_picking_assigned(self, cr, uid, ids, event_ids, context=None):
        if context is None:
            context = {}
        context['check_date_ready_for_export'] = True

        if isinstance(ids, list) and len(ids) > 1:
            ret = []
            for x in ids:
                ret.extend(self._process_stock_picking_assigned(cr, uid, x, event_ids, context=context))
            return ret

        conf_data = self.pool.get('configuration.data').get(cr, uid, [], context=context)

        today = datetime.today()
        env = [self.pool, cr, uid]

        if context:
            context = context.copy()
        else:
            context = {}

        if 'stock_connect_id' not in context:
            context['stock_connect_id'] = ids[0]
        if 'yc_min_number_attachments' not in context:
            context['yc_min_number_attachments'] = 2

        wab_factory = get_factory(env, 'wab', context=context)
        wbl_factory = get_factory(env, 'wbl', context=context)
        picking_obj = self.pool['stock.picking']
        stock_event_obj = self.pool['stock.event']
        stock_connect_obj = self.pool['stock.connect']
        project_issue_obj = self.pool['project.issue']

        ret = []
        this = self.pool['stock.connect'].browse(cr, uid, ids[0], context)

        # Stores events to be ignored & errored, which are those ones belonging
        # to a picking which was manually removed.
        events_picking_removed_ids = []

        stock_events_ignored = []  # Stores the events to ignore.
        for event in stock_event_obj.browse(cr, uid, event_ids, context=context):

            event_id = event.id
            error_message = None

            picking_id = event.res_id

            # It can happen that the picking related to the event has been
            # manually removed (should never happen, but has happened
            # in the past, so we prepare for it.)
            if not picking_obj.search(cr, SUPERUSER_ID,
                                      [('id', '=', event.res_id),
                                       ], context=context, limit=1):
                events_picking_removed_ids.append(event_id)
                continue

            picking = picking_obj.browse(cr, uid, picking_id, context)

            # For Reserve & Collect just 1 attachments about picking is needed, not the one from the invoice
            if picking.sale_id.carrier_id and picking.sale_id.carrier_id.stock_type_id \
                    and picking.sale_id.carrier_id.stock_type_id.route == 'c+r':
                context['yc_min_number_attachments'] = 1


            if conf_data.yc_ignore_events_until_process_date:
                if not(picking.process_date):
                    logger.debug("Recomputing process_date for picking {0}".format(picking.name))
                    logger.warning("MISSING add_todo ON V7 !!!")
                if not(picking.process_date) or datetime.strptime(picking.process_date, DEFAULT_SERVER_DATETIME_FORMAT) >= today:
                    event.write({"info": "Ignored until process date is met."})
                    continue

            if picking.type == 'out':
                # If the sale order has not finished its automation, then we wait.
                if not picking.sale_id.automation_finished:
                    event.write({"info": "Skipped until associated sale order finishes its automation."})
                    continue

                # If the picking is not yet ready for export, we don't process this event for the moment.
                if not picking.ready_for_export:
                    event.write({"info": "Skipped until the picking is ready for export."})
                    continue

            # Back-orders are never processed
            if picking.do_not_send_to_warehouse or \
                    picking.state in ('draft', 'done', 'cancel'):
                stock_events_ignored.append(event)
                continue

            # We re-use this method for C&C and C&R but only if the state
            # is confirmed; so if the state is confirmed but the route
            # is not one of the routes that can reuse the method (C&C and C&R)
            # then we skip the event.
            if picking.state == 'confirmed' and \
              (picking.get_route() not in ('c+c', 'c+r')):
                stock_events_ignored.append(event)
                continue

            picking_type = None

            if picking.sale_id and picking_type in ['outgoing', None]:
                factory = wab_factory
                factory_type = 'wab'
            elif picking.purchase_id and picking_type in ['incoming', None]:
                factory = wbl_factory
                factory_type = 'wbl'
            else:
                factory = None
                factory_type = None
            context['warehouse_id'] = event.warehouse_id.id

            if factory_type and not self.is_type_enabled(
                    cr, uid, this.id, factory_type, context=context):
                continue

            try:
                new_cr = self.pool.db.cursor()

                # If an exception happens, then the transaction will have
                # not finished, and that will cause the search (at least)
                # to raise an error of the type "InternalError: current
                # transaction is aborted, commands ignored until end
                # of transaction block". So we do all this block within
                # this savepoint, and rollback if an exception happens.
                cr.execute("SAVEPOINT _process_stock_picking_assigned;")

                if not factory:
                    raise Warning(_('This stock.picking cannot be processed, it neither has a purchase or a sale order related'))
                if event.context:
                    factory.context.update(safe_eval(event.context))
                related_items = factory.get_related_items(picking_id)
                related_files = []
                product_ids = []
                if self.is_type_enabled(cr, uid, this.id, 'art', context=context):
                    for product_id in related_items.get('product.product', False) or []:
                        msg = None
                        res = self.get_fields_of_last_file_for_record(cr, uid, this.id,
                                                                      'product.product', product_id,
                                                                      ['create_date', 'server_ack', 'state'],
                                                                      _type='art', context=context)
                        if not res:
                            msg = 'Missing'
                            product_ids.append(product_id)
                        else:
                            if not res['server_ack'] or res['state'] != 'done':
                                msg = 'Pending'
                            elif this.yc_hours_between_art_files:
                                delta = timedelta(hours=this.yc_hours_between_art_files)
                                filedate = datetime.strptime(res['create_date'], DEFAULT_SERVER_DATETIME_FORMAT)
                                if filedate + delta < datetime.today():
                                    msg = 'Out-of-date'
                                    product_ids.append(product_id)
                        # If there is a pending file, we mark it
                        if msg:
                            related_files.append(('product.product', product_id, msg))

                    # Here we create the missing documents that we have a dependency
                    if this.yc_enable_art_ondemand:
                        if this.yc_enable_art_multifile:
                            for p in product_ids:
                                self._process_art_file(cr, uid, this.id, missing_product_ids=[p], context=context)
                        elif product_ids:
                            self._process_art_file(cr, uid, this.id, missing_product_ids=product_ids, context=context)

                if related_files:
                    msg = "There are missing files that must be processed before: {0}".format(related_files)
                    event.write({'info': msg})
                    logger.info(msg)
                else:
                    picking_id = factory.generate_files([('id', '=', picking_id)])
                    if picking_id:
                        ret.append(event)
                cr.execute("RELEASE SAVEPOINT _process_stock_picking_assigned;")

            except Warning as w:
                cr.execute("RELEASE SAVEPOINT _process_stock_picking_assigned;")
                error_message = _('Warning while processing event on stock.picking with ID {0}: {1}').format(picking_id, format_exception(w))
                if context.get('yc_print_errors', True):
                    logger.error(error_message)
                project_issue_obj.create_issue(new_cr, uid, 'stock.event', event_id, error_message, context=context)

                stock_event_obj.write(new_cr, uid, event.id, {'error': True, 'info': error_message}, context=context)

            except Exception as e:
                cr.execute("ROLLBACK TO SAVEPOINT _process_stock_picking_assigned;")
                error_message = _('Exception while processing event on stock.picking with ID {0}: {1}').format(picking_id, format_exception(e))
                stock_connect_obj.log_issue(new_cr, uid, ids, error_message, event_id=event_id, context=context, exception=e, log_issue_no_format=True)
                logger.error(error_message)
                project_issue_obj.create_issue(cr, uid, 'stock.event', event_id, error_message, context=context)

                stock_event_obj.write(new_cr, uid, event_id, {'error': True, 'info': error_message}, context=context)

                # We used to raise here, but we found that just one event
                # could block all the others, thus we simply set the
                # event as errored and we continue, assuming that the events
                # are independent between them (that is, that an event is
                # not going to affect what other does).
                #
                # raise

            finally:
                new_cr.commit()
                new_cr.close()

        # Sets to ignored and errored all those events belonging to a
        # picking which was not found.
        if events_picking_removed_ids:
            stock_event_obj.write(
                cr, uid, events_picking_removed_ids,
                {'state': EVENT_STATE_IGNORED,
                 'error': True,
                 'info': _('Event was marked as being ignored and errored '
                           'because the picking was not found.'),
                 }, context=context)

        # Sets as done all those events which were correctly processed.
        stock_event_obj.write(cr, uid, [event.id for event in ret],
                              {'state': EVENT_STATE_DONE, 'info': ''},
                              context=context)

        # Sets as ignored the events which are must be ignored.
        stock_event_obj.write(cr, uid,
                              [event.id for event in stock_events_ignored],
                              {'state': EVENT_STATE_IGNORED, 'info': ''},
                              context=context)

        del context['check_date_ready_for_export']
        return [x.id for x in ret]

    def _process_event(self, cr, uid, ids, func, event_code, warehouse_id, context=None):
        ''' If something goes wrong, an issue will be logged associated to the current warehouse.
                It is the function passed as the argument 'func' which must log an issue per each
            event which yielded an error.
        '''
        if context is None:
            context = {}

        project_issue_obj = self.pool.get('project.issue')
        stock_event_obj = self.pool.get('stock.event')

        event_ids = stock_event_obj.search(cr, uid, [('warehouse_id', '=', warehouse_id),
                                                     ('event_code', '=', event_code),
                                                     ('state', '=', EVENT_STATE_DRAFT),
                                                     ('error', '=', False),
                                                     ], context=context)

        try:
            processed_event_ids = func(cr, uid, ids, event_ids, context=context)
        except Exception as e:
            error_message = "Warehouse with ID={0}: Error on event {1}, over events {2}: {3}".format(warehouse_id,
                                                                                                     event_code,
                                                                                                     event_ids,
                                                                                                     format_exception(e))
            logger.error(error_message)
            project_issue_obj.create_issue(cr, uid, 'stock.warehouse', warehouse_id, error_message, context=context)
            raise

        logger.debug("{0} Event {1}: processed {2} of {3} events".format(warehouse_id, event_code, len(processed_event_ids), len(event_ids)))
        logger.debug("{0} Event {1}: untouched events: {2}".format(warehouse_id, event_code, list(set(event_ids) - set(processed_event_ids))))

    def connection_process_events(self, cr, uid, ids, context=None):
        partner_obj = self.pool['res.partner']
        stock_event_obj = self.pool['stock.event']
        stock_connect_obj = self.pool['stock.connect']
        project_issue_obj = self.pool['project.issue']
        if type(ids) is not list:
            ids = [ids]
        if context is None:
            context = {}

        this = stock_connect_obj.browse(cr, uid, ids[0], context)

        func_dir = self.get_function_mapping()

        # Sets to be ignored all those events which have an event code
        # which must be ignored and which are not yet ignored.
        event_codes_to_ignore = this.get_event_codes_to_ignore()
        event_to_ignore_ids = stock_event_obj.search(cr, uid, [
            ('event_code', 'in', event_codes_to_ignore),
            ('warehouse_id', 'in', [x.id for x in this.warehouse_ids]),
            ('state', '!=', EVENT_STATE_IGNORED),
            ('error', '=', False),
        ], context=context)
        if event_to_ignore_ids:
            stock_event_obj.write(cr, uid, event_to_ignore_ids, {'state': EVENT_STATE_IGNORED}, context)

        # First, we make sure every partner has correct data.
        # If there was an error with any partner, an exception will be raised.
        # In this case, we mark as failed all the events.
        partner_ids = partner_obj.search(cr, uid, [('ref', 'in', [False, None, ''])], context=context)
        for partner in partner_obj.browse(cr, uid, partner_ids, context=context):
            try:
                partner._validate()

            except Exception as e:
                error_message = _("The validation of partner with ID={0} failed. Error: {1}".format(partner.id, format_exception(e)))
                project_issue_obj.create_issue(cr, uid, 'res.partner', partner.id, error_message, context=context)

                # Over all the events that we were about to process, and that won't be processed because any
                # of the partners do not validate, we do not log an issue to inform about the cause of the problem,
                # because there may be thousands of events, but instead mark them as having being stopped by
                # an error, and indicate which one it is.
                for connect in stock_connect_obj.browse(cr, uid, ids, context=context):
                    for warehouse in connect.warehouse_ids:
                        for event_code in func_dir:
                            new_cr = self.pool.db.cursor()
                            event_ids = stock_event_obj.search(cr, uid, [('warehouse_id', '=', warehouse.id),
                                                                         ('event_code', '=', event_code),
                                                                         ('state', '=', EVENT_STATE_DRAFT),
                                                                         ('error', '=', False),
                                                                         ], context=context)
                            try:
                                stock_event_obj.write(new_cr, uid, event_ids, {'error': True,
                                                                               'info': error_message},
                                                      context=context)
                            finally:
                                new_cr.commit()
                                new_cr.close()
                raise

        logger.debug("Started checking events on connections.")

        for connect in stock_connect_obj.browse(cr, uid, ids, context):
            for warehouse in connect.warehouse_ids:
                for event_code in func_dir:

                    # It is the function passed in the parameter 'func' which 
                    # must deal with the exception, not this code.
                    try:
                        self._process_event(cr, uid, [connect.id],
                                            func=func_dir[event_code],
                                            event_code=event_code,
                                            warehouse_id=warehouse.id,
                                            context=context)
                    except Exception as e:
                        # _process_event must raise, but just in case...
                        raise

        logger.debug("Finished checking events on connections.")

        logger.debug("Events finished")
        return True

    def get_function_mapping(self):
        return {
            'new_picking_state_assigned': self._process_stock_picking_assigned,
            'new_picking_state_done': self._process_stock_picking_done,
            'new_picking_state_cancel': self._process_stock_picking_cancel,
        }

    def connection_process_files(self, cr, uid, ids, context=None):
        if type(ids) is not list:
            ids = [ids]
        if context is None:
            context = {}
        this = self._this(cr, uid, ids, context)

        # First we check the BAR, so new products won't trigger an error
        # if they never went sent by ART
        this._process_bar_file()

        # Then we can send the ART so BAR won't see the new products
        this._process_art_file()

        for file_type in ['bur', 'war', 'wba', 'wbl']:
            if not this._process_file(file_type):
                return False

        # We check if we have to set to done any WBA.
        this._confirm_pickings_by_wba()

        # We check if we have to cancel any backorder.
        this._cancel_backorders_by_connection()

        return True

    def cron_check_missing_products_lots_bar(self, cr, uid, context=None):
        ''' Checks for products and lots missing in a BAR update for long time.
        '''
        if context is None:
            context = {}

        connect_pool = self.pool.get('stock.connect')
        project_issue_obj = self.pool.get('project.issue')
        product_product_obj = self.pool.get('product.product')
        stock_production_lot_obj = self.pool.get('stock.production.lot')

        ctx2 = context.copy()
        ctx2['mail_thread_no_duplicate'] = timedelta(days=1)

        # Gets the number of days to check against.
        connect_ids = connect_pool.search(cr, uid, [('yc_missing_bar_days_due', '>', '0')], context=context, order='yc_missing_bar_days_due DESC')
        for connect_id in connect_ids:
            context['connect_ids'] = [connect_id]

            yc_missing_bar_days_due = connect_pool.read(cr, uid, connect_id, ['yc_missing_bar_days_due'], context=context)['yc_missing_bar_days_due'] or 0

            # Checking old products missing a BAR update.
            logger.debug("Checking old products missing a BAR update")
            missing_bar_msg = _('The product has pending stock, but no BAR file has submitted a status update.')
            product_ids = product_product_obj.yc_get_missing_bar_products(cr, uid, None, context)
            for product in product_product_obj.browse(cr, uid, product_ids, context=context):
                missing_bar_subject = _('Product {0} (ID={1}) has been missing in the BAR since {2} days ago.').format(product.name, product.id, yc_missing_bar_days_due)
                logger.debug("Product with ID={0} was old, and an issue is created.".format(product.id))
                issue_ids = project_issue_obj.find_resource_issues(cr, uid, 'product.product', product.id, tags=['missing-bar'], create=True, reopen=True, context=ctx2)
                for issue_id in issue_ids:
                    project_issue_obj.message_post(cr, uid, issue_id, subject=missing_bar_subject, body=missing_bar_msg, context=ctx2)

            # Checking old lots missing a BAR update.
            logger.debug("Checking old lots missing a BAR update")
            missing_lot_msg = _('No stock was reported for the lot in a BAR file since {0} days ago.').format(yc_missing_bar_days_due)
            lot_ids = stock_production_lot_obj.yc_get_missing_bar_lots(cr, uid, None, context)
            for lot in stock_production_lot_obj.browse(cr, uid, lot_ids, context=context):
                missing_lot_subject = _('Lot {0} (ID={1}) has been missing in the BAR since {2} days ago.').format(lot.name, lot.id, yc_missing_bar_days_due)
                logger.debug("Lot with ID={0} was old, and an issue was created".format(lot.id))
                issue_ids = project_issue_obj.find_resource_issues(cr, uid, 'stock.production.lot', lot.id, tags=['missing-bar'], create=True, reopen=True, context=ctx2)
                for issue_id in issue_ids:
                    project_issue_obj.message_post(cr, uid, issue_id, subject=missing_lot_subject, body=missing_lot_msg, context=ctx2)

            del context['connect_ids']

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
