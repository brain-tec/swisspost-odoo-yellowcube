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

import hashlib
import shutil
from subprocess import Popen, PIPE
import os
import logging

logger = logging.getLogger(__name__)


def get_hash(file_path):
    """ Returns the SHA-1 hash for a file path.
    """
    sha1_hexdigest = False

    f = open(file_path, 'rb')
    try:
        sha1 = hashlib.sha1()
        sha1.update(f.read())
        sha1_hexdigest = sha1.hexdigest()
    except Exception:
        raise
    finally:
        f.close()

    return sha1_hexdigest


def concatenate_pdfs(summary_file_name, file_list_to_merge):
    """ Receives a list of PDF files' paths to merge, and creates a summary
        PDF file containing the concatenation of the PDFs.
        The concatenation is done using a system's command.

        It is the responsibility of the caller to ASSURE that the
        summary file is unique.

        The files that doesn't exist are not concatenated, and an line
        on the logger is written. The files that could be concatenated
        are returned as a list.
    """

    files_concatenated = []

    for file_to_merge in file_list_to_merge:
        if os.path.exists(file_to_merge):
            files_concatenated.append(file_to_merge)
        else:
            logger.error('File {0} does not exist and '
                         'could not be concatenated.'.format(file_to_merge))

    if len(files_concatenated) == 0:
        logger.error('No files were found, so file {0} '
                     'could not be generated.'.format(summary_file_name))

    elif len(files_concatenated) == 1:
        the_only_file = file_list_to_merge[0]
        if os.path.exists(the_only_file):
            shutil.copy2(the_only_file, summary_file_name)
        else:
            logger.error('The only file {0} does not exist, '
                         'so file {1} could not be generated.'.format(
                the_only_file, summary_file_name))

    else:
        # Before we used 'gs', but a problem with strange characters
        # ghostcript could not deal with forced us to consider another tool.
        # gs_arguments = ['gs','-dBATCH','-dNOPAUSE','-q','-sDEVICE=pdfwrite']
        # execution_arguments = gs_arguments[:]
        # execution_arguments.extend(['-sOutputFile=' + summary_file_name])
        # execution_arguments.extend(file_list_to_merge)

        execution_arguments = ['pdfunite']
        execution_arguments.extend(files_concatenated)
        execution_arguments.append(summary_file_name)

        # Call blocks until it finishes.
        proc = Popen(execution_arguments, stderr=PIPE)
        proc.wait()

        # We check if the command output any error that we have
        # to take care about.
        out, err = proc.communicate()
        if err:
            for file_to_merge in files_concatenated:
                logger.error('File {0} could not be concatenated because '
                             'there was an error while generating the '
                             'concatenated file.'.format(file_to_merge))
            files_concatenated = []

        if proc.poll():
            try:
                # We safe this code within a try since between the poll()
                # and the termination() it may have been already terminated.
                proc.terminate()
            except:
                logger.warning('The call to TERMINATE the process which '
                               'concatenates the PDFs failed.')
        if proc.poll():
            try:
                # We safe this code within a try since between the poll()
                # and the kill() it may have been already terminated.
                proc.kill()
            except:
                logger.warning('The call to KILL the process which '
                               'concatenates the PDFs failed.')

        # We make sure we closed the pipes opened (not needed according
        # to the documentation, but just in case)
        if proc:
            try:
                proc.stderr.close()
            except:
                logger.warning('The call to close the standard error '
                               'obtained when concatenating PDFs failed.')

    return files_concatenated

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
