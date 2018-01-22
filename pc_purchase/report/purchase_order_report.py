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

from openerp.addons.report_webkit import report_sxw_ext
from openerp.addons.pc_generics import generics
from openerp.addons.pc_generics import generics_bvr
from openerp.addons.pc_connect_master.utilities.reports import \
    delete_report_from_db

import os


class purchase_order_report(generics.report_ext):

    def __init__(self, cr, uid, name, context):
        super(purchase_order_report, self).__init__(cr, uid, name, context=context)
        self.localcontext.update({
            'get_tax_breakdown': self.get_tax_breakdown,
            'get_top_of_css_class': self.get_top_of_css_class,
            'get_procurement_order': self.get_procurement_order,
            'assign_lines_to_pages': self.assign_lines_to_pages,
        })

    def get_tax_breakdown(self, purchase_lines, purchase_order, tax_id, context=None):
        """ Given a list of purchase lines and a tax id,
            it returns the tax code associated to that tax, the total amount paid for
            that tax, and which part of that quantity corresponds to that tax.
        """
        if context is None:
            context = {}

        tax = self.pool.get('account.tax').browse(self.cr, self.uid, tax_id, context=context)

        tax_code = tax.description  # Tax Code is saved into field 'description'

        quantity_with_taxes = 0  # The total amount paid having this tax.
        quantity_corresponding_to_taxes = 0  # The amount paid corresponding to taxes.
        for purchase_line in purchase_lines:
            purchase_line_tax_code_id = len(purchase_line.taxes_id) and purchase_line.taxes_id[0].id
            if tax.id == purchase_line_tax_code_id:
                quantity_with_taxes += purchase_line.get_total_amount_including_taxes(context=context)
                quantity_corresponding_to_taxes += purchase_line.get_amount_corresponding_to_taxes(context=context)

        return tax_code, quantity_with_taxes, quantity_corresponding_to_taxes

    def get_top_of_css_class(self, configuration_data, class_name, context=None):
        return str(self._page_num * generics_bvr.GAP_BETWEEN_PAGES + configuration_data[class_name]).replace(',', '.')

    def get_procurement_order(self, purchase_order):
        procurement_order_obj = self.pool.get('procurement.order')
        proc_order_ids = procurement_order_obj.search(self.cr, self.uid, [('purchase_id', '=', purchase_order.id),
                                                                          ], limit=1, context=self.localcontext)
        ret = None
        if proc_order_ids:
            ret = proc_order_ids[0]
        return ret

    def assign_lines_to_pages(self, order_lines, sale_order, num_lines_per_page_first, num_lines_per_page_not_first, payment_term=None,context=None):
        """ This is highly heuristic algorithm to place the elements on the different pages of the
            report.

            A Purchase order needs to print (in this order):
                   1. The regular lines of the purchase order, with a title-row as heading.
                   2. One blank lines (this may be flexible).
                   7. The taxes, grouped by code, and heading_regular_lineNO title-row (they have no heading).
                   8. The total amount to pay, taking into consideration the fees applied.

            Obviously, if the blank line appears at the end of the page, it's nonsense to print
            them.
                Also, if the number of lines in the purchase order split into different pages, the
            title-row must appear the first one in each page, and of course it's nonsense to print
            the title-row  at the end of a page (thus it may be possible that one page does not fill
            in its space completely so that the content of the next page is more beautiful).
                What has been said for the title-row for the regular lines applies also to the
            fee lines, but not to the taxes lines.

            The first page is special: since it contains the address-window and a lot of extra
            information (such as the customer number, etc.) the first page is
            special and can only contain a much lower number of entries than the next pages.

            Regular lines is of type purchase.order.line, but
            taxes are not of that type.

            All those considerations have been taken into account while developing the following
            algorithm, which places the lines into the different pages.
                The algorithm returns a list of lists, each list containing the elements to be
            printed in each page; and each element is a tuple of two elements:
                    1. A type, indicating the type of element of the second element.
                    2. An element.
        """

        # TODO: For the next change in pc_purchase, use the new algorithm to
        # TODO: split the lines into pages that is used now on pc_account.

        if context is None:
            context = {}

        def __get_lines_from_text(text):
            lines = text.split('\n')
            ret_lines = []
            for line in lines:
                no_r_lines = line.split('\r')
                for no_r_line in no_r_lines:
                    ret_lines.append(no_r_line)

            return ret_lines

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

        conf_data = self.pool.get('configuration.data').get(self.cr, self.uid, [], context=context)

        tax_ids = set()  # Stores the different taxes which the account.invoice.lines have.

        regular_lines = []
        for order_line in order_lines:
            regular_lines.append(order_line)

            # The tax code is stored in a field called 'description'; and the description in a field called 'name'.
            tax_id = (len(order_line.taxes_id) > 0) and order_line.taxes_id[0].id
            if tax_id and (tax_id not in tax_ids):
                tax_ids.add(tax_id)

        # Now, and to make more understandable the algorithm (although less efficient) we create a temporal
        # list storing all the elements, assuming they fit into a single page.
        all_lines = [('heading_regular_line', None)]
        for regular_line in regular_lines:
            all_lines.append(('regular_line', regular_line))
        all_lines.append(('blank_line', None))
        all_lines.append(('blank_line', None))
        for tax_id in tax_ids:
            all_lines.append(('tax_line', tax_id))
        all_lines.append(('total', None))
        all_lines.append(('blank_line', None))

        # We add the text part which is not into a table,
        # but we want to consider in order to print multiple pages
        if payment_term:
            lines_of_payment_term = __get_lines_from_text(payment_term.name)
            for payment_term_line in lines_of_payment_term:
                all_lines.append(('payment_term_line', payment_term_line))
            all_lines.append(('blank_line', None))

        if conf_data.purchase_ending_text:
            ending_text_lines = __get_lines_from_text(conf_data.purchase_ending_text)
            for ending_line in ending_text_lines:
                all_lines.append(('others', ending_line))

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
                    while type_line_to_introduce in ('blank_line'):
                        line_to_introduce = all_lines.pop()
                        type_line_to_introduce = __get_type_of_line(line_to_introduce)
                lines_per_page[-1].append(line_to_introduce)
                num_lines_in_current_page += 1

            # It can be that we filled-in the last element of a page, and that element was a heading.
            # We don't want headings at the end of any page, so we substitute it by an extra blank space.
            if ((num_current_page == 1) and (num_lines_in_current_page == num_lines_per_page_first)) or \
               ((num_current_page > 1) and (num_lines_in_current_page == num_lines_per_page_not_first)):
                if 'heading' in type_line_to_introduce:  # 'heading_fee_line'):
                    del lines_per_page[-1][-1]  # We remove the line introduced.
                    all_lines.append(line_to_introduce)  # We put it again on the list.
                    lines_per_page[-1].append(('blank_line', None))  # We add an extra table blank space.

            # If we have filled in the current page and there's still room for new elements, we prepare the next page.
            if __current_page_is_full(num_current_page, num_lines_in_current_page) and (len(all_lines) > 0):
                num_current_page += 1
                num_lines_in_current_page = 0
                lines_per_page.append([])  # Adds the next page.

        self._num_pages = len(lines_per_page)
        return lines_per_page


mako_path = os.path.abspath(os.path.join(os.path.dirname(__file__), 'purchase_order.mako'))
delete_report_from_db('pc_purchase_order_report')
report_sxw_ext.report_sxw_ext('report.pc_purchase_order_report',
                              'purchase.order',
                              mako_path,
                              parser=purchase_order_report)

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
