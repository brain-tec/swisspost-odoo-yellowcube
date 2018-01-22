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


def product_import_media(pool, cr, uid, csv, context):
    for x in ['default_code', 'url', 'sort_order', 'name']:
        if x not in csv.fieldnames:
            return (False, 'Invalid header. Missing {0}'.format(x))
    pictures_created = 0
    pictures_modified = 0
    products_updated = []
    product_obj = pool.get('product.product')
    image_obj = pool.get('product.images')
    for row in csv:
        product_id = product_obj.search(cr, uid, [('default_code', '=', row['default_code'])], context=context)[0]
        if product_id not in products_updated:
            products_updated.append(product_id)
        image_id = image_obj.search(cr, uid, [('product_id', '=', product_id), ('sort_order', '=', row['sort_order'])], context=context)
        if image_id:
            pictures_modified += 1
            image_obj.write(cr, uid, image_id, {'name': row['name'], 'url': row['url'], 'link': True}, context=context)
        else:
            pictures_created += 1
            image_obj.create(cr,
                              uid,
                              {'name': row['name'],
                               'url': row['url'],
                               'product_id': product_id,
                               'sort_order': row['sort_order'],
                               'link': True},
                              context=context)

    products_updated = [x['default_code'] for x in product_obj.read(cr, uid, products_updated, ['default_code'], context=context)]
    return (True, 'Media files imported\nPictures created: {0}\nPictures modified: {1}\nUpdated products:\n{2}'.format(pictures_created, pictures_modified, '\n'.join(products_updated)))


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: