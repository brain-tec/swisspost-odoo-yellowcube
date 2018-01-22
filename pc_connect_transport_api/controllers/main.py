# -*- coding: utf-8 -*-
#
#    Copyright (c) 2017 brain-tec AG (http://www.braintec-group.com)
#    All Right Reserved
#
#    See LICENSE file for full licensing details.
from openerp.addons.web import http

import logging

_logger = logging.getLogger(__name__)


class ConnectTransportController(http.Controller):
    _cp_path = "/transport_api_v1"

    @http.jsonrequest
    def create_stock_connect_file(self,
                                  req,
                                  profile,
                                  *args,
                                  **kwargs):
        return req.session.model('connect.transport.api').api_call(
            [],
            'create_stock_connect_file',
            profile,
            kwargs
        )

    @http.jsonrequest
    def get_connect_file_status(self,
                                req,
                                profile,
                                *args,
                                **kwargs):
        return req.session.model('connect.transport.api').api_call(
            [],
            'get_connect_file_status',
            profile,
            kwargs
        )
