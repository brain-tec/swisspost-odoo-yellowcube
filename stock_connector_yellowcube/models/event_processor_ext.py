# -*- coding: utf-8 -*-
##############################################################################
#
#    Copyright (c) 2016 brain-tec AG (http://www.braintec-group.com)
#    All Right Reserved
#
#    See LICENSE file for full licensing details.
##############################################################################
from openerp.addons.stock_connector import EventProcessor
from .backend_processor_ext import wh_yc_backend
import logging
logger = logging.getLogger(__name__)


@wh_yc_backend
class EventProcessorExt(EventProcessor):

    def process_event(self, event):
        """
        This method will read and process open pickings
        """
        record = event.get_record()
        if event.res_model == 'stock.picking':
            code = record.picking_type_id.code
            is_return = False
            if record.picking_type_id.default_location_dest_id:
                if record.picking_type_id.default_location_dest_id\
                        .return_location:
                    is_return = True

            if record.id == 0:
                logger.debug('Canceling event %s without picking ID'
                             % event.id)
                event.state = 'cancel'
                return
            elif record.state in ['done', 'cancel']:
                logger.debug('Canceling event %s with picking state %s'
                             % (event.id, record.state))
                event.state = 'cancel'
                return
            elif event.code not in ['stock.picking_state_partially_available',
                                    'stock.picking_state_assigned',
                                    ]:
                logger.debug('Ignoring event %s with code %s'
                             % (event.id, event.code))
                if self.backend_record.yc_parameter_cancel_ignored_events:
                    logger.info('Cancelling ignored event %s with code %s'
                                % (event.id, event.code))
                    event.state = 'cancel'
                return
            elif code == 'outgoing' or is_return:
                if self.backend_record.yc_parameter_sync_picking_out:
                    self.backend_record.get_processor()\
                        .yc_create_wab_file(event)
            elif code == 'incoming':
                if self.backend_record.yc_parameter_sync_picking_in:
                    self.backend_record.get_processor().\
                        yc_create_wbl_file(event)
        else:
            logger.debug('Event %s with model %s is unrelated to YC'
                         % (event.id, event.res_model))
        return True

    def search_open_events(self):
        """
        @return: list of open events to process
        @rtype: recordset
        """
        domain = [
            '&',
            ('state', '=', 'ready'),
            ('res_model', '=', 'stock.picking'),
        ]
        return self.model.search(domain)
