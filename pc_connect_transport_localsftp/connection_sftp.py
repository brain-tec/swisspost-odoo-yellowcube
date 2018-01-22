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

from StringIO import StringIO
import paramiko
import stat
import time
from openerp.tools.translate import _
import logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)



def _log_call(f):
    def new_f(self, *args, **kargs):
        logger.debug('{0}({1}, {2})'.format(f, args, kargs))
        try:
            return f(self, *args, **kargs)
        except:
            logger.error('{0}({1}, {2})'.format(f, args, kargs))
            raise
    return new_f


class connection_sftp(object):
    ''' Implements a connection object which uses SFTP as connection.
    '''

    @_log_call
    def __init__(self, url, username, password, rsa_key):
        self._server_url = url
        self._username = username
        self._password = password
        self._rsa_key = rsa_key
        self._connection = None
        self._transport = None

    @_log_call
    def open(self, retries=3):
        ''' Opens an SFTP connection.
        '''
        # Gets the key.
        rsa_key = self._rsa_key and paramiko.RSAKey.from_private_key(StringIO(self._rsa_key)) or None

        # Sets the parameters to use.
        path = self._server_url
        port = 22  # Default port for SFTP.
        if ':' in path:
            t = path.split(':')
            path = t[0]
            port = int(t[1])

        while self._connection is None:
            try:
                # Opens the connection.
                transport = paramiko.Transport((path, port))
                self._transport = transport
                transport.connect(username=self._username, password=self._password, pkey=rsa_key)
                ssh = paramiko.SFTPClient.from_transport(transport)
                self._connection = ssh
            except Exception as e:
                if retries <= 0:
                    raise
                else:
                    retries -= 1
                    time.sleep(1)
        # ssh.set_missing_host_key_policy(paramiko.WarningPolicy())
        # ssh.connect(path, port=port, username=self._username, password=self._password, pkey=rsa_key)
        # self._connection = ssh.open_sftp()

    @_log_call
    def close(self):
        ''' Closes the connection and its associated transport.
        '''
        if self._connection:
            self._connection.close()
            self._connection = None
        if self._transport:
            self._transport.close()
            self._transport = None

    @_log_call
    def list(self, directory):
        ''' Lists the files of a directory.
        '''
        if self._connection:
            result = []
            for filelist in self._connection.listdir_attr(directory):
                if stat.S_IFREG & filelist.st_mode:
                    result.append(filelist.filename)
            return result
        else:
            raise Exception(_("A 'directory list' operation was attempted over a non-existing connection."))

    @_log_call
    def chdir(self, directory):
        ''' Changes the directory.
        '''
        if self._connection:
            return self._connection.chdir(directory)
        else:
            raise Exception(_("A 'chdir' operation was attempted over a non-existing connection."))

    @_log_call
    def put(self, local_file_path, remote_file_path):
        ''' Puts/writes a file from local to remote.
        '''
        if self._connection:
            paths = remote_file_path.split('/')
            for p in paths[:-1]:
                self.chdir(p)
            self._connection.put(local_file_path, paths[-1])
            for p in paths[:-1]:
                if p != '.':  # To avoid moving above the top folder.
                    self.chdir('..')
        else:
            raise Exception(_("A 'put' operation was attempted over a non-existing connection."))

    @_log_call
    def get(self, remote_file_path, local_file_path):
        ''' Gets/reads a file from remote to local.
        '''
        if self._connection:
            paths = remote_file_path.split('/')
            for p in paths[:-1]:
                self.chdir(p)
            self._connection.get(paths[-1], local_file_path)
            for p in paths[:-1]:
                if p != '.':  # To avoid moving above the top folder.
                    self.chdir('..')
        else:
            raise Exception(_("A 'get' operation was attempted over a non-existing connection."))

    @_log_call
    def remove(self, remote_file_path):
        ''' Deletes a file from the remote server.
        '''
        if self._connection:
            paths = remote_file_path.split('/')
            for p in paths[:-1]:
                self.chdir(p)
            self._connection.remove(paths[-1])
            for p in paths[:-1]:
                if p != '.':  # To avoid moving above the top folder.
                    self.chdir('..')
        else:
            raise Exception(_("A 'remove' operation was attempted over a non-existing connection."))

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
