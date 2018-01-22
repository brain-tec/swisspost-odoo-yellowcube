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

from openerp.addons.report_webkit import report_sxw_ext
import os
from openerp.addons.pc_generics import generics
from openerp.addons.pc_connect_master.utilities.reports import \
    delete_report_from_db


class report_picking_report(generics.report_ext):

    def __init__(self, cr, uid, name, context):
        super(report_picking_report, self).__init__(cr, uid, name, context=context)
        self.localcontext.update({
            'assign_lines_to_pages': self.assign_lines_to_pages,
        })

    def assign_lines_to_pages(self, picking_lines, num_lines_per_page_first, num_lines_per_page_not_first, context=None):
        """  This is highly heuristic algorithm to place the elements on the different pages of the report.
        """

        # TODO: For the next change in pc_stock, use the new algorithm to
        # TODO: split the lines into pages that is used now on pc_account.
        if context is None:
            context = {}

        conf_data = self.pool.get('configuration.data').get(self.cr, self.uid, [], context=context)

        # Gets the picking of the lines.
        picking = picking_lines[0].picking_id

        # Determines if the picking is associated to a sale order which
        # has a stock type associated to its delivery carrier which is either
        # C+C or C+R, since in that case we have to consider as valid lines
        # those which have a destination location which is 'internal'.
        valid_location_usages = ['customer', 'supplier']
        sale = picking.sale_id or False
        if sale and sale.carrier_id.stock_type_id.route in ('c+c', 'c+r'):
            valid_location_usages.append('internal')

        # Adds the picking lines.
        all_lines = [('heading_regular_line', None)]
        for picking_line in picking_lines:
            if picking_line.location_dest_id.usage in valid_location_usages:
                # An stock.picking may have multiple moves associated, but for this report,
                # we are only interested in customer/supplier moves.
                all_lines.append(('regular_line', picking_line))

        # Two extra rows for separation.
        all_lines.append(('blank_line', None))
        all_lines.append(('blank_line', None))

        # Optionally adds the ending message.
        if picking.sale_id and picking.sale_id.note:
            all_lines.append(('note_message', picking.sale_id.note))
            all_lines.append(('blank_line', None))

        # Optionally prints the ending message.
        if conf_data.stock_picking_ending_text:
            all_lines.append(('ending_message', conf_data.stock_picking_ending_text or ''))
            all_lines.append(('blank_line', None))

        # Optionally prints the gift text.
        if picking.sale_id and picking.sale_id.additional_message_content:
            all_lines.append(('gift_text', picking.sale_id.additional_message_content.replace('\n', '<br />')))
            all_lines.append(('blank_line', None))

        # Optionally prints the message that more deliveries are coming.
        more_deliveries_to_come = (picking.sale_id.picking_policy == 'direct') and picking.sale_id.has_backorder() and (not picking.is_last_picking())
        if more_deliveries_to_come:
            all_lines.append(('more_deliveries_to_come_message', conf_data.stock_picking_report_text_for_partial_deliveries or ''))
            all_lines.append(('blank_line', None))

        # If we have to print the products which are in back-orders, we optionally add them to the list.
        if conf_data.stock_picking_include_backorder_items and picking.backorder_items_for_pickings_ids:
            all_lines.append(('blank_line', None))
            all_lines.append(('backorder_products_title', None))
            all_lines.append(('backorder_products_heading', None))
            for backorder_items in picking.backorder_items_for_pickings_ids:
                all_lines.append(('backorder_products_line', (backorder_items.product_id, backorder_items.product_uom_qty, backorder_items.product_uom)))

        # We remove any ending blank_line, since we do not need it and complicates the split into pages.
        while len(all_lines) > 0 and all_lines[-1][0] == 'blank_line':
            all_lines.pop()

        # Once we have the list of lines to assign, converts them to pages.
        lines_per_page = self._assign_lines_to_pages(all_lines, num_lines_per_page_first, num_lines_per_page_not_first, context=context)

        return lines_per_page

    def _assign_lines_to_pages(self, all_lines, num_lines_per_page_first, num_lines_per_page_not_first, context=None):
        """ Given a list containing the lines, and the number of lines to use on the first and next pages (different
            than the first one) it returns a list of list, each sublist i-th containing the elements which
            go to the i-th page.
        """

        def __get_type_of_line(element_in_page):
            """ Receives a tuple, encoding the elements to be introduced in each page,
                and returns its type.
            """
            return element_in_page[0]

        def __current_page_is_full(num_current_page, num_lines_in_current_page):
            """ Returns whether the current page is completely filled-in.
            """
            if num_current_page == 1:
                return num_lines_in_current_page == num_lines_per_page_first
            else:
                return num_lines_in_current_page == num_lines_per_page_not_first

        if context is None:
            context = {}

        # We reverse the lines so that we can use it as a stack (method 'pop' extracts from the tail).
        all_lines.reverse()

        # Next, starts splitting the different elements into pages. It makes so by inserting/deleting
        # elements in the list. It's not as efficient as it could be using an iterative algorithm,
        # but I prefer it to be easily understandable (and it's going to be executed only once per invoice).
        lines_per_page = [[]]

        num_current_page = 1  # The current page number we are filling-in (1 is the first one).
        num_lines_in_current_page = 0  # The current number of lines we have inserted into the current page.

        while len(all_lines) > 0:

            line_to_introduce = all_lines[-1]
            type_line_to_introduce = __get_type_of_line(line_to_introduce)

            # We first check if we start the page, and if that's the case if we need a heading on it.
            heading_introduced = False

            # We only check for pages different than the first one, since the first one always has the heading.
            if (num_lines_in_current_page == 0) and (num_current_page > 1):
                if type_line_to_introduce == 'regular_line':
                    lines_per_page[-1].append(('heading_regular_line', None))
                    heading_introduced = True
                elif type_line_to_introduce in ('backorder_products_line'):
                    lines_per_page[-1].append(('backorder_products_heading', None))
                    heading_introduced = True
                else:
                    pass  # No other types of lines require a heading.

            # If we introduced a heading at the start of the page, we do nothing more for the moment.
            if heading_introduced:
                num_lines_in_current_page += 1

            # However, if we did not introduce a heading, then we must add a new line,
            # which will be skipped if it was the first of the page AND it's blank (because
            # we don't want blank lines at the beginning of each page).
            else:
                all_lines.pop()  # We are going to introduce the line, stored in 'line_to_introduce', so we remove it.

                # We skip blank lines at the beginning of each page.
                if num_lines_in_current_page == 0:
                    while type_line_to_introduce == 'blank_line':
                        line_to_introduce = all_lines.pop()
                        type_line_to_introduce = __get_type_of_line(line_to_introduce)
                lines_per_page[-1].append(line_to_introduce)
                num_lines_in_current_page += 1

            # It can be that we filled-in the last element of a page, and that element was a heading.
            # We don't want headings at the end of any page, so we substitute it by an extra blank space.
            if ((num_current_page == 1) and (num_lines_in_current_page == num_lines_per_page_first)) or \
                    ((num_current_page > 1) and (num_lines_in_current_page == num_lines_per_page_not_first)):
                if type_line_to_introduce in ('heading_regular_line', 'backorder_products_title', 'backorder_products_heading'):  # 'heading_discount_line'):
                    del lines_per_page[-1][-1]  # We remove the line introduced.
                    all_lines.append(line_to_introduce)  # We put it again on the list.
                    lines_per_page[-1].append(('blank_line', None))  # We add an extra blank space.

            # If we have filled in the current page and there's still room for new elements, we prepare the next page.
            if __current_page_is_full(num_current_page, num_lines_in_current_page) and (len(all_lines) > 0):
                num_current_page += 1
                num_lines_in_current_page = 0
                lines_per_page.append([])  # Adds the next page.

        return lines_per_page

    def get_full_address(self, partner_obj, without_company, context=None):
        return partner_obj._display_address(partner_obj, without_company).replace('\n', '<br />')


mako_path = os.path.abspath(os.path.join(os.path.dirname(__file__), 'stock_picking.mako'))
delete_report_from_db('pc_stock_picking_report')
report_sxw_ext.report_sxw_ext('report.pc_stock_picking_report',
                              'stock.picking',
                              mako_path,
                              parser=report_picking_report)

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
