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

from abc import ABCMeta, abstractmethod


class connection(object):
    ''' Implements an abstract class which is the base for concrete connection objects, e.g. SFTP.
    '''
    __metaclass__ = ABCMeta

    @abstractmethod
    def chdir(self, path):
        ''' Changes the working folder to the indicated one.
        '''
        pass

    @abstractmethod
    def open(self):
        ''' Opens a connection.
        '''
        pass

    @abstractmethod
    def close(self):
        ''' Closes a connection.
        '''
        pass

    @abstractmethod
    def list(self, directory):
        ''' Lists the contents of a directory.
        '''
        pass

    @abstractmethod
    def put(self, local_file_path, remote_file_path):
        ''' Puts/writes a file from local to remote.
        '''
        pass

    @abstractmethod
    def get(self, remote_file_path, local_file_path):
        ''' Gets/reads a file from remote to local.
        '''
        pass

    @abstractmethod
    def remove(self, remote_file_path):
        ''' Deletes a file from the remote server.
        '''
        pass

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
