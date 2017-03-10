# -*- coding: utf-8 -*-
##############################################################################
#
#    Copyright (c) 2016 brain-tec AG (http://www.braintec-group.com)
#    All Right Reserved
#
#    See LICENSE file for full licensing details.
##############################################################################
import paramiko
import time
import tempfile
import logging
from StringIO import StringIO

from paramiko import SSHClient
from paramiko import WarningPolicy

from openerp.exceptions import UserError
from openerp.tools import ustr
import stat
import json
_logger = logging.getLogger(__name__)
# _logger.setLevel(logging.DEBUG)


class SFTPTransport:

    transport = None
    connection = None

    def __init__(self, backend):
        self.backend = backend
        json_config = {}
        if backend.transport_id.sftp_config_file:
            with open(backend.transport_id.sftp_config_file, 'r') as fp:
                json_config = json.load(fp)
            _logger.debug('Values found on config file: %s',
                          (','.join([x for x in json_config
                                     if json_config[x]])))
        self.username = backend.transport_id.sftp_username or\
            json_config.get('sftp_username', None)
        self.password = backend.transport_id.sftp_password or\
            json_config.get('sftp_password', None)
        self.path = backend.transport_id.sftp_path or\
            json_config.get('sftp_path', None)
        self.rsa_key = backend.transport_id.sftp_rsa_key or\
            json_config.get('sftp_rsa_key', None)
        self.read_attrs = backend.transport_id.sftp_read_attrs
        self.retries = 3

    def test_connection(self):
        with self:
            try:
                stdin, stdout, stderr = self.transport.exec_command('locale')
                _logger.info('locale: %s' % stdout.read())
            except Exception as e:
                _logger.info('Error when querying for locale: %s' % str(e))
            _logger.debug(self.list_dir())
        return True

    def send_file(self, connector_file):
        with tempfile.NamedTemporaryFile() as temp:
            temp.write(connector_file.content)
            temp.flush()
            # Requires version 1.7.7
            self.connection.put(temp.name, connector_file.name, confirm=False)
            connector_file.state = 'done'

    def get_file(self, filename):
        try:
            with tempfile.NamedTemporaryFile() as temp:
                self.connection.get(filename, temp.name)
                content = file(temp.name).read()
                self.backend.env['stock_connector.file'].create({
                    'backend_id': self.backend.id,
                    'name': filename,
                    'transmit': 'in',
                    'content': ustr(content),
                })
        except:
            _logger.error('get_file(%s)' % filename)
            raise

    def remove_file(self, filename):
        _logger.info('External file removed %s' % filename)
        self.connection.remove(filename)

    def change_dir(self, path):
        self.connection.chdir(path)

    def list_dir(self):
        result = []
        if self.read_attrs:
            for remote_file in self.connection.listdir_attr():
                if remote_file.st_mode & stat.S_IFREG:
                    result.append(remote_file.filename)
        else:
            for name in self.connection.listdir():
                result.append(name)
        return result

    def open(self):
        """
        Opens an SFTP connection.
        """
        # Gets the key.
        if self.rsa_key:
            rsa_key = paramiko.RSAKey.from_private_key(StringIO(self.rsa_key))
        else:
            rsa_key = None

        # Sets the parameters to use.
        path = self.path
        port = 22  # Default port for SFTP.
        retries = self.retries
        if path is None:
            raise UserError("Missing parameter 'path'")
        if ':' in path:
            t = path.split(':')
            path = t[0]
            port = int(t[1])

        while self.connection is None:
            try:
                # Opens the connection.
                ssh = SSHClient()
                ssh.logger = _logger
                ssh.set_missing_host_key_policy(WarningPolicy())
                ssh.connect(
                    path, port=port,
                    username=self.username,
                    password=self.password,
                    pkey=rsa_key)
                sftp = ssh.open_sftp()
                self.transport = ssh
                self.connection = sftp
            except:
                if retries <= 0:
                    raise
                else:
                    retries -= 1
                    time.sleep(1)

    def close(self):
        # self.connection.close()
        self.transport.close()
        self.connection = None
        self.transport = None

    def __enter__(self):
        self.open()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
