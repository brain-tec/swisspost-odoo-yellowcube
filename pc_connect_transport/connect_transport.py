# b-*- encoding: utf-8 -*-
##############################################################################
#
#    Copyright (c) 2015 brain-tec AG (http://www.brain-tec.ch)
#    All Right Reserved
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

from openerp.osv import osv, fields, orm
from openerp.tools.translate import _


# Here we list the types of connections that we are going to support.
PC_CONNECTION_TYPES = [
    ('soap', 'SOAP'),
    ('fds', 'FDS'),
    ('localsftp', 'Local SFTP'),
    ('magentoxmlrpc', 'Magento XML-RPC'),
]


class connect_transport(osv.Model):
    _name = 'connect.transport'

    def test_connection(self, cr, uid, ids, context=None):
        ''' Tests if the connection works OK.
            This usually opens a connection, tests that some folder can be listed, and closes.
        '''
        if context is None:
            context = {}
        if isinstance(ids, list):
            ids = ids[0]

        connection = self.browse(cr, uid, ids, context=context)
        ret = self.pool.get('connect.transport.{type}'.format(type=connection.type)).test_connection(cr, uid, ids, context)
        ctx2 = context.copy()
        ctx2['popup'] = {'name': _('Succesful connection.'),
                         'desc': '\n'.join(ret)}
        return self.pool.get('wizard.popup').show(cr, uid, ctx2)

    def create_connection(self, cr, uid, ids, context=None):
        ''' Creates a connection object.
        '''
        if context is None:
            context = {}

        if isinstance(ids, list):
            ids = ids[0]

        connection = self.browse(cr, uid, ids, context=context)
        return self.pool.get('connect.transport.{type}'.format(type=connection.type)).create_connection(cr, uid, ids, context)

    def _type_installed(self, cr, uid, ids):
        """
        This constraint checks that the type is supported by some model
        """
        for con in self.browse(cr, uid, ids):
            if con.type:
                if not self.pool.get('connect.transport.{0}'.format(con.type)):
                    return False
        return True

    def _type_not_implemented(self, cr, uid, ids):
        """
        This constraint checks that an unimplemented type is not selected
        """
        for con in self.browse(cr, uid, ids):
            if con.type:
                if con.type in ['magentoxmlrpc', 'soap']:
                    return False
        return True

    _columns = {'type': fields.selection(PC_CONNECTION_TYPES, 'Type', required=True, help='The type of the connection.'),
                'name': fields.char('Name', required=True, help='The name of the connection.'),
                'test_mode': fields.boolean('Test mode?', help='If active, no change in the server is done.'),

                # Credentials-related fields.
                'server_url': fields.char('Server URL', help='The URL of the server.'),
                'username': fields.char('Username', help='The username to connect to the server.'),
                'password': fields.char('Password', help='The password to connect to the server.'),
                'rsa_key': fields.text('RSA Private Key', help='The RSA private key to connect to the server.'),
                }

    _defaults = {'test_mode': True,
                 }

    _constraints = [
        (_type_installed, 'Selected type is not present on the server. Install related module', ['type']),
        (_type_not_implemented, 'Selected type is not implemented yet.', ['type']),
    ]
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
