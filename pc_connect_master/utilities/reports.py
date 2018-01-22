# b-*- encoding: utf-8 -*-
##############################################################################
#
#    Copyright (c) 2017 brain-tec AG (http://www.braintec-group.com)
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

import base64
import netsvc


def delete_report_from_db(report_names):
    """ Deletes a report from the database.

        Receives a list with the names of the reports to delete.

        Copied from bt_helper of repository BT-Developer by brain-tec AG.
    """
    if type(report_names) is not list:
        report_names = [report_names]
    for name in report_names:
        if 'report.' + name in netsvc.Service._services:
            del netsvc.Service._services['report.' + name]


def get_pdf_from_report(cr, uid, service_name, dictionary,
                        context=None):
    """
    Returns a PDF encoded in base64.

    @param service_name: The name of the service that generates the PDF.
    @type service_name: string.

    @param dictionary: Dictionary containing keys 'ids' and 'model'.
    @type dictionary: dict.

    @rtype: base64. PDF file encoded in base64.

    Copied from bt_helper of repository BT-Developer by brain-tec AG.
    """

    service = netsvc.LocalService(service_name)

    ids_list = dictionary['ids']
    if type(dictionary['ids']) is not list:
        ids_list = [dictionary['ids']]

    (result, _) = service.create(cr, uid, ids_list, dictionary,
                                 context=context)
    return base64.b64encode(result)


def associate_ir_attachment_with_object(delegate, cr, uid,
                                        encoded_data, file_name,
                                        res_model, res_id):
    """
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

    Copied from bt_helper of repository BT-Developer by brain-tec AG.
    """

    ir_attachment_obj = delegate.pool.get('ir.attachment')
    result = ir_attachment_obj.create(cr, uid, {'name': file_name,
                                                'datas': encoded_data,
                                                'datas_fname': file_name,
                                                'res_model': res_model,
                                                'res_id': res_id,
                                                'type': 'binary'})
    return result


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
