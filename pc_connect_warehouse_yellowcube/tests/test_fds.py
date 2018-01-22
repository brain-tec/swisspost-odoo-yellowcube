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
from yellowcube_testcase import yellowcube_testcase
import os
import logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
from unittest2 import skipIf

UNDER_DEVELOPMENT = False
UNDER_DEVELOPMENT_TEXT = "Test was skipped because of being under development."


class test_fds(yellowcube_testcase):

    _sftp_process = None
    _sftp_key_file = None

    def _unlink_if_exists(self, path):
        if os.path.exists(path):
            if os.path.isfile(path):
                os.unlink(path)
            else:
                for subitem in os.listdir(path):
                    if subitem not in ['.', '..']:
                        self._unlink_if_exists(subitem)
                os.rmdir(path)

    def setUp(self):
        super(test_fds, self).setUp()

    def tearDown(self):
        if self._sftp_process:
            self._sftp_process.terminate()
        self._unlink_if_exists(self._sftp_key_file)
        self._unlink_if_exists(self._sftp_key_file + '.pub')
        for tempdir in self.tempdir:
            logger.info('Directory \'{0}\' must be deleted by user or OS'
                        .format(tempdir))
            # self._unlink_if_exists(tempdir)
        super(test_fds, self).tearDown()

    @skipIf(UNDER_DEVELOPMENT, UNDER_DEVELOPMENT_TEXT)
    def test_connection(self):
        """
        This test tests the connection to an FDS server in local
        """
        self.prepare_test_fds_server()
        if self.vals.get('ignore', False):
            logger.warning("Ignoring FDS tests")
            return
        self.stock_connect_id.connect_transport_id.test_connection()

    @skipIf(UNDER_DEVELOPMENT, UNDER_DEVELOPMENT_TEXT)
    def test_connection_list_put_and_get(self):
        """
        This test tests the connection to an FDS server in local, and sends a file.
        """
        self.prepare_test_fds_server()
        if self.vals.get('ignore', False):
            logger.warning("Ignoring FDS tests")
            return
        connection = self.stock_connect_id.connect_transport_id.create_connection()
        connection.open()
        # We send a file
        remote_path = './{0}.remote_put'.format(self._sftp_key_file.split('/')[-1])
        connection.put(self._sftp_key_file, remote_path)
        _list = connection.list('.')
        self.assertTrue(isinstance(_list, list), 'returns a dir list')
        connection.get(remote_path, '{0}.remote_get'.format(self._sftp_key_file))
        connection.close()

        self._unlink_if_exists('{0}.remote_get'.format(self._sftp_key_file))
        self._unlink_if_exists('{0}.remote_put'.format(self._sftp_key_file))

    @skipIf(UNDER_DEVELOPMENT, UNDER_DEVELOPMENT_TEXT)
    def test_connection_list_put_and_get_different_connections(self):
        """
        This test tests the connection to an FDS server in local, and sends a file.
        """
        self.prepare_test_fds_server()
        if self.vals.get('ignore', False):
            logger.warning("Ignoring FDS tests")
            return
        connection = self.stock_connect_id.connect_transport_id.create_connection()
        # We send a file
        remote_path = './{0}.remote_put'.format(self._sftp_key_file.split('/')[-1])
        connection = self.stock_connect_id.connect_transport_id.create_connection()
        connection.open()
        _list1 = connection.list('.')
        connection.put(self._sftp_key_file, remote_path)
        connection.close()
        self.assertTrue(isinstance(_list1, list), 'returns a list')
        connection = self.stock_connect_id.connect_transport_id.create_connection()
        connection.open()
        _list2 = connection.list('.')
        connection.close()
        self.assertTrue(isinstance(_list2, list), 'returns a list')
        for x in _list2:
            self.assertTrue(isinstance(x, str) or isinstance(x, unicode),
                            'returns a list of str')
        self.assertGreater(len(_list2), len(_list1),
                           'More items are on directory')
        connection = self.stock_connect_id.connect_transport_id.create_connection()
        connection.open()
        connection.get(remote_path, '{0}.remote_get'.format(self._sftp_key_file))
        connection.close()

        self._unlink_if_exists('{0}.remote_get'.format(self._sftp_key_file))
        self._unlink_if_exists('{0}.remote_put'.format(self._sftp_key_file))

    @skipIf(UNDER_DEVELOPMENT, UNDER_DEVELOPMENT_TEXT)
    def test_stock_connection_methods(self):
        """
        This test tests the stock.connect methods, to make sure everything works ok.
        """
        self.prepare_test_fds_server()
        if self.vals.get('ignore', False):
            logger.warning("Ignoring FDS tests")
            return
        connection = self.stock_connect_id
        connection.connection_get_files()
        connection.connection_send_files()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: