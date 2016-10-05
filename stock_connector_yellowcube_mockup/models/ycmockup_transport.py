# -*- coding: utf-8 -*-
##############################################################################
#
#    Copyright (c) 2016 brain-tec AG (http://www.braintec-group.com)
#    All Right Reserved
#
#    See LICENSE file for full licensing details.
##############################################################################
import logging
_logger = logging.getLogger(__name__)
_logger.setLevel(logging.DEBUG)


def log_call(logger_function=_logger.debug):
    def _wrapper(f):
        def _wrapped_version(*args, **kargs):
            str_args = []
            str_args.extend(map(str, args[1:]))
            str_args.extend(['%s=%s' % (x, str(kargs[x])) for x in kargs])
            logger_function('%s(%s)' % (f.__name__, ', '.join(str_args)))
            return f(*args, **kargs)
        return _wrapped_version
    return _wrapper


class YCMockupTransport:

    def __init__(self, backend):
        self.backend = backend

    @log_call()
    def test_connection(self):
        return True

    @log_call(_logger.info)
    def send_file(self, connector_file):
        self.backend.transport_id.ycmockup_received_files = [
            (4, connector_file.id),
        ]
        connector_file.state = 'done'
        return

    @log_call(_logger.info)
    def get_file(self, filename):
        transport = self.backend.transport_id
        for file_out in transport.ycmockup_ready_to_send_files:
            if file_out.name == filename:
                file_out.backend_id = self.backend.id
                file_out.transmit = 'in'
                transport.ycmockup_ready_to_send_files = [(3, file_out.id, 0)]
                return
        return

    @log_call()
    def change_dir(self, path):
        return

    @log_call()
    def list_dir(self):
        result = [
            x.name
            for x in self.backend.transport_id.ycmockup_ready_to_send_files
        ]
        return result

    @log_call()
    def open(self):
        return

    @log_call()
    def close(self):
        return

    def __enter__(self):
        self.open()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
