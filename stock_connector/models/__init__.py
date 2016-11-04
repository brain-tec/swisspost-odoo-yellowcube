# -*- coding: utf-8 -*-
##############################################################################
#
#    Copyright (c) 2016 brain-tec AG (http://www.braintec-group.com)
#    All Right Reserved
#
#    See LICENSE file for full licensing details.
##############################################################################
from . import product_uom_ext
from . import stock_connector_backend
from . import stock_connector_binding
from . import stock_connector_event
from . import stock_connector_file
from . import stock_connector_file_related_record
from . import stock_connector_transport
from . import backend_processor
from . import event_processor
from openerp.addons.connector import backend
# Here we define the backend and the current version
stock_backend = backend_processor.stock_backend
stock_backend_alpha = backend_processor.stock_backend_alpha