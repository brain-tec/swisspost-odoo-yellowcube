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

from openerp.osv import osv, fields
from openerp.tools.translate import _
from openerp.tools import DEFAULT_SERVER_DATETIME_FORMAT
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT, DEFAULT_SERVER_TIME_FORMAT
from datetime import datetime
import time
import pytz

class stock_connect_file_ext(osv.Model):
    _inherit = 'stock.connect.file'

    _columns = {
        'picking_ids': fields.one2many('stock.picking', 'connect_file_id', 'Related stock pickings'),
    }

    def get_company_lang(self, cr, uid, ids, context=None):
        ''' This is to be called from the email.template.
            Gets the company's language.
        '''
        if context is None:
            context = {}

        language_id = self.pool.get('res.users').browse(cr, uid, uid, context=context).company_id.partner_id.lang or False
        return language_id

    def get_company_email_address(self, cr, uid, ids, context=None):
        ''' This is to be called from the email.template.
            Gets the company's email.
        '''
        if context is None:
            context = {}

        email = self.pool.get('res.users').browse(cr, uid, uid, context=context).company_id.email or ''
        return email

    def get_email_address_primary(self, cr, uid, ids, context=None):
        ''' This is to be called from the email.template.
            Returns the email defined as the primary email, or the empty
            string if it is not defined.
        '''
        if context is None:
            context = {}

        configuration_data = self.pool.get('configuration.data').get(cr, uid, None, context)
        email = configuration_data.email_connector_email_address_primary or ''

        return email

    def get_creation_datetime(self, cr, uid, ids, context=None):
        ''' This is to be called from the email.template.
            Returns the date and time in the format expected by the language of the email.template
        '''
        if context is None:
            context = {}

        stock_connect_file = self.browse(cr, uid, ids[0], context=context)

        config = self.pool.get('configuration.data').get(cr, uid, [], context=context)
        create_date = datetime.strptime(stock_connect_file.create_date, DEFAULT_SERVER_DATETIME_FORMAT).replace(tzinfo=pytz.utc).astimezone(pytz.timezone(config.support_timezone))

        language_obj = self.pool.get('res.lang')

        language = context.get("lang")

        if not language:
            language = self.get_company_lang(cr, uid, ids, context)

        language_ids = language_obj.search(cr, uid, [('code', '=', language), ], context=context)

        if language_ids:
            language = language_obj.browse(cr, uid, language_ids[0], context=context)
            date_format = language.date_format
            time_format = language.time_format
        else:
            date_format = DEFAULT_SERVER_DATE_FORMAT
            time_format = DEFAULT_SERVER_TIME_FORMAT

        return datetime.strftime(create_date, date_format + " " + time_format)

    def get_email_address_secondary(self, cr, uid, ids, context=None):
        ''' This is to be called from the email.template.
            Returns the email defined as the secondary email, or the empty
            string if it is not defined.
        '''
        if context is None:
            context = {}

        configuration_data = self.pool.get('configuration.data').get(cr, uid, None, context)
        email = configuration_data.email_connector_email_address_secondary or ''

        return email

    def get_picking_list(self, cr, uid, ids, context=None):
        ''' This is to be called from the email.template.
            Returns an HTML with the information contained in the picking list:
            - list of sale orders & pickings (HMTL list),
            - table of products (HTML table).
        '''
        if context is None:
            context = {}

        sale_orders_list = self.get_sale_orders_list(cr, uid, ids, context)
        products_list = self.get_products_list(cr, uid, ids, context)
        content = '{0}\n{1}\n\n{2}\n{3}'.format(_('List of Pickings'), sale_orders_list,
                                                _('List of Products'), products_list)
        return content

    def get_sale_orders_list(self, cr, uid, ids, context=None):
        ''' This is to be called from the email.template.
            Returns the HTML list of sale orders & pickings.
        '''
        if context is None:
            context = {}
        if type(ids) is not list:
            ids = [ids]

        stock_connect_file = self.browse(cr, uid, ids[0], context=context)

        html_content = ''
        if stock_connect_file.picking_ids:
            html_content = '{0}<ul>\n'.format(html_content)
            for stock_picking in stock_connect_file.picking_ids:
                html_content = '{original}\t<li>{order_name}-{picking_name}</li>\n'.format(original=html_content,
                                                                                           order_name=stock_picking.sale_id.name,
                                                                                           picking_name=stock_picking.name)
            html_content = '{original}</ul>\n'.format(original=html_content)

        return html_content

    def get_products_list(self, cr, uid, ids, context=None):
        ''' This is to be called from the email.template.
            Returns an HTML table with the product's default code,
            its description, its UOM, and its quantity.
        '''
        if context is None:
            context = {}
        if type(ids) is not list:
            ids = [ids]

        stock_picking_obj = self.pool.get('stock.picking')
        product_product_obj = self.pool.get('product.product')
        product_uom = self.pool.get('product.uom')

        # Gets all the products contained in all the stock pickings referenced by the stock.connect.file.
        stock_connect_file = self.browse(cr, uid, ids[0], context=context)
        stock_picking_ids = [sp.id for sp in stock_connect_file.picking_ids]
        product_lines = stock_picking_obj.get_product_lines(cr, uid, stock_picking_ids, context=context)

        html_content = ''
        if product_lines:
            html_content = '<table>\n\t<tr>\n\t\t<td>{0}</td>\n\t\t<td>{1}</td>\n\t\t<td>{2}</td>\n\t\t<td>{3}</td>\n\t</tr>\n'.format(_('Default Code'),
                                                                                                                                       _('Description'),
                                                                                                                                       _('Unit of Measure'),
                                                                                                                                       _('Quantity'))
            for product_line in product_lines:
                html_content = '{0}{1}'.format(html_content, '\t<tr>\n')
                product_id, uom_id, qty = product_line[0], product_line[1], product_line[2]
                product = product_product_obj.browse(cr, uid, product_id, context=context)
                uom = product_uom.browse(cr, uid, uom_id, context=context)
                html_content = '{original}\t\t<td>{default_code}</td>\n\t\t<td>{description}</td>\n\t\t<td>{uom}</td>\n\t\t<td>{qty}</td>\n'.format(original=html_content,
                                                                                                                                                    default_code=product.default_code,
                                                                                                                                                    description=product.name,
                                                                                                                                                    uom=uom.name,
                                                                                                                                                    qty=qty)
                html_content = '{0}{1}'.format(html_content, '\t</tr>\n')

            html_content = '{original}</table>\n'.format(original=html_content)

        return html_content

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
