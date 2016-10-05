# -*- coding: utf-8 -*-
##############################################################################
#
#    Copyright (c) 2016 brain-tec AG (http://www.braintec-group.com)
#    All Right Reserved
#
#    See LICENSE file for full licensing details.
##############################################################################
from openerp.addons.connector.connector import ConnectorUnit
from .backend_processor import stock_backend_alpha


@stock_backend_alpha
class EventProcessor(ConnectorUnit):
    """
    This class represents the basic functionality in order to process events
    """
    _model_name = 'stock_connector.event'

    def process_event(self, event):
        """
        This is method is override by specific connectors that
         need this functionality

        @param event: Event to process
        @type event: record
        """
        pass

    def process_events(self):
        for event in self.search_open_events():
            self.process_event(event)

    def search_open_events(self):
        """
        @return: list of open events to process
        @rtype: recordset
        """
        return self.model.search([('state', '=', 'ready')])
