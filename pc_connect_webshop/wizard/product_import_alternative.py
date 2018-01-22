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


def product_import_alternative(pool, cr, uid, csv, context):
    if context is None:
        context = {}

    # Checks that all the expected fields are there.
    expected_fields = set(('default_code', 'other_default_code'))
    actual_fields = csv.fieldnames
    if not expected_fields.issubset(actual_fields):
        return (False, 'Missing fields. Required fields are: {0}.'.format(','.join(list(expected_fields))))

    product_obj = pool.get('product.product')

    # Stores any errors present.
    errors = []

    # Parses the lines of the CSV file.
    current_default_code = ''
    num_row = 1
    for row in csv:
        num_row += 1
        # Caches the values of the columns of this row.
        default_code = row['default_code']
        other_default_code = row['other_default_code']

        # Updates the current default code being used.
        if default_code != '':
            current_default_code = default_code
            product_id = product_obj.search(cr, uid, [('default_code', '=', current_default_code)], context=context)
            if not product_id:
                errors.append('{0}: The product with code={1} does not exist. It must be created first.'.format(num_row, current_default_code))
                continue  # Proceed with the following record, if any.
                # return (False, 'The product with code={0} does not exist. It must be created first.'.format(current_default_code))
            else:
                product_id = product_id[0]
        if (default_code == '') and (current_default_code == ''):
            errors.append('{0}: Bad formed CSV: default_code must be the parent of subsequent rows.'.format(num_row))
            continue

        # Gets the products to relate to.
        other_product_id = product_obj.search(cr, uid, [('default_code', '=', other_default_code)], context=context)
        if not other_product_id:
            errors.append('{0}: The product with code={1} does not exist. It must be created first.'.format(num_row, other_default_code))
            continue  # Proceed with the following record, if any.
            # return (False, 'The product with code={0} does not exist. It must be created first.'.format(other_default_code))
        else:
            other_product_id = other_product_id[0]

        # Creates the relation.
        _id = pool.get('product.alternative').create(cr, uid, {'product_id': product_id,
                                                               'product_alternative_id': other_product_id,
                                                               }, context=context)
        if not _id:
            errors.append('{0}: The creation of the record in this row was not possible.'.format(num_row))
            continue  # Proceed with the following record, if any.
            # return (False, 'The creation of the record in row number {0} was not possible.'.format(num_row))

    if errors:
        errors = ['Some errors ocurred in the import, thus no record was imported.'] + errors
        return (False, '\n\t'.join(errors))
    else:
        return (True, 'All imports were imported correctly.')

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
