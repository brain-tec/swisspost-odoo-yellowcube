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

from openerp.addons.report_webkit import report_sxw_ext
import os
from openerp.addons.pc_generics import generics
from tools.translate import _
import math
from openerp.osv import osv, fields


class report_picking_list_report(generics.report_ext):

    def __init__(self, cr, uid, name, context):
        super(report_picking_list_report, self).__init__(cr, uid, name, context=context)
        self.localcontext.update({'get_creation_datetime': self.get_creation_datetime,
                                  'assign_elements_to_pages': self.assign_elements_to_pages,
                                  'get_product': self.get_product,
                                  'get_uom': self.get_uom,
                                  })

    def get_creation_datetime(self, context=None):
        ''' Gets the datetime of right now.
        '''
        if context is None:
            context = {}
        return fields.datetime.now()

    def __group_delivery_orders_in_columns(self, objects, num_columns, context=None):
        ''' Returns a list of tuples, each tuple containing as many strings of
            the form <name of delivery>-<name of sale order> as columns we have
            indicated.
        '''
        if context is None:
            context = {}

        grouped_delivery_orders = []

        for i in range(0, len(objects), num_columns):
            group = objects[i:i + num_columns]
            for group_index in xrange(len(group)):
                stock_picking_out = group[group_index]
                group[group_index] = '{0}-{1}'.format(stock_picking_out.sale_id.name, stock_picking_out.name)
            grouped_delivery_orders.append(tuple(group))

        return grouped_delivery_orders

    def __get_product_lines(self, objects, context=None):
        ''' Returns a list of 3-tuples, each tuple being of type
            (product's ID, UOM's ID, quantity).
        '''
        if context is None:
            context = {}

        stock_picking_ids = [o.id for o in objects]
        product_lines = self.pool.get('stock.picking').get_product_lines(self.cr, self.uid, stock_picking_ids, context)
        return product_lines

    def assign_elements_to_pages(self, objects, num_lines_per_page, num_columns_listing, context=None):
        ''' Returns a list of lists, each sublist containing a 2-tuple of:
            (type_of_line, content), which represents a line in the report.
        '''
        if context is None:
            context = {}

        assert(num_lines_per_page > 10)
        elements_to_pages = [[]]
        last_page = elements_to_pages[-1]

        def count_lines_in_page(page):
            ''' Receives a list encoding a page, and returns the number of lines.
                We need this auxiliary method because not all the 'lines' are counted.
            '''
            LINES_NOT_TO_COUNT = ['start_table',
                                  'end_table',
                                  ]
            num_lines = 0
            for line in page:
                if line[0] not in LINES_NOT_TO_COUNT:
                    num_lines += 1
            return num_lines

        # Inserts the heading elements.
        last_page.append(('picking_list_title', None))
        last_page.append(('start_table', None))
        last_page.append(('document_creation_date', None))
        last_page.append(('number_of_delivery_orders', None))
        last_page.append(('end_table', None))

        # The listing of the delivery slips contained.

        last_page.append(('picking_list_delivery_orders_title', None))
        last_page.append(('start_table', None))
        grouped_delivery_orders = self.__group_delivery_orders_in_columns(objects, num_columns_listing, context)
        grouped_delivery_orders_index = 0
        while count_lines_in_page(last_page) <= num_lines_per_page:
            if count_lines_in_page(last_page) == num_lines_per_page:
                # If the page is filled, we add an extra page.
                last_page.append(('end_table', None))
                elements_to_pages.append([])
                last_page = elements_to_pages[-1]
                last_page.append(('start_table', None))
            else:
                last_page.append(('picking_list_delivery_orders_item', grouped_delivery_orders[grouped_delivery_orders_index]))
                grouped_delivery_orders_index += 1
                if grouped_delivery_orders_index == len(grouped_delivery_orders):
                    break  # The listing ended.
        if last_page[-1][0] != 'end_table':
            last_page.append(('end_table', None))

        # The listing of the products.
        last_page.append(('picking_list_products_title', None))
        product_lines = self.__get_product_lines(objects, context)
        product_lines_index = 0
        while count_lines_in_page(last_page) <= num_lines_per_page:
            if count_lines_in_page(last_page) == num_lines_per_page:
                # If the page is filled, we add an extra page.
                last_page.append(('end_table', None))
                elements_to_pages.append([])
                last_page = elements_to_pages[-1]
                last_page.append(('start_table', None))
                last_page.append(('picking_list_products_heading', None))

            elif last_page[-1][0] == 'picking_list_products_title':
                # Special case: If we just finished the listing of delivery orders,
                # then we need the heading of the table anyway.
                last_page.append(('start_table', None))
                last_page.append(('picking_list_products_heading', None))

            else:
                last_page.append(('picking_list_products_item', product_lines[product_lines_index]))
                product_lines_index += 1
                if product_lines_index == len(product_lines):
                    break  # The listing ended.
        if last_page[-1][0] != 'end_table':
            last_page.append(('end_table', None))

        # Finishes the report.
        last_page.append(('picking_list_end_of_report', None))

        return elements_to_pages

    def get_product(self, product_id, context=None):
        ''' Given a product's ID, returns the record.
        '''
        if context is None:
            context = {}
        if type(product_id) is list:
            product_id = product_id[0]
        return self.pool.get('product.product').browse(self.cr, self.uid, product_id, context=context)

    def get_uom(self, uom_id, context=None):
        ''' Given a UOM's ID, returns the record.
        '''
        if context is None:
            context = {}
        if type(uom_id) is list:
            uom_id = uom_id[0]
        return self.pool.get('product.uom').browse(self.cr, self.uid, uom_id, context=context)


mako_path = os.path.abspath(os.path.join(os.path.dirname(__file__), 'picking_list.mako'))
report_sxw_ext.report_sxw_ext('report.picking_list_report',
                              'stock.picking.out',
                              mako_path,
                              parser=report_picking_list_report)

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
