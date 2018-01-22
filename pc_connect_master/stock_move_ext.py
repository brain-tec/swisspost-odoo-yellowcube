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

from utilities import filters
from openerp.osv import fields, osv


class stock_move_ext(osv.Model):
    _inherit = 'stock.move'

    # BEGIN OF THE CODE WHICH DEFINES THE NEW FILTERS TO ADD TO THE OBJECT.
    def _replace_delivery_to_customer_placeholders(self, cr, uid, args, context=None):
        return filters._replace_delivery_to_customer_placeholders(self, cr, uid, args, context=context)

    def search(self, cr, uid, args, offset=0, limit=None, order=None, context=None, count=False):
        return filters.search(self, cr, uid, args, stock_move_ext, offset=offset, limit=limit, order=order, context=context, count=count)

    def read_group(self, cr, uid, domain, fields, groupby, offset=0, limit=None, context=None, orderby=False):
        return filters.read_group(self, cr, uid, domain, fields, groupby, stock_move_ext, offset=offset, limit=limit, context=context, orderby=orderby)
    # END OF THE CODE WHICH DEFINES THE NEW FILTERS TO ADD TO THE OBJECT.

    def create(self, cr, uid, vals, context=None):
        move_id = super(stock_move_ext, self).create(
            cr, uid, vals, context=context)

        if 'product_id' in vals:
            self.set_mandatory_additional_shipping_codes(
                cr, uid, move_id, context=context)

        return move_id

    def write(self, cr, uid, ids, vals, context=None):
        ret = super(stock_move_ext, self).write(
            cr, uid, ids, vals, context=context)

        if 'product_id' in vals:
            self.set_mandatory_additional_shipping_codes(
                cr, uid, ids, context=context)

        return ret

    def set_mandatory_additional_shipping_codes(self, cr, uid, ids,
                                                context=None):
        """ Modifies the mandatory additional shipping codes on the picking
            depending on the stock.move. The part which updates the services
            depending on the carrier of the picking is in the model
            stock.picking.
        """
        if not isinstance(ids, list):
            ids = [ids]
        if context is None:
            context = {}

        picking_obj = self.pool.get('stock.picking')
        sep = ';'

        for move in self.browse(cr, uid, ids, context=context):
            picking = move.picking_id

            mandatory_additional_options = set()

            # Stores the already existing mandatory additional services,
            # just in case the user had modified them manually.
            if picking.yc_mandatory_additional_shipping:
                original_mandatory_options = set(
                    picking.yc_mandatory_additional_shipping.split(sep))
                mandatory_additional_options.update(original_mandatory_options)
            else:
                original_mandatory_options = set()

            # Adds the mandatory additional services by the product's template
            # and the product's category.
            prod_templ = move.product_id.product_tmpl_id
            for addit_op in prod_templ.yc_mandatory_additional_option_ids:
                mandatory_additional_options.add(addit_op.code)
            for addit_op in prod_templ.categ_id.yc_mandatory_additional_option_ids:
                mandatory_additional_options.add(addit_op.code)

            # We update the list of mandatory additional shipping options
            # but only if it changed.
            if mandatory_additional_options and \
                    original_mandatory_options != mandatory_additional_options:
                picking_obj.write(cr, uid, picking.id, {
                    'yc_mandatory_additional_shipping': sep.join(
                        mandatory_additional_options),
                }, context=context)

        return True

    def _get_partner_title(self, cr, uid, ids, field_name, args, context=None):
        if context is None:
            context = {}
        res = {}
        for stock_move in self.browse(cr, uid, ids, context=context):
            res[stock_move.id] = stock_move.partner_id.title.name
        return res

    def _get_partner_state(self, cr, uid, ids, field_name, args, context=None):
        if context is None:
            context = {}
        res = {}
        for stock_move in self.browse(cr, uid, ids, context=context):
            res[stock_move.id] = stock_move.partner_id.state_id.name
        return res

    def _get_partner_country(self, cr, uid, ids, field_name, args, context=None):
        if context is None:
            context = {}
        res = {}
        for stock_move in self.browse(cr, uid, ids, context=context):
            res[stock_move.id] = stock_move.partner_id.country_id.name
        return res

    _columns = {
        'product_id_name': fields.related('product_id', 'name', type='char', readonly=True, size=64,
                                          relation='stock.move.product_id',
                                          string='Name of the Product', store=True),
        'prodlot_id_name': fields.related('prodlot_id', 'name', type='char', readonly=True, size=64,
                                          relation='stock.move.prodlot_id', string='Serial number',
                                          store=True),
        'picking_id_name': fields.related('picking_id', 'name', type='char', readonly=True, size=64,
                                          relation='stock.move.prodlot_id', string='Reference'),
        'location_id_name': fields.related('location_id', 'name', type='char', readonly=True,
                                           size=64, relation='stock.move.location_id',
                                           string='Source Location'),
        'location_dest_id_name': fields.related('location_dest_id', 'name', type='char',
                                                readonly=True, size=64,
                                                relation='stock.move.location_dest_id',
                                                string='Destination Location'),
        'partner_title': fields.function(_get_partner_title, type='text',
                                         string='Partner title', help='Title of the customer'),
        'partner_firstname': fields.related('partner_id', 'firstname', type='text', readonly=True,
                                            size=30, relation='stock.move.partner_id',
                                            string="Partner Firstname"),
        'partner_lastname': fields.related('partner_id', 'lastname', type='text', readonly=True,
                                           size=30, relation='stock.move.partner_id',
                                           string="Partner Lastname"),
        'partner_name': fields.related('partner_id', 'name', type='text', readonly=True,
                                       size=30, relation='stock.move.partner_id',
                                       string="Partner Name"),
        'partner_company': fields.related('partner_id', 'company', type='text', readonly=True,
                                          size=30, relation='stock.move.partner_id',
                                          string="Partner Company"),
        'partner_street': fields.related('partner_id', 'street', type='text', readonly=True,
                                         size=30, relation='stock.move.partner_id',
                                         string="Partner Street"),
        'partner_street_no': fields.related('partner_id', 'street_no', type='text', readonly=True,
                                            size=30, relation='stock.move.partner_id',
                                            string="Partner Street Number"),
        'partner_street2': fields.related('partner_id', 'street2', type='text', readonly=True,
                                          size=30, relation='stock.move.partner_id',
                                          string="Partner Street2"),
        'partner_po_box': fields.related('partner_id', 'po_box', type='text', readonly=True,
                                         size=30, relation='stock.move.partner_id',
                                         string="Partner P.O. Box"),
        'partner_zip': fields.related('partner_id', 'zip', type='text', readonly=True,
                                      size=30, relation='stock.move.partner_id',
                                      string="Partner Zip"),
        'partner_city': fields.related('partner_id', 'city', type='text', readonly=True,
                                       size=30, relation='stock.move.partner_id',
                                       string="Partner City"),
        'partner_state': fields.function(_get_partner_state, type='text',
                                         string="Partner State", help='State of the partner'),
        'partner_country': fields.function(_get_partner_country, type='text',
                                           string="Partner Country", help='Country of the partner'),
        'partner_phone': fields.related('partner_id', 'phone', type='text', readonly=True,
                                        size=30, relation='stock.move.partner_id',
                                        string="Partner Phone"),
        'partner_mobile': fields.related('partner_id', 'mobile', type='text', readonly=True,
                                         size=30, relation='stock.move.partner_id',
                                         string="Partner Mobile"),
        'partner_email': fields.related('partner_id', 'name', type='text', readonly=True,
                                        size=30, relation='stock.move.partner_id',
                                        string="Partner Email"),
    }
