# -*- coding: utf-8 -*-
##############################################################################
#
#    Copyright (c) 2016 brain-tec AG (http://www.braintec-group.com)
#    All Right Reserved
#
#    See LICENSE file for full licensing details.
##############################################################################
from openerp.addons.connector.connector import ConnectorUnit
from openerp.addons.connector import backend
import re
import logging
logger = logging.getLogger(__name__)
# Here we define the backend and the current version
stock_backend = backend.Backend('stock')
stock_backend_alpha = backend.Backend(parent=stock_backend, version='0.1')


def CheckBackends():
    for x in [stock_backend, stock_backend_alpha]:
        if x not in backend.BACKENDS.backends:
            backend.BACKENDS.register_backend(x)


@stock_backend_alpha
class BackendProcessor(ConnectorUnit):
    """
    This class represents the basic functionality in order to do general
     actions on a specific backend
    """
    _model_name = 'stock_connector.backend'

    def synchronize(self):
        """
        This is method is override by specific connectors that
         need this functionality

        @param event: Event to process
        @type event: record
        """
        pass

    def test_connection(self):
        transport = self.backend_record.\
            transport_id.get_transport().setup(self.backend_record)
        return transport.test_connection()

    def synchronize_files(self):
        backend = self.backend_record
        with backend.transport_id.get_transport().setup(backend) as transport:
            transport.change_dir(backend.output_path)
            file_obj = self.env['stock_connector.file']
            for out_file in file_obj.search([
                ('backend_id', '=', backend.id),
                ('transmit', '=', 'out'),
                ('state', '=', 'ready'),
            ]):
                transport.send_file(out_file)
            transport.change_dir(None)
            transport.change_dir(backend.input_path)
            if backend.file_regex:
                regex = re.compile(backend.file_regex)
            else:
                regex = None
            for filename in transport.list_dir():
                if regex is None or regex.match(filename):
                    if 0 == file_obj.search([
                        ('name', '=', filename),
                        ('backend_id', '=', backend.id),
                        ('transmit', '=', 'in'),
                        ('state', '!=', 'cancel'),
                    ], limit=1, count=True):
                        transport.get_file(filename)

    def notify_new_event(self, new_event):
        logger.debug('New event notified: %s %s %s' %
                     (new_event.res_model, new_event.res_id, new_event.code))
