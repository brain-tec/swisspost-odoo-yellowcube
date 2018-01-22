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
###############################################################################

from osv import osv, fields, orm
from openerp.addons.pc_generics import generics
from tools.translate import _


@generics.has_mako_header()
class stock_picking_out_ext(osv.osv):
    _inherit = 'stock.picking.out'

    def generate_barcodes(self, cr, uid, ids, tracking_ids=None, context=None):
        ''' Computes & stores on the database the barcode images associated to
            this stock.picking.out, in order to place it in the mako report.

            Optionally allows to set a tracking_ids, so one label is computed
            per each tracking ID provided on the list.

            This method must be called over just one ID on ids; if a list of IDs
            is provided it just gets the first element.
        '''
        if context is None:
            context = {}
        if type(ids) is not list:
            ids = [ids]

        stock_picking_obj = self.pool.get('stock.picking')
        barcode_storage_obj = self.pool.get('barcode.storage')

        picking = stock_picking_obj.browse(cr, uid, ids[0], context=context)

        context['default_type'] = 'out'
        context['contact_display'] = 'partner_address'

        # This is called only if it was not called already over any of the trackings of the same picking.
        barcodes_stored = barcode_storage_obj.search(cr, uid, [('picking_id', '=', picking.id),
                                                               ('tracking_id', 'in', tracking_ids or [False]),
                                                               ], context=context, limit=1, count=True)

        if not barcodes_stored:
            labels = picking.generate_shipping_labels(tracking_ids=tracking_ids)
            for label in labels:
                data = label['file'].encode('base64')
                tracking_id = label['tracking_id']

                barcode_storage_obj.create(cr, uid, {'picking_id': picking.id,
                                                     'tracking_id': tracking_id,
                                                     'barcode_base64': data,
                                                     }, context=context)

        return True

    def get_barcode(self, cr, uid, ids, tracking_id=None, context=None):
        ''' Returns the already-computed  stored barcode label for a given
            tracking number, or for the picking if no tracking number is provided.

            If no barcode label is found, then it raises an exception.

            This method must be called over just one ID on ids; if a list of IDs
            is provided it just gets the first element.
        '''
        if context is None:
            context = {}
        if type(ids) is not list:
            ids = [ids]

        barcode_storage_obj = self.pool.get('barcode.storage')

        picking_id = ids[0]

        barcode_stored_ids = barcode_storage_obj.search(cr, uid, [('picking_id', '=', picking_id),
                                                                  ('tracking_id', '=', tracking_id),
                                                                  ], context=context, limit=1)
        if not barcode_stored_ids:
            raise orm.except_orm(_('No Barcode Label Found'),
                                 _('No barcode label was found for picking ID={0} and tracking ID={1}').format(picking_id, tracking_id))
        else:
            barcode_stored = barcode_storage_obj.browse(cr, uid, barcode_stored_ids[0], context=context)
            data = barcode_stored.barcode_base64
            return data

    def get_file_name_barcode(self, cr, uid, ids, context=None):
        ''' Returns the name of the filename for the barcode's report.
        '''
        return self.pool.get('stock.picking').get_file_name_barcode(cr, uid, ids, context=context)

    def get_different_packages(self, cr, uid, ids, context=None):
        ''' Returns a list with the different package's IDs contained on the moves of the picking.

            IDs must contain just one element, otherwise just the first element of the list is taken.
        '''
        return self.pool.get('stock.picking').get_different_packages(cr, uid, ids, context=context)
