# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>).
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

import unicodedata
import base64
import netsvc
from openerp.osv import osv, fields

'''
File with useful methods.

In order to get access to these methods, you need to import this file. You can do it as follows:

from bt_helper.tools import bt_misc
'''


def bt_unaccent(text):
    '''Returns the specified string with all the accents removed.

    @param text: string with accents
    @type text: unicode'''

    if not text:
        return ''

    nkfd_form = unicodedata.normalize('NFKD', unicode(text))
    result = u''.join([c for c in nkfd_form if not unicodedata.combining(c)])

    return result


def set_o2m_triplets_to_remove(o2m_triplets):
    '''Marks the specified o2m triplets as "deleted".

    This method is very useful when the onchange method of a field needs to remove all the records
    of a o2m field (for example, before re-populating the o2m field with new records). Note that
    re-populating a o2m field with new records via an onchange method involves always EXPLICITLY
    removing the previous records, otherwise, the old records will "reappear" once the main object
    is saved.

    @param o2m_triplets: list of o2m triplets (e.g., [[0, False, {'name': 'Record name'}], ...])
    @type o2m_triplets: list'''

    triplets = []

    for triplet in o2m_triplets:
        if triplet[0] == 4:
            # Triplet already stored; it must be marked as "to delete"
            triplets.append((2, triplet[1], False))
        elif triplet[0] == 2:
            # Triplet manually removed; it must remain removed
            triplets.append(tuple(triplet))

    return triplets


def get_label_from_selection(selection_list, selection_key):
    '''Given a list used to populate a selection field, returns the label associated with the
    specified key.

    @param selection_list: a list used to populate a selection field (e.g.,
                           [('draft', _('Draft'), ('done', 'Done'))])
    @type selection_list: list

    @param selection_key: one of the keys in the selection list (e.g., 'draft')
    @type selection_key: any'''

    for (key, value) in selection_list:
        if key == selection_key:
            return value

    return ''


def get_pdf_from_report(cr, uid, service_name, dictionary, context=None):
    '''
    Returns a PDF encoded in base64.

    @param service_name: The name of the service that generates the PDF.
    @type service_name: string.

    @param dictionary: Dictionary containing keys 'ids' and 'model'.
    @type dictionary: dict.

    @rtype: base64. PDF file encoded in base64.
    '''

    service = netsvc.LocalService(service_name)

    ids_list = dictionary['ids']
    if type(dictionary['ids']) is not list:
        ids_list = [dictionary['ids']]

    (result, _) = service.create(cr, uid, ids_list, dictionary, context=context)
    return base64.b64encode(result)


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
