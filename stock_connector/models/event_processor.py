# -*- coding: utf-8 -*-
##############################################################################
#
#    Copyright (c) 2016 brain-tec AG (http://www.braintec-group.com)
#    All Right Reserved
#
#    See LICENSE file for full licensing details.
##############################################################################
from openerp import api
from openerp.addons.connector.connector import ConnectorUnit
from .backend_processor import stock_backend_alpha
from .constants import SQL_RELEASE, SQL_ROLLBACK, SQL_SAVEPOINT
import logging

logger = logging.getLogger(__name__)


@stock_backend_alpha
class EventProcessor(ConnectorUnit):
    """
    This class represents the basic functionality in order to process events
    """
    _model_name = 'stock_connector.event'

    def use_failsafe_processing(self):
        logger.debug("Implement your own failsafe check, for safety")
        return True

    def _process_event(self, event):
        savepoint_name = "stock_connector_backend_process_event_%s" % event.id
        if not self.use_failsafe_processing():
            return self.process_event(event)

        result = False
        try:
            with api.Environment.manage():
                self.env.cr.execute(SQL_SAVEPOINT % savepoint_name)
                result = self.process_event(event) or True
        except Exception as e:
            logger.error(str(e))
            old_info = event.info or ''
            self.env.cr.execute(
                SQL_ROLLBACK % savepoint_name)
            event.write({
                'info': 'Exception %s\n\n%s' % (str(e), old_info),
                'state': 'error',
            })
            self.env.invalidate_all()
        else:
            self.env.cr.execute(
                SQL_RELEASE % savepoint_name)
        return result

    def process_event(self, event):
        """
        This is method is override by specific connectors that
         need this functionality

        @param event: Event to process
        @type event: record
        """
        logger.debug('Unimplemented function')

    def process_events(self):
        for event in self.search_open_events():
            self._process_event(event)

    def search_open_events(self):
        """
        @return: list of open events to process
        @rtype: recordset
        """
        return self.model.search([('state', '=', 'ready')])
