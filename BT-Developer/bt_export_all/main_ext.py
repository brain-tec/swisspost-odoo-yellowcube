# -*- coding: utf-8 -*-

import ast
import base64
import csv
import glob
import itertools
import logging
import operator
import datetime
import hashlib
import os
import re
import simplejson
import time
import urllib
import urllib2
import urlparse
import xmlrpclib
import zlib
from xml.etree import ElementTree
from cStringIO import StringIO

import babel.messages.pofile
import werkzeug.utils
import werkzeug.wrappers
#from numpy.ma.core import ids
try:
    import xlwt
except ImportError:
    xlwt = None

import openerp
import openerp.modules.registry
from openerp.tools.translate import _
from openerp.tools import config

from web import http
openerpweb = http
from web.controllers import main
#from main import content_disposition

import functools

from openerp.osv import osv
from openerp import osv
#from osv import osv, fields, orm
#----------------------------------------------------------
# OpenERP Web helpers
#----------------------------------------------------------



def __new_index(f):
    """
    This function decorates orm.BaseModel.export_data, so multiple language descriptions of a
     record are exported.
    """
    @openerpweb.httprequest
    @functools.wraps(f)
    def __index(self, req, data, token):
        loaded_data = simplejson.loads(data)
        if 'export_all' not in loaded_data:
            loaded_data['export_all'] = False
        model, fields, ids, domain, import_compat, export_all = \
            operator.itemgetter('model', 'fields', 'ids', 'domain',
                                'import_compat', 'export_all')(
                loaded_data)

        Model = req.session.model(model)
        
        #context = req.session.context
        
        if export_all:
            #update context
            req.context.update({'export_all':True})
            
            data = "A Message will be sent to your email address with the required Export"
            advice_filename = "Important_Message.txt"
            content_type='text/txt;charset=utf8'
            
            a=req.make_response(data,
                              headers=[('Content-Disposition',main.content_disposition(advice_filename, req)),
                                       ('Content-Type', content_type)
                                       ],
                              cookies={'fileToken': token}
                              )
            
            field_names = map(operator.itemgetter('name'), fields)
            Export_all= req.session.model('export.all')
            Export_all.export_all(ids, model, field_names, import_compat, req.context)
            
            #import_data = Model.export_data(ids, field_names, req.context).get('datas',[])
            #return werkzeug.wrappers.Response('A file will be sento to you WERKZEUG')
            
            return a

        #normal case
        else:
            req.context.update({'export_all':False})
            ids = ids or Model.search(domain, 0, False, False, req.context)
            field_names = map(operator.itemgetter('name'), fields)
            import_data = Model.export_data(ids, field_names, req.context).get('datas',[])
            if import_compat:
                columns_headers = field_names
            else:
                columns_headers = [val['label'].strip() for val in fields]

            return req.make_response(self.from_data(columns_headers, import_data),
                                     headers=[('Content-Disposition',
                                               main.content_disposition(self.filename(model), req)),
                                              ('Content-Type', self.content_type)],
                                     cookies={'fileToken': token})
    return __index

main.ExportFormat.index = __new_index(main.ExportFormat.index)

# vim:expandtab:tabstop=4:softtabstop=4:shiftwidth=4:
