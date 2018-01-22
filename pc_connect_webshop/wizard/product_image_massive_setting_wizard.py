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

from osv import osv, fields
from openerp.tools.translate import _
from openerp.addons.pc_connect_master.utilities.others import format_exception


class product_image_massive_setting_wizard(osv.TransientModel):
    _name = 'product.image_massive_setting_wizard'

    def do_massive_image_setting(self, cr, uid, ids, context=None):
        """ For those products selected, we massively set its image, taken from the
            list of images that are stored on it. We take always the image with
            the lowest sequence number.
        """
        if context is None:
            context = {}

        product_product_obj = self.pool.get('product.product')
        product_images_obj = self.pool.get('product.images')

        wizard = self.browse(cr, uid, ids[0], context=context)

        # Keeps track of the IDs for the products having an image which could not be set.
        error_images = []
        images_not_found = []

        # Copies the images.
        product_ids = context.get('active_ids', [])
        for product in product_product_obj.browse(cr, uid, product_ids, context=context):
            image_ids = product_images_obj.search(cr, uid, [('product_id', '=', product.id)], limit=1, order='sort_order', context=context)
            if image_ids:
                image_base64 = product_images_obj.get_image(cr, uid, image_ids[0], context=context)
                try:
                    cr.execute("SAVEPOINT image_base64_writing;")
                    product.write({'image': image_base64})
                    cr.execute("RELEASE SAVEPOINT image_base64_writing;")
                except Exception as e:
                    error_images.append('<li><strong>{0}</strong> (Reference={1}, ID={2}): {3}...</li>'.format(product.name, product.default_code, product.id, format_exception(e)[:100]))
                    cr.execute("ROLLBACK TO SAVEPOINT image_base64_writing;")
            else:
                images_not_found.append('<li><strong>{0}</strong> (Reference={1}, ID={2})</li>'.format(product.name, product.default_code, product.id))

        # Provides some feedback to the user.
        message = ''
        if images_not_found:
            message += _('<strong>The images for the following products could not be found:</strong> <ul>{0}</ul> </br>').format('\n'.join(images_not_found))
        if error_images:
            message += _('<strong>The images for the following products could not be set because of an error:</strong> <ul>{0}</ul> </br>').format('\n'.join(error_images))
        if not error_images and not images_not_found:
            message = _('<strong>The images were set for all the products selected.</strong>\n').format(len(product_ids))

        wizard.write({'message': message,
                      'state': 'done',
                      })

        return {
            'name': 'Result',
            'context': context,
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'product.image_massive_setting_wizard',
            'res_id': ids[0],
            'type': 'ir.actions.act_window',
            'target': 'new',
        }

    _columns = {
        'state': fields.selection([('draft', 'draft'),
                                   ('done', 'done'),
                                   ]),
        'message': fields.text("Message", readonly=True)
    }

    _defaults = {
        'state': 'draft',
        'message': _('The images for the selected products will be automatically set.'),
    }

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
