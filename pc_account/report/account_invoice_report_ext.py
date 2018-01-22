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

import os.path

from openerp.addons.pc_connect_master.utilities.reports import \
    delete_report_from_db
from openerp.addons.pc_generics import generics
from openerp.addons.pc_generics import generics_bvr
from openerp.addons.pc_generics.ReportLine import \
    ReportLine, split_lines_into_pages
from openerp.addons.report_webkit import report_sxw_ext
from openerp.tools.translate import _


class account_invoice_report_ext(generics.report_ext):

    def __init__(self, cr, uid, name, context):
        super(account_invoice_report_ext, self).__init__(cr, uid, name, context=context)
        self.localcontext.update({
            '_space': self._space,
            '_get_ref': self._get_ref,
            'get_invoice_title': self.get_invoice_title,
            'get_top_of_css_class': self.get_top_of_css_class,
            'print_bvr': self.print_bvr,
            'void_if_needed': self.void_if_needed,
            'show_blank_instead_of_amount_on_bvr':
                self.show_blank_instead_of_amount_on_bvr,
            'get_tax_breakdown': self.get_tax_breakdown,
            'assign_lines_to_pages': self.assign_lines_to_pages,
        })

    def assign_lines_to_pages(
            self, invoice_lines, num_lines_1st_page, num_lines_other_page,
            context=None):
        """ Returns a list of lists of elements of type ReportLine.

        :param invoice_lines: Content of the field invoice_line of an invoice.
        :param num_lines_1st_page: Number of lines of the first page.
        :param num_lines_other_page: Number of lines of the page not being
        the first one.
        :param context: The context of Odoo.
        :return: A list of lists of elements of type ReportLine. 
        """
        if context is None:
            context = {}

        # Generates the list of lines.
        report_lines = self.create_report_lines(invoice_lines, context=context)

        # Splits the lines into pages.
        lines_per_page = split_lines_into_pages(
            report_lines, num_lines_1st_page, num_lines_other_page)

        return lines_per_page

    def create_report_lines(self, invoice_lines, context=None):
        """ Generates the list of ReportLine objects, each one encoding
            a line for this mako.

        :param invoice_lines: Content of the field invoice_line of an invoice. 
        :param context: Context of Odoo.
        """
        if context is None:
            context = {}

        conf_obj = self.pool.get('configuration.data')
        conf = conf_obj.get(self.cr, self.uid, [], context=context)

        # Stores the ReportLine objects, as a list without splits.
        report_lines = []

        # Stores those account.invoice.lines which are not discount-lines.
        regular_lines = []

        # Stores the different taxes which the account.invoice.lines have.
        tax_ids = set()

        # Stores the different tax IDs to know how many different taxes we
        # must make room for, and keeps track of the regular lines found.
        for inv_line in invoice_lines:

            # We skip the discount lines
            # (those are left for pc_account_stage_discount)
            if hasattr(inv_line, 'is_discount') and inv_line.is_discount:
                continue

            regular_lines.append(inv_line)

            # The tax code is stored in a field called 'description';
            # and the description in a field called 'name'.
            tax_id = inv_line.invoice_line_tax_id and \
                     inv_line.invoice_line_tax_id[0].id
            if tax_id and (tax_id not in tax_ids):
                tax_ids.add(tax_id)

        # Now creates the list of ReportLine objects.
        heading_regular_line = \
            ReportLine(line_type='heading_regular_line', is_header=True)
        backorder_products_title = \
            ReportLine(line_type='backorder_products_title', is_header=True)
        backorder_products_heading = \
            ReportLine(line_type='backorder_products_heading', is_header=True,
                       header=backorder_products_title)

        # Adds the regular invoice lines.
        report_lines.append(heading_regular_line)
        for regular_line in regular_lines:
            report_lines.append(ReportLine(line_type='regular_line',
                                           header=heading_regular_line,
                                           data=regular_line))

        report_lines.append(ReportLine.BlankLine())

        # Adds the taxes.
        for tax_id in tax_ids:
            report_lines.append(ReportLine(line_type='tax_line', data=tax_id))

        report_lines.append(ReportLine(line_type='total'))

        # Adds the down-payments that are gift-cards, if any.
        gift_card_lines = []
        invoice = invoice_lines[0].invoice_id
        for payment in invoice.payment_ids:
            # A down-payment is a gift card if it belongs to the journal
            # set on the configuration for the gift-cards.
            if conf.gift_card_journal_id and \
               payment.journal_id.id == conf.gift_card_journal_id.id:
                gift_card_name = payment.get_debit_move_line_name()
                gift_card_lines.append(ReportLine(line_type='gift_card',
                                                  data=(payment.credit,
                                                        gift_card_name)))
        if gift_card_lines:
            report_lines.append(ReportLine.BlankLine())
            report_lines.extend(gift_card_lines)
            report_lines.append(ReportLine(line_type='total_minus_gift_cards',
                                           data=invoice.residual))

        report_lines.append(ReportLine(line_type='ending_message'))

        # If we have to print the products which are in back-orders,
        # we add them.
        invoice = invoice_lines[0].invoice_id  # Common to all the lines.
        conf = self.pool.get('configuration.data').\
            get(self.cr, self.uid, [], context=context)
        if conf.invoice_include_backorder_items and \
           invoice.backorder_items_for_invoice_ids:

            report_lines.append(ReportLine(line_type='blank_line'))
            report_lines.append(backorder_products_title)
            report_lines.append(backorder_products_heading)
            for backorder_items in invoice.backorder_items_for_invoice_ids:
                report_lines.append(ReportLine(
                    line_type='backorder_products_line',
                    header=backorder_products_heading,
                    data=(backorder_items.product_id,
                          backorder_items.product_uom_qty,
                          backorder_items.product_uom)))

        return report_lines

    def get_tax_breakdown(self, invoice_lines, invoice, tax_id, context=None):
        """ Given a list of invoice lines (which may be discount lines if the module
            stage_discount is installed) and a tax id, it returns the tax code
            associated to that tax, the total amount paid for that tax, and which part
            of that quantity corresponds to that tax.
        """
        if context is None:
            context = {}

        tax = self.pool.get('account.tax').browse(self.cr, self.uid, tax_id, context=context)

        tax_code = tax.description  # Tax Code is saved into field 'description'

        quantity_with_taxes = 0  # The total amount paid having this tax.
        quantity_corresponding_to_taxes = 0  # The amount paid corresponding to taxes.
        for invoice_line in invoice_lines:
            invoice_line_tax_code_id = len(invoice_line.invoice_line_tax_id) and invoice_line.invoice_line_tax_id[0].id
            if tax.id == invoice_line_tax_code_id:
                quantity_with_taxes += invoice_line.price_total_less_disc
        # calculate quantity_corresponding_to_taxes in order to go through tax_line's in invoice
        for tax_line in invoice.tax_line:
            if tax_line.tax_id.id == tax.id:
                quantity_corresponding_to_taxes = tax_line.amount

        return tax_code, quantity_with_taxes, quantity_corresponding_to_taxes


    def print_bvr(self, type_, context=None):
        """ Controls when the BVR is displayed,
            Currently, BVR is only displayed if it is not a refund.
        """
        if type_ == 'out_refund' or type_ == 'in_refund':
            return False
        else:
            return True

    def get_top_of_css_class(self, configuration_data, class_name, context=None):
        return str(self._page_num * generics_bvr.GAP_BETWEEN_PAGES + configuration_data[class_name]).replace(',', '.')

    def get_invoice_title(self, type_, state, context=None):
        title = ''
        if (type_ == 'out_invoice' and (state == 'open' or state == 'paid')) or type_ == 'in_invoice':
            title = _('Invoice')
        elif type_ == 'out_invoice' and state == 'proforma2':
            title = _('PRO-FORMA Invoice')
        elif type_ == 'out_invoice' and state == 'draft':
            title = _('DRAFT Invoice')
        elif type_ == 'out_invoice' and state == 'cancel':
            title = _('CANCELLED Invoice')
        elif type_ == 'out_refund' or type_ == 'in_refund':
            title = _('Credit Note')
        return title

    def show_blank_instead_of_amount_on_bvr(self, invoice, context=None):
        """ Returns whether we print or not the amount-part on the BVR of
            the invoice or if we show a blank space instead (i.e. if we print
            nothing on that area).
                Notice that this refers to all the amount-PART, that
            is, that part may be voided with 'X', but even if it's voided
            we are here deciding if we print those characters (voided or not).
        """
        conf_data = self.pool.get('configuration.data').\
            get(self.cr, self.uid, [], context=context)

        return invoice.amount_total == 0.0 and \
               conf_data.invoice_report_show_bvr_when_zero_amount_total

    def void_if_needed(self, original_content, invoice, is_bvr_ocr=False,
                       context=None):
        """ If needed, voids with a row of X's the original content received.

            Prints the real content IF any of the following
            two groups of conditions are met:

              GROUP 1 (special case):
                (1) The invoice has an amount to be paid of <= 0.0, AND
                (2) The configuration flag to show contents on BVR when the
                    amount is zero is set.
                This group is implemented by method whether_void_bvr() of
                pc_connect_master.

              GROUP 2 (regular case):
                (1) a bank account of type BVR is connected, AND
                (2) it's the report's first page, AND
                (3) the invoice is in state open (should always be otherwise
                    we shouldn't be producing the report in the first place,
                    hence might be skipped, AND
                (4) the payment method on the sale order has the
                epayment flag set to false.

            Otherwise print Xs.
        """
        if context is None:
            context = {}

        # Determines if the information has to be hidden or not.
        show_content = invoice.show_bvr() and self.is_first_page()

        content = original_content or ''
        if not show_content:
            if not is_bvr_ocr:
                # All the text but the OCR (which is an special case)
                # is filled with Xs.
                if not original_content:
                    num_x = 0
                else:
                    num_x = min(10, len(original_content or ''))

                if (num_x == 0) or (original_content[0] == '&'):
                    # If is empty or is an special HTML character...
                    num_x = 1
                content = 'X' * num_x
            else:
                # In the case of the OCR code, 0 are used instead of X
                content = '0'
                if original_content == '&gt;':
                    content = '>'
                elif original_content == '&nbsp;':
                    content = ' '
                elif original_content == '+':
                    content = '+'

        return content

    def _space(self, nbr, nbrspc=5, context=None):
        return generics_bvr._space(nbr, nbrspc)

    def _get_ref(self, inv, context=None):
        return generics_bvr._get_ref(inv)


mako_path = os.path.abspath(os.path.join(os.path.dirname(__file__), 'account_invoice.mako'))
delete_report_from_db('pc_invoice_report')
report_sxw_ext.report_sxw_ext('report.pc_invoice_report',
                              'account.invoice',
                              mako_path,
                              parser=account_invoice_report_ext)

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
