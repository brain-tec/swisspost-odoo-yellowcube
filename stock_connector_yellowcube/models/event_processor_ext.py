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
            if record.state in ['done', 'cancel']:
                return
            if event.code not in ['stock.picking_state_partially_available',
                                  'stock.picking_state_assigned',
                                  ]:
                return
            if code == 'outgoing' or is_return:
                if self.backend_record.yc_parameter_sync_picking_out:
                    self.backend_record.get_processor()\
                        .yc_create_wab_file(event)
            elif code == 'incoming':
                if self.backend_record.yc_parameter_sync_picking_in:
                    self.backend_record.get_processor().\
                        yc_create_wbl_file(event)

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
