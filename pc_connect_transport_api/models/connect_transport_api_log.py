# -*- coding: utf-8 -*-
#
#    Copyright (c) 2017 brain-tec AG (http://www.braintec-group.com)
#    All Right Reserved
#
#    See LICENSE file for full licensing details.

from openerp.osv import orm, fields

_STATES = [
    ('success', 'Success'),
    ('failure', 'Failure'),
]


class ConnectTransportAPILog(orm.Model):
    _name = 'connect.transport.api.log'
    _description = 'Connect Transport API Log'
    _order = 'create_date DESC'

    _columns = {
        'connect_transport_profile': fields.many2one(
            'connect.transport.api', 'Connect Transport Profile',
            required=True, readonly=True, select=1),
        'state': fields.selection(
            _STATES, 'State', default='success',
            readonly=True, select=1),
        'method': fields.char('Method Name', readonly=True, select=1),
        'args': fields.text(
            'Method Arguments', help="Kept only on failure.", readonly=True),
        'exc_info': fields.text('Exception', readonly=True),
        'create_date': fields.datetime('Create Date', readonly=True, select=1),
        'external_uid': fields.many2one(
            'res.users', 'User', readonly=True, select=1),
    }
