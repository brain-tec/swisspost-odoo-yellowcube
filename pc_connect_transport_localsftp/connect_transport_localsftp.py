# b-*- encoding: utf-8 -*-
##############################################################################
#
#    Copyright (c) 2015 brain-tec AG (http://www.braintec-group.com)
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

from connection_sftp import connection_sftp


class connect_transport_localsftp(osv.Model):
    _inherit = 'connect.transport'
    _name = 'connect.transport.localsftp'

    def test_connection(self, cr, uid, ids, context=None):
        ''' Tests if the connection works OK.
            This usually opens a connection, tests that some folder can be listed, and closes.
        '''
        if context is None:
            context = {}
        if type(ids) is not list:
            ids = [ids]

        l = None
        connection_sftp = self.create_connection(cr, uid, ids[0], context)
        try:
            connection_sftp.open()
            l = connection_sftp.list('.')
        finally:
            connection_sftp.close()
        return l or []

    def create_connection(self, cr, uid, ids, context=None):
        ''' Creates a connection object.
        '''
        if context is None:
            context = {}
        if type(ids) is not list:
            ids = [ids]

        connection = self.pool.get('connect.transport').browse(cr, uid, ids[0], context=context)
        return connection_sftp(url=connection.server_url or None,
                               username=connection.username or None,
                               password=connection.password or None,
                               rsa_key=connection.rsa_key or None)

    _defaults = {'type': 'localsftp',
                 }

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
