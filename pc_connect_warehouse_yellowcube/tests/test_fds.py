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
from yellowcube_testcase import yellowcube_testcase
import subprocess
from tempfile import mkstemp
import os
import time
import socket
from unittest2 import skip
import logging
logger = logging.getLogger(__name__)


class test_fds(yellowcube_testcase):

    _sftp_process = None
    _sftp_key_file = None

    def _unlink_if_exists(self, path):
        if os.path.exists(path):
            os.unlink(path)

    def setUp(self):
        super(test_fds, self).setUp()
        cr, uid, ctx = self.cr, self.uid, self.context
        parameter_obj = self.registry('ir.config_parameter')
        param_value = parameter_obj.get_param(cr, uid, 'test_fds_config')
        self.vals = {}
        fd, self._sftp_key_file = mkstemp(suffix='.key', prefix='sftpserver_test_key', dir='/tmp')
        if param_value:
            self.vals = eval(param_value)
            if self.vals.get('ignore', False):
                logger.warning("Ignoring FDS tests")
                return
            with open(self._sftp_key_file, 'w') as f:
                f.write('Hello World')
        else:
            os.unlink(self._sftp_key_file)
            subprocess.Popen(["ssh-keygen", "-f", self._sftp_key_file, "-t", "rsa", '-N', ""]).wait()
            s = socket.socket()
            s.bind(('', 0))
            port = s.getsockname()[1]
            s.close()
            self._sftp_process = subprocess.Popen(["sftpserver", "-k", self._sftp_key_file, '-p', str(port), '-l', 'DEBUG'], cwd='/tmp', stdout=subprocess.PIPE)
            time.sleep(1)
            self.vals = {
                'server_url': 'localhost:{0}'.format(port),
                'username': 'admin',
                'password': 'admin',
                'rsa_key': None,
            }
        con_obj = self.registry('stock.connect')
        copy_id = con_obj.copy(cr,
                               uid,
                               self.ref('pc_connect_warehouse.demo_connection_1'),
                               context=ctx,
                               default={'connect_transport_id': self.ref('pc_connect_warehouse_yellowcube.fds_dummy_connection')})
        self.stock_connect_id = con_obj.browse(cr, uid, copy_id, ctx)
        self.stock_connect_id.connect_transport_id.write(self.vals)

    def tearDown(self):
        if self._sftp_process:
            self._sftp_process.terminate()
        self._unlink_if_exists(self._sftp_key_file)
        self._unlink_if_exists(self._sftp_key_file + '.pub')
        super(test_fds, self).tearDown()

    def test_connection(self):
        """
        This test tests the connection to an FDS server in local
        """
        if self.vals.get('ignore', False):
            logger.warning("Ignoring FDS tests")
            return
        self.stock_connect_id.connect_transport_id.test_connection()

    def test_connection_list_put_and_get(self):
        """
        This test tests the connection to an FDS server in local, and sends a file.
        """
        if self.vals.get('ignore', False):
            logger.warning("Ignoring FDS tests")
            return
        connection = self.stock_connect_id.connect_transport_id.create_connection()
        connection.open()
        _list = connection.list('.')
        self.assertTrue(isinstance(_list, list), 'returns a dir list')
        # We send a file
        remote_path = './{0}.remote_put'.format(self._sftp_key_file.split('/')[-1])
        connection.put(self._sftp_key_file, remote_path)
        connection.get(remote_path, '{0}.remote_get'.format(self._sftp_key_file))
        connection.close()

        self._unlink_if_exists('{0}.remote_get'.format(self._sftp_key_file))
        self._unlink_if_exists('{0}.remote_put'.format(self._sftp_key_file))

    def test_connection_list_put_and_get_different_connections(self):
        """
        This test tests the connection to an FDS server in local, and sends a file.
        """
        if self.vals.get('ignore', False):
            logger.warning("Ignoring FDS tests")
            return
        connection = self.stock_connect_id.connect_transport_id.create_connection()
        connection.open()
        _list = connection.list('.')
        self.assertTrue(isinstance(_list, list), 'returns a dir list')
        # We send a file
        remote_path = './{0}.remote_put'.format(self._sftp_key_file.split('/')[-1])
        connection.close()
        connection = self.stock_connect_id.connect_transport_id.create_connection()
        connection.open()
        connection.put(self._sftp_key_file, remote_path)
        connection.close()
        connection = self.stock_connect_id.connect_transport_id.create_connection()
        connection.open()
        connection.get(remote_path, '{0}.remote_get'.format(self._sftp_key_file))
        connection.close()

        self._unlink_if_exists('{0}.remote_get'.format(self._sftp_key_file))
        self._unlink_if_exists('{0}.remote_put'.format(self._sftp_key_file))

    def test_stock_connection_methods(self):
        """
        This test tests the stock.connect methods, to make sure everything works ok.
        """
        if self.vals.get('ignore', False):
            logger.warning("Ignoring FDS tests")
            return
        connection = self.stock_connect_id
        connection.connection_get_files()
        connection.connection_send_files()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
