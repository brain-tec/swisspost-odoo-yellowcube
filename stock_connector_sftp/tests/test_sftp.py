# -*- coding: utf-8 -*-
##############################################################################
#
#    Copyright (c) 2016 brain-tec AG (http://www.braintec-group.com)
#    All Right Reserved
#
#    See LICENSE file for full licensing details.
##############################################################################

import subprocess
import os
import time
import socket
import logging
import pip
from tempfile import mkstemp, mkdtemp
import json
from openerp.addons.stock_connector_sftp.models import sftp_transport
from openerp.addons.stock_connector.models import backend_processor
from openerp.tests import TransactionCase
from openerp.tools import safe_eval
logger = logging.getLogger(__name__)


class TestSFTP(TransactionCase):

    _sftp_process = None
    _sftp_key_file = None
    _sftp_config_file = None

    def _unlink_if_exists(self, path):
        if path and os.path.exists(path):
            os.unlink(path)

    def setUp(self):
        super(TestSFTP, self).setUp()
        self.backend = self.env['stock_connector.backend'].create({
            'name': 'Backend SFTP Test',
            'input_path': '.',
            'output_path': '.',
            'remove_remote_files': True,
        })
        self.transport = None

    def prepare_test(self):
        backend_processor.CheckBackends()

        if self.transport:
            return True
        parameter_obj = self.env['ir.config_parameter']
        param_value = parameter_obj.get_param('test_sftp_config')
        self.tmp_server_dir = mkdtemp('test_sftp')
        fd, self._sftp_key_file = mkstemp(suffix='.key',
                                          prefix='sftpserver_test_key',
                                          dir=self.tmp_server_dir)
        if param_value:
            values = safe_eval(param_value)
            if values.get('ignore', False):
                logger.warning("Ignoring sftp tests")
                return False
            with open(self._sftp_key_file, 'w') as f:
                f.write('Hello World')
        else:
            self.assertIn('sftpserver',
                          [x.key for x in pip.get_installed_distributions()],
                          'sftpserver is required for automated tests. '
                          'sudo pip install sftpserver')
            os.unlink(self._sftp_key_file)
            subprocess.call(["ssh-keygen", "-f", self._sftp_key_file,
                             "-t", "rsa", '-N', ""], stdout=subprocess.PIPE)
            s = socket.socket()
            s.bind(('', 0))
            port = s.getsockname()[1]
            s.close()
            self.assertTrue(os.path.exists(self._sftp_key_file))
            self._sftp_process = subprocess.Popen([
                "sftpserver",
                "-k", self._sftp_key_file,
                '-p', str(port),
                '-l', 'INFO'
            ], cwd=self.tmp_server_dir, stdout=subprocess.PIPE)
            time.sleep(1)
            values = {
                'sftp_path': 'localhost:{0}'.format(port),
                'sftp_username': 'admin',
                'sftp_password': 'admin',
                'sftp_rsa_key': None,
                'sftp_read_attrs': False,
            }
            _, self._sftp_config_file = mkstemp()
            with open(self._sftp_config_file, 'w') as fp:
                fp.write(json.dumps(values))
            values = {'sftp_config_file': self._sftp_config_file}
        values2 = {
            'version': 'stock_connector_sftp.transport'
        }
        values2.update(values)
        self.backend.transport_id = self.env['stock_connector.transport']\
            .create(values2)
        self.transport = sftp_transport.SFTPTransport(self.backend)
        self.transport.retries = 0
        return True

    def tearDown(self):
        if self._sftp_process:
            logger.debug('Stopping sftp server')
            self._sftp_process.terminate()
        if self._sftp_key_file:
            self._unlink_if_exists(self._sftp_key_file)
            self._unlink_if_exists(self._sftp_key_file + '.pub')
        self._unlink_if_exists(self._sftp_config_file)
        super(TestSFTP, self).tearDown()

    def test_connection(self):
        """
        This test tests the connection to an SFTP server in local
        """
        if not self.prepare_test():
            logger.warning("Ignoring SFTP tests")
            return
        self.assertTrue(self.backend.test_connection(),
                        'Problem while testing connection')

    def test_connection_list_put_get_and_remove(self):
        """
        This test tests the connection to an SFTP server in local,
        and sends a file.
        """
        if not self.prepare_test():
            logger.warning("Ignoring SFTP tests")
            return
        with self.transport as transport:
            _list = transport.list_dir()
            self.assertTrue(isinstance(_list, list), 'returns a dir list')
            # We send a file
            remote_path = './{0}.remote_put'.format(self._sftp_key_file
                                                    .split('/')[-1])
            transport.connection.put(self._sftp_key_file, remote_path)
            transport.connection.get(remote_path,
                                     '{0}.remote_get'.format(self
                                                             ._sftp_key_file))
            transport.remove_file(remote_path)

        self._unlink_if_exists('{0}.remote_get'.format(self._sftp_key_file))
        self._unlink_if_exists('{0}.remote_put'.format(self._sftp_key_file))

    def test_connection_list_put_get_and_remove_with_attrs(self):
        if not self.prepare_test():
            logger.warning("Ignoring SFTP tests")
            return
        self.backend.transport_id.sftp_read_attrs = True
        self.test_connection_list_put_get_and_remove()

    def test_connection_list_put_and_get_different_connections(self):
        """
        This test tests the connection to an SFTP server in local,
        and sends a file.
        """
        if not self.prepare_test():
            logger.warning("Ignoring SFTP tests")
            return
        with self.transport as transport:
            _list = transport.list_dir()
            self.assertTrue(isinstance(_list, list), 'returns a dir list')
        # We send a file
        remote_path = '{0}.remote_put'.format(self._sftp_key_file
                                              .split('/')[-1])
        with self.transport as transport2:
            transport2.connection.put(self._sftp_key_file, remote_path)
        with self.transport as transport3:
            transport3.connection.get(remote_path,
                                      '{0}.remote_get'.format(self
                                                              ._sftp_key_file))

        self._unlink_if_exists('{0}.remote_get'.format(self._sftp_key_file))
        self._unlink_if_exists('{0}.remote_put'.format(self._sftp_key_file))

    def test_connection_list_put_and_get_different_connections_with_attrs(
            self):
        if not self.prepare_test():
            logger.warning("Ignoring SFTP tests")
            return
        self.backend.transport_id.sftp_read_attrs = True
        self.test_connection_list_put_and_get_different_connections()

    def test_stock_connection_methods(self):
        """
        This test tests the stock.connect methods,
        to make sure everything works ok.
        """
        if not self.prepare_test():
            logger.warning("Ignoring SFTP tests")
            return
        self.assertTrue(self.backend.synchronize_files(),
                        self.backend.output_for_debug)
        self.backend.transport_id.sftp_read_attrs = True
        self.assertTrue(self.backend.synchronize_files(),
                        self.backend.output_for_debug)
