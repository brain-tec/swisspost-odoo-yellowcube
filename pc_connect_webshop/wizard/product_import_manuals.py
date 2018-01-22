# b-*- encoding: utf-8 -*-
##############################################################################
#
#    Copyright (c) 2014 brain-tec AG (http://www.braintec-group.com)
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
from osv import osv, fields
from openerp.tools.translate import _


def product_import_manuals(pool, cr, uid, csv, context=None):
    if context is None:
        context = {}

    # Checks that all the expected fields are there.
    expected_fields = set(('default_code', 'manual_description', 'manual_lang', 'manual_url'))
    actual_fields = csv.fieldnames
    if not expected_fields.issubset(actual_fields):
        return (False, 'Missing fields. Required fields are: {0}.'.format(','.join(list(expected_fields))))

    # Parses the lines of the CSV file.
    current_default_code = ''
    num_row = 0
    errors = []
    for row in csv:
        num_row += 1
        default_code = row['default_code']
        manual_description = row['manual_description']
        manual_lang = row['manual_lang']
        manual_url = row['manual_url']

        # Updates the current default code being used.
        if default_code != '':
            current_default_code = default_code
        if (default_code == '') and (current_default_code == ''):
            errors.append('{0}: Bad formed CSV: default_code must be the parent of subsequent rows.'.format(num_row))
            continue

        # Checks if the indicated language exists in the system.
        # If not, indicates an error. If it exists, gets the code and the language ID.
        language_code_id = pool.get('res.lang').search(cr, uid, [('code', '=', manual_lang)], context=context)
        if not language_code_id:
            errors.append('{0}: The language code {1} was not found in the supported languages for the system.'.format(num_row, manual_lang))
            continue

        # Gets the product to attach the manuals to.
        # If the product does not exists, indicates an error.
        product_obj = pool.get('product.product')
        product_ids = product_obj.search(cr, uid, [('default_code', '=', current_default_code)], context=context)
        product = product_obj.browse(cr, uid, product_ids[0], context=context)
        if not product:
            errors.append('{0}: The product with code={1} does not exist. It must be created first.'.format(num_row, current_default_code))
            continue

        # Creates the attachment for the manual.
        attachment_id = pool.get('ir.attachment').create(cr, uid, {'url': manual_url,
                                                                   'type': 'url',
                                                                   'name': '{0}-{1}'.format(manual_description, manual_lang),
                                                                   }, context=context)
        if not attachment_id:
            errors.append('{0}: The creation of the attachment in this row was not possible.'.format(num_row))
            continue

        # Creates the relation in product_manual.
        _id = pool.get('product.manual').create(cr, uid, {'product_id': product.id,
                                                          'description': manual_description,
                                                          'language_id': language_code_id[0],
                                                          'attachment_id': attachment_id,
                                                          }, context=context)
        if not _id:
            errors.append('{0}: The creation of the record in this row was not possible.'.format(num_row))
            continue

    if errors:
        return (False, '\n'.join(errors))
    else:
        return (True, 'All imports were imported correctly.')


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: