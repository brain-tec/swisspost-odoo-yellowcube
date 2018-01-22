# b-*- encoding: utf-8 -*-
##############################################################################
#
#    Copyright (c) 2016 brain-tec AG (http://www.braintec-group.com)
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

import os
from tempfile import mkstemp
from openerp.addons.pc_connect_master.utilities.others import format_exception


class FileManager:
    ''' Allows to easily handle temporal files created using mkstemp.
        The resources used will be freed-up when a call to clear() is done.
    '''
    def __init__(self, directory):
        self.directory = directory
        self.paths = []  # List of paths created.
        self.fds = []  # List of file descriptors opened.

    def create_new_file(self, suffix=None, prefix=None):
        ''' Creates a temporal file, and returns its full path.
        '''

        fd = None
        attachment_local_full_path = None

        suffix_to_use = suffix or '.pdf'
        prefix_to_use = prefix or 'ir_attachment'

        try:
            fd, attachment_local_full_path = mkstemp(suffix=suffix_to_use, prefix=prefix_to_use, dir=self.directory)
            self.fds.append(fd)
            self.paths.append(attachment_local_full_path)

        except Exception as e:
            if fd:
                os.close()
            if attachment_local_full_path:
                os.remove(attachment_local_full_path)
            raise Exception(_('There was an error when creating the temporal file on {0}. Error: {1}').format(self.directory, format_exception(e)))

        return attachment_local_full_path

    def clear(self):
        ''' Removes the temporal data created (files and file descriptors).
        '''
        for fd in self.fds:
            os.close(fd)  # Closes the file descriptors opened.
        for full_path in self.paths:
            os.remove(full_path)  # Removes temporal files created.

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
