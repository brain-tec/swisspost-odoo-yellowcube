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
from openerp.osv import osv, fields
from openerp.tools.translate import _
from openerp.tools import DEFAULT_SERVER_DATETIME_FORMAT
from openerp.addons.pc_connect_master.utilities.misc import format_exception
import sys
from openerp.addons.pc_connect_warehouse.stock_event import EVENT_STATE_DONE, EVENT_STATE_DRAFT, EVENT_STATE_IGNORED
from openerp.addons.pc_connect_warehouse.stock_connect_file import FILE_STATE_READY, FILE_STATE_DRAFT
from xml_abstract_factory import get_factory
from datetime import timedelta, datetime
from osv.orm import except_orm
from openerp import api
import logging
logger = logging.getLogger(__name__)


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
        file_obj = self.pool['stock.connect.file']
        this = self._this(cr, uid, ids, context)
        ret = file_obj.search(cr, uid,
                              [('stock_connect_id', '=', this.id),
                               ('type', 'in', [_type.upper(), _type.lower()]),
                               # ('binary_content', '=', True),
                               ('input', '=', True),
                               ('error', '!=', True),
                               ],
                              context=context,
                              order='name ASC')

        file_ids = file_obj.search(cr, uid,
                                   [('stock_connect_id', '=', this.id),
                                    ('type', 'in', [False, None, 0]),
                                    # ('binary_content', '=', True),
                                    ('input', '=', True),
                                    ('error', '!=', True),
                                    ],
                                   context=context)
        # This strange query makes sure type is valid, ignoring namespaces
        search_text = 'Type>{0}</'.format(_type)
        _files = file_obj.browse(cr, uid, file_ids, context)
        for _file in _files:
            if search_text in _file.content:
                # We think it is a file of that type, but it is better if the parser it self marks that file
                ret.append(_file.id)
        return ret

    def _process_art_file(self, cr, uid, ids, missing_product_ids=None, context=None):
        if isinstance(ids, list):
            ids = ids[0]
        project_issue_obj = self.pool.get('project.issue')

        this = self.pool['stock.connect'].browse(cr, uid, ids, context)
        if not self.is_type_enabled(cr, uid, ids, 'art', context=context):
            return
        ctx = context.copy()
        env = [self.pool, cr, uid]
        limit_date = datetime.now() - timedelta(hours=this.yc_hours_between_art_files)
        created_art_products = []
        file_obj = self.pool['stock.connect.file']
        for _file in this.stock_connect_file_ids:
            if _file.type == 'art' and _file.input == False:
                if _file.state in [FILE_STATE_READY, FILE_STATE_DRAFT] or datetime.strptime(_file.create_date, DEFAULT_SERVER_DATETIME_FORMAT) > limit_date or \
                        _file.server_ack is False:
                    if _file.model == 'stock.location':
                        complete = True
                        for p in missing_product_ids or []:
                            if ',product.product:{0},'.format(p) not in _file.related_ids:
                                complete = False
                                break
                        if complete or not this.yc_enable_art_ondemand:
                            logger.info("ART file already exists, and was ready to submit.")
                            return
                    elif _file.model == 'product.product':
                        created_art_products.append(_file.res_id)
        art_factory = get_factory(env, 'art', context=ctx)
        if not this.yc_enable_art_multifile:
            created_art_products = None
        elif this.yc_enable_art_ondemand and not missing_product_ids:
            logger.info("ART on demand activated. Not creating nothing automatically.")
            return
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

    def _process_bar_file(self, cr, uid, ids, context):
        this = self._this(cr, uid, ids, context)
        env = [self.pool, cr, uid]
        if not this.is_type_enabled('bar'):
            return
        bar_file_ids = this._find_yc_import_file('BAR')
        if not bar_file_ids:
            return

        project_issue_obj = self.pool.get('project.issue')
        file_obj = self.pool.get('stock.connect.file')
        product_obj = self.pool.get('product.product')
        stock_production_lot_obj = self.pool.get('stock.production.lot')
        stock_connect = self.pool.get('stock.connect').browse(cr, uid, ids[0], context)

        for bar_file in file_obj.browse(cr, uid, bar_file_ids, context):
            if bar_file.state != 'draft' or bar_file.error:
                if stock_connect.log_about_already_existing_files:
                    logger.info('Ignoring bar file {0}#{1}'.format(bar_file.id, bar_file.name))
                continue
            error = None

            new_cr = self.pool.db.cursor()
            try:
                ctx = context.copy()
                ctx['imported_products'] = None
                ctx['imported_lots'] = None
                bar_factory = get_factory(env, 'bar', context=ctx)
                if bar_factory.import_file(bar_file.content):
                    bar_file.write({'type': 'bar',
                                    'state': 'done',
                                    'info': str(ctx['imported_products'])
                                    })
                    if ctx['imported_products']:
                        product_obj.write(cr,
                                          uid,
                                          ctx['imported_products'],
                                          {'yc_last_bar_update': datetime.now().strftime(DEFAULT_SERVER_DATETIME_FORMAT)},
                                          context=ctx)
                    if ctx['imported_lots']:
                        stock_production_lot_obj.write(cr, uid, ctx['imported_lots'],
                                                       {'yc_last_bar_update': datetime.now().strftime(DEFAULT_SERVER_DATETIME_FORMAT)},
                                                       context=ctx)
                else:
                    error = 'Not success'

            except Warning as w:
                self.pool.get('stock.connect').log_issue(cr, uid, ids, _('Error while processing BAR file'), file_id=bar_file.id, context=context, exception=w)
                project_issue_obj.create_issue(cr, uid, 'stock.connect.file', bar_file.id, _('Error while processing BAR file'), context=context)
                if context.get('yc_print_errors', True):
                    logger.error(format_exception(w))
                error = format_exception(w)

            except Exception as e:
                error = format_exception(e)
                project_issue_obj.create_issue(cr, uid, 'stock.connect.file', bar_file.id, error, context=context)
                logger.error('Exception: {0}'.format(error))
                if file_obj.search(new_cr, uid, [('id', '=', bar_file.id)], context=context):
                    file_obj.write(new_cr, uid, bar_file.id, {'error': True, 'info': error}, context=context)
                else:
                    logger.error("Impossible to log error on unsaved BAR file!!! {0}".format(error))
                raise

            finally:
                new_cr.commit()
                new_cr.close()

            if error:
                bar_file.write({'error': True, 'info': error})

    def _process_file(self, cr, uid, ids, xml_type, context=None):
        env = [self.pool, cr, uid]
        this = self._this(cr, uid, ids, context)
        if not this.is_type_enabled(xml_type):
            return
        file_ids = this._find_yc_import_file(xml_type.upper())
        if not file_ids:
            return

        factory = get_factory(env, xml_type.lower(), context=context)
        file_obj = self.pool.get('stock.connect.file')
        stock_connect = self.pool.get('stock.connect').browse(cr, uid, ids[0], context)
        project_issue_obj = self.pool.get('project.issue')

        for _file in file_obj.browse(cr, uid, file_ids, context):
            if _file.state != 'draft' or _file.error:
                if stock_connect.log_about_already_existing_files:
                    logger.info('Ignoring {0} file {1}#{2}'.format(xml_type, _file.id, _file.name))
                continue
            error = None

            new_cr = self.pool.db.cursor()
            try:
                if factory.import_file(_file.content):
                    _file.write({'type': xml_type.lower(),
                                 'state': 'done',
                                 'info': ''
                                 })
                else:
                    error = 'Not success'

            except Warning as w:
                error = '{0} {1}'.format(_('Warning: Error while processing file.'), format_exception(w))
                project_issue_obj.create_issue(cr, uid, 'stock.connect.file', _file.id, error, context=context)
                if context.get('yc_print_errors', True):
                    logger.error(error)
                _file.write({'error': True, 'info': error}, context=context)

            except Exception as e:
                error = '{0} {1}'.format(_('Exception: Error while processing file.'), format_exception(e))
                project_issue_obj.create_issue(cr, uid, 'stock.connect.file', _file.id, error, context=context)
                logger.error(error)
                file_obj.write(new_cr, uid, _file.id, {'error': True, 'info': error}, context=context)
                print 'error>>>' * 5
                print _file.content
                print '<<<error' * 5
                raise

            finally:
                new_cr.commit()
                new_cr.close()

            if error:
                _file.write({'error': True, 'info': error})

    def get_last_file_for_record(self, cr, uid, _id, model, item_id, _type=None, context=None):
        file_obj = self.pool['stock.connect.file']
        domain = [
            ('stock_connect_id', '=', _id),
            ('state', '!=', 'cancel'),
            ('related_ids', 'ilike', ',{0}:{1},'.format(model, item_id or '')),
        ]
        if _type:
            domain.append(('type', '=', _type))
        res = file_obj.search(cr, uid, domain, limit=1, order='id DESC', context=context)
        res = len(res) > 0 and file_obj.browse(cr, uid, res[0], context=context)
        return res or None

    def _process_stock_picking_assigned(self, cr, uid, ids, event_ids, ctx=None):
        if ctx is None:
            ctx = {}

        if isinstance(ids, list) and len(ids) > 1:
            ret = []
            for x in ids:
                ret.extend(self._process_stock_picking_assigned(cr, uid, x, event_ids, ctx=ctx))
            return ret

        conf_data = self.pool.get('configuration.data').get(cr, uid, [], context=ctx)

        today = datetime.today()
        env = [self.pool, cr, uid]

        if ctx:
            context = ctx.copy()
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
        stock_events_ignored = []  # Stores the events to ignore.
        for event_id in event_ids:

            error_message = None

            event = stock_event_obj.browse(cr, uid, event_id, context=context)
            picking_id = event.res_id
            picking = picking_obj.browse(cr, uid, picking_id, context)

            if conf_data.yc_ignore_events_until_process_date:
                if not(picking.process_date):
                    logger.debug("Recomputing process_date for picking {0}".format(picking.name))
                    logger.warning("MISSING add_todo ON V7 !!!")
                if not(picking.process_date) or datetime.strptime(picking.process_date, DEFAULT_SERVER_DATETIME_FORMAT) >= today:
                    event.write({"info": "Ignored until process date is met."})
                    continue

            # Back-orders are never processed
            if picking.do_not_send_to_warehouse or (picking.state != 'assigned'):
                stock_events_ignored.append(event)
                continue

            picking_type = None
            # The following two lines were intended easy the sync between v7 and v8, but ended up polluting the log with tons of Warnings.
#             if hasattr(picking, 'picking_type_id'):
#                 picking_type = picking.picking_type_id.code
            factory = None

            if picking.sale_id and picking_type in ['outgoing', None]:
                factory = wab_factory
            elif picking.purchase_id and picking_type in ['incoming', None]:
                factory = wbl_factory
            else:
                factory = None
            context['warehouse_id'] = event.warehouse_id.id

            try:
                new_cr = self.pool.db.cursor()
                if not factory:
                    raise Warning(_('This stock.picking cannot be processed, it neither has a purchase or a sale order related'))

                related_items = factory.get_related_items(picking_id)
                related_files = []
                product_ids = []
                if self.is_type_enabled(cr, uid, this.id, 'art', context=context):
                    for product_id in related_items.get('product.product', False) or []:
                        msg = None
                        res = self.get_last_file_for_record(cr,
                                                            uid,
                                                            this.id,
                                                            'product.product',
                                                            product_id,
                                                            _type='art',
                                                            context=context)
                        if not res:
                            msg = 'Missing'
                            product_ids.append(product_id)
                        else:
                            if not res.server_ack or res.state != 'done':
                                msg = 'Pending'
                            elif this.yc_hours_between_art_files:
                                delta = timedelta(hours=this.yc_hours_between_art_files)
                                filedate = datetime.strptime(res.create_date, DEFAULT_SERVER_DATETIME_FORMAT)
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

            except Warning as w:
                error_message = _('Warning while processing event on stock.picking with ID {0}: {1}').format(picking_id, format_exception(w))
                if context.get('yc_print_errors', True):
                    logger.error(error_message)
                project_issue_obj.create_issue(new_cr, uid, 'stock.event', event_id, error_message, context=context)

                stock_event_obj.write(new_cr, uid, event.id, {'error': True, 'info': error_message}, context=context)

            except Exception as e:
                error_message = _('Exception while processing event on stock.picking with ID {0}: {1}').format(picking_id, format_exception(e))
                stock_connect_obj.log_issue(new_cr, uid, ids, error_message, event_id=event_id, context=context, exception=e)
                logger.error(error_message)
                project_issue_obj.create_issue(cr, uid, 'stock.event', event_id, error_message, context=context)

                stock_event_obj.write(new_cr, uid, event_id, {'error': True, 'info': error_message}, context=context)

                raise

            finally:
                new_cr.commit()
                new_cr.close()

        # Sets as done all those events which were correctly processed.
        for event_correctly_processed in ret:
            event_correctly_processed.write({'state': EVENT_STATE_DONE, 'info': ''})

        # Sets as ignored the events which are must be ignored.
        for event_to_ignore in stock_events_ignored:
            event_to_ignore.write({'state': EVENT_STATE_IGNORED, 'info': ''})

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
            processed_event_ids = func(cr, uid, ids, event_ids, ctx=context)
        except Exception as e:
            error_message = "Warehouse with ID={0}: Error on event {1}, over events {2}: {3}".format(warehouse_id,
                                                                                                     event_code,
                                                                                                     event_ids,
                                                                                                     format_exception(e))
            logger.error(error_message)
            project_issue_obj.create_issue(cr, uid, 'stock.warehouse', warehouse_id, error_message, context=context)
            raise

        logger.debug("{0} Event {1}: processed {2} of {3} events".format(warehouse_id, event_code, len(processed_event_ids), len(event_ids)))

    def connection_process_events(self, cr, uid, ids, context=None):
        partner_obj = self.pool['res.partner']
        stock_event_obj = self.pool['stock.event']
        stock_connect_obj = self.pool['stock.connect']
        project_issue_obj = self.pool['project.issue']
        if not isinstance(ids, list):
            ids = [ids]
        if context is None:
            context = {}

        func_dir = {
            'new_picking_state_assigned': self._process_stock_picking_assigned,
        }

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
            old_event_ids = [x.id for x in connect.stock_event_ids]

            for warehouse in connect.warehouse_ids:
                for event_code in func_dir:

                    # It is the function passed in the parameter 'func' which must
                    # deal with the exception, not this code.
                    try:
                        self._process_event(cr, uid, [connect.id],
                                            func=func_dir[event_code],
                                            event_code=event_code,
                                            warehouse_id=warehouse.id,
                                            context=context)
                    except Exception as e:
                        # _process_event must raise, but just in case...
                        raise

            # Informs in the log about the untouched events.
            old_event_ids = stock_event_obj.search(cr, uid,
                                                   [('id', 'in', old_event_ids),
                                                    ('event_code', 'in', [x for x in func_dir]),
                                                    ('state', '=', 'draft'),
                                                    ], context=context)
            if old_event_ids:
                logger.debug("Untouched events: {0}".format(old_event_ids))

        logger.debug("Finished checking events on connections.")

        logger.debug("Events finished")
        return True

    def connection_process_files(self, cr, uid, ids, context=None):
        if not isinstance(ids, list):
            ids = [ids]
        if context is None:
            context = {}
        this = self._this(cr, uid, ids, context)

        # First we check the BAR, so new products won't trigger an error if they never went sent by ART
        this._process_bar_file()
        # Then we can send the ART so BAR won't see the new products
        this._process_art_file()
        this._process_file('bur')
        this._process_file('war')
        this._process_file('wba')
        return True

    def cron_check_missing_products_lots_bar(self, cr, uid, context=None):
        ''' Checks for products and lots missing in a BAR update for long time.
        '''
        if context is None:
            context = {}

        project_issue_obj = self.pool.get('project.issue')

        ctx2 = context.copy()
        ctx2['mail_thread_no_duplicate'] = timedelta(days=1)

        # Checking old products missing a BAR update.
        logger.debug("Checking old products missing a BAR update")
        missing_bar_msg = _('The product has pending stock, but no BAR file has submitted an status update.')
        for product_id in self.pool.get('product.product').yc_get_missing_bar_products(cr, uid, None, context):
            logger.debug("Product with ID={0} was old, and an issue is created.".format(product_id))
            issue_ids = project_issue_obj.find_resource_issues(cr, uid, 'product.product', product_id, tags=['missing-bar'], create=True, reopen=True, context=ctx2)
            for issue_id in issue_ids:
                project_issue_obj.message_post(cr, uid, issue_id, missing_bar_msg, context=ctx2)

        # Checking old lots missing a BAR update.
        logger.debug("Checking old lots missing a BAR update")
        missing_lot_msg = _('No stock was reported for the lot in a BAR file since the indicated number of days ago.')
        for lot_id in self.pool.get('stock.production.lot').yc_get_missing_bar_lots(cr, uid, None, context):
            logger.debug("Lot with ID={0} was old, and an issue was created".format(lot_id))
            issue_ids = project_issue_obj.find_resource_issues(cr, uid, 'stock.production.lot', lot_id, tags=['missing-bar'], create=True, reopen=True, context=ctx2)
            for issue_id in issue_ids:
                project_issue_obj.message_post(cr, uid, issue_id, missing_lot_msg, context=ctx2)

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
