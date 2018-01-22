# -*- coding: utf-8 -*-
#
#    Copyright (c) 2017 brain-tec AG (http://www.braintec-group.com)
#    All Right Reserved
#
#    See LICENSE file for full licensing details.

import sys
import traceback
import logging
import copy

from base64 import b64decode

from openerp.osv import fields
from openerp.osv.orm import Model
from openerp import SUPERUSER_ID, sql_db

from .exceptions import (ProfileNotFound, APIException, TooManyProfiles)

_logger = logging.getLogger(__name__)

# this are the same states as defined in pc_connect_warehouse.stock_connect_file
FILE_STATE_DRAFT = 'draft'
FILE_STATE_READY = 'ready'
FILE_STATE_DONE = 'done'
FILE_STATE_CANCEL = 'cancel'

_FILE_STATE = [
    (FILE_STATE_DRAFT, 'Waiting'),
    (FILE_STATE_READY, 'Ready'),
    (FILE_STATE_DONE, 'Finished'),
    (FILE_STATE_CANCEL, 'Ignored'),
]


class ConnectTransportAPI(Model):
    _name = 'connect.transport.api'
    _rec_name = 'name'
    _description = 'Connect Transport API'

    _columns = {
        'name': fields.char('Name', required=True),

        'warehouse_id': fields.many2one('stock.warehouse',
                                        'Warehouse'),
        'stock_connect_id': fields.many2one('stock.connect',
                                            'Connection'),
        'initial_state': fields.selection(_FILE_STATE, 'Initial state'),
        'priority': fields.integer('Priority'),
        'type': fields.char("Type"),
        'input': fields.boolean("Input file"),

        'external_user_id': fields.many2one(
            'res.users', 'Service Public User', required=True),
        'internal_user_id': fields.many2one(
            'res.users', 'Service Internal User', required=True),
        'enable_logs': fields.boolean(
            'Enable Logs',
            help="""Activate the detailed logging in database of all the
                incoming calls."""),
        'logs_all_on_success': fields.boolean(
            'Log all on success',
            help="Logs method arguments on success as well."),
        'stock_connect_file_ids': fields.one2many('stock.connect.file',
                                                  'connect_transport_profile',
                                                  'Files')
    }

    def find_from_ref(self, cr, uid, profile_id, context=None):
        found_ids = self.name_search(cr, SUPERUSER_ID, profile_id, context)

        if not found_ids:
            raise ProfileNotFound(profile_id)
        elif len(found_ids) > 1:
            raise TooManyProfiles(profile_id)

        return found_ids[0][0]

    def api_call(self, cr, uid, ids, method, profile_id, kwargs, context=None):
        """Handle an API call with the internal user."""
        cr.execute("SAVEPOINT connect_transport_api_call")

        try:
            profile_id = self.find_from_ref(cr,
                                            uid,
                                            profile_id,
                                            context)
            profile = self.browse(cr,
                                  SUPERUSER_ID,
                                  profile_id,
                                  context=context)
        except Exception as e:
            cr.execute("ROLLBACK TO SAVEPOINT connect_transport_api_call")

            return {
                'status': 'error',
                'comment': repr(e),
            }
        # check if user using this functions matches the external user
        # specified in the profile
        if uid != profile.external_user_id.id:
            cr.execute("ROLLBACK TO SAVEPOINT connect_transport_api_call")
            return {
                'status': 'error',
                'comment': 'User differs from the service public user '
                           'specified in this profile!',
            }

        internal_user = profile.internal_user_id

        values = {'connect_transport_profile': profile.id,
                  'external_uid': uid,
                  'method': method
                  }

        if 'content' in kwargs:
            kwargs_decoded = copy.deepcopy(kwargs)

            kwargs_decoded['content'] = b64decode(kwargs_decoded['content'])

            values.update({'args': "kwargs (decoded):\n%s" % kwargs_decoded})
        else:
            values.update({'args': "kwargs:\n%s" % kwargs})

        try:
            result = getattr(self, method)(cr,
                                           internal_user.id,
                                           profile,
                                           kwargs,
                                           context=context)
            cr.execute("RELEASE connect_transport_api_call")
        except APIException as e:
            cr.execute("ROLLBACK TO SAVEPOINT connect_transport_api_call")

            result = {
                'status': 'error',
                'comment': repr(e),
            }
            values.update({
                'state': 'failure',
                'exc_info': repr(e),
            })
        except Exception as e:
            cr.execute("ROLLBACK TO SAVEPOINT connect_transport_api_call")

            exc_info = sys.exc_info()

            result = {
                'status': 'error',
                'comment': repr(e),
            }
            values.update({
                'state': 'failure',
                'exc_info': traceback.format_exc(exc_info),
            })
        else:
            values['state'] = 'success'
            if not profile.logs_all_on_success:
                values.pop('args')
        finally:
            if profile.enable_logs:
                new_cr = sql_db.db_connect(cr.dbname).cursor()
                log = self.pool['connect.transport.api.log']
                log.create(new_cr, internal_user.id, values, context)
                new_cr.commit()
                new_cr.close()

        return result

    def create_stock_connect_file(self,
                                  cr,
                                  uid,
                                  profile,
                                  kwargs,
                                  context=None):
        if _logger.isEnabledFor(logging.DEBUG):
            _logger.debug("profile_id: %s, kwargs:%s" % (profile, kwargs))
            _logger.debug("content: %s" % b64decode(kwargs['content']))

        response = self.pool.get('stock.connect.file').create(cr, uid, {
            'content': b64decode(kwargs['content']),
            'name': kwargs['filename'],
            'connect_transport_profile': profile.id,
            'warehouse_id': profile.warehouse_id.id,
            'stock_connect_id': profile.stock_connect_id.id,
            'state': profile.initial_state,
            'priority': profile.priority,
            'type': profile.type,
            'input': profile.input,
            'binary_content': False,
            'model': 'stock.connect.file',
        }, context)

        if _logger.isEnabledFor(logging.DEBUG):
            _logger.debug("response:%s" % response)

        return {
            'status': 'success',
            'id': response,
        }

    def get_connect_file_status(self,
                                cr,
                                uid,
                                profile,
                                kwargs,
                                context=None):
        if _logger.isEnabledFor(logging.DEBUG):
            _logger.debug("kwargs:%s" % kwargs)

        stock_connect_file_obj = self.pool.get('stock.connect.file')

        stock_connect_file_ids = []

        if 'file_ids' in kwargs:
            stock_connect_file_ids.extend(
                stock_connect_file_obj.search(
                    cr, uid, [('id', 'in', kwargs['file_ids'])])
            )

        if 'file_refs' in kwargs:
            stock_connect_file_ids.extend(
                stock_connect_file_obj.search(
                    cr, uid, [('name', 'in', kwargs['file_refs'])])
            )

        connect_files = []

        for stock_connect_file in stock_connect_file_obj.browse(
                cr, uid, list(set(stock_connect_file_ids)), context):
            connect_file = {
                'file_id': stock_connect_file.id,
                'file_ref': stock_connect_file.name,
                'file_state': stock_connect_file.state,
                'file_create_timestamp': stock_connect_file.create_date,
                'file_error': stock_connect_file.error,
                'info_message':
                    stock_connect_file.info if stock_connect_file.info else '',
            }
            connect_files.append(connect_file)

        if _logger.isEnabledFor(logging.DEBUG):
            _logger.debug("connect_files:%s" % connect_files)

        return {
            'status': 'ok',
            'connect_files': connect_files,
        }
