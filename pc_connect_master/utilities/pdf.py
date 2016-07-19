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
import shutil
import subprocess
import os
import base64
from openerp.report import render_report
import logging
logger = logging.getLogger(__name__)


def get_pdf_from_report(cr, uid, service_name, dictionary, context=None):
    '''
    Returns a PDF encoded in base64. This is deprecated, and is provided only
    for backwards compatibility: use instead openerp.report.render_report()

    @param service_name: The name of the service that generates the PDF.
    @type service_name: string, e.g. 'report.invoice'.
    @param dictionary: Dictionary containing keys 'ids' and 'model'.
    @type dictionary: dict.
    @rtype: base64. PDF file encoded in base64.
    '''
    logger.warning('get_pdf_from_report() is deprecated. Port your code to use render_report().')

    ids_list = dictionary['ids']
    if not isinstance(dictionary['ids'], list):
        ids_list = [dictionary['ids']]

    pdf_data, _ = render_report(cr, uid, ids_list,
                                service_name, {'model': dictionary['model']}, context=context)
    return base64.b64encode(pdf_data)


def associate_ir_attachment_with_object(delegate, cr, uid, encoded_data, file_name, res_model, res_id):
    '''
    Returns the ID of the generated attachment.
    @param encoded_data: Data of the file to attach, encoded in base64.
    @type encoded_data: base64.
    @param file_name: Name of the file to generate.
    @type file_name: string.
    @param res_model: String of the model to which the attachment will be attached.
    @type res_model: string.
    @param res_id: ID of the object of res_model to which we want to attach the information.
    @type res_id: integer.
    @rtype: Int. ID of the generated attachment.
    '''
    ir_attachment_obj = delegate.pool.get('ir.attachment')
    result = ir_attachment_obj.create(cr, uid, {'name': file_name,
                                                'datas': encoded_data,
                                                'datas_fname': file_name,
                                                'res_model': res_model,
                                                'res_id': res_id,
                                                'type': 'binary'})
    return result


def concatenate_pdfs(summary_file_name, file_list_to_merge):
    ''' Receives a list of PDF files to merge, and creates a summary PDF file containing the
        concatenation of the PDFs. The concatenation is done using a system's command.
        It is the responsibility of the caller to ASSURE that the summary file is unique.
        The files that doesn't exist are not concatenated, and an line on the logger is written.
        The files that could be concatenated are returned as a list.
    '''

    files_concatenated = []

    for file_to_merge in file_list_to_merge:
        if os.path.exists(file_to_merge):
            files_concatenated.append(file_to_merge)
        else:
            logger.error('File {0} does not exist and could not be concatenated.'.format(file_to_merge))

    if len(files_concatenated) == 0:
        logger.error('No files were found, so file {0} could not be generated.'.format(summary_file_name))

    elif len(files_concatenated) == 1:
        the_only_file = file_list_to_merge[0]
        if os.path.exists(the_only_file):
            shutil.copy2(the_only_file, summary_file_name)
        else:
            logger.error('The only file {0} does not exist, so file {1} could not be generated.'.format(the_only_file, summary_file_name))

    else:
        # Before we used 'gs', but a problem with strange characters ghostcript could not deal
        # with forced us to consider another tool.
        # gs_arguments = ['gs', '-dBATCH', '-dNOPAUSE', '-q', '-sDEVICE=pdfwrite']
        # execution_arguments = gs_arguments[:]
        # execution_arguments.extend(['-sOutputFile=' + summary_file_name])
        # execution_arguments.extend(file_list_to_merge)

        execution_arguments = ['pdfunite']
        execution_arguments.extend(files_concatenated)
        execution_arguments.append(summary_file_name)

        # Call blocks until it finishes.
        subprocess.call(execution_arguments)

    return files_concatenated


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
