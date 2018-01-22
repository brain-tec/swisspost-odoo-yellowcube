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
from openerp.addons.pc_account.report import account_invoice_report_ext
from openerp.addons.pc_connect_master.utilities.reports import \
    delete_report_from_db
from openerp.addons.pc_generics.ReportLine import \
    ReportLine, split_lines_into_pages

# We reuse the mako from pc_account.
from openerp.addons.pc_account.report.account_invoice_report_ext import mako_path


class account_invoice_report_ext(account_invoice_report_ext.account_invoice_report_ext):

    def __init__(self, cr, uid, name, context):
        super(account_invoice_report_ext, self).__init__(cr, uid, name, context=context)
        self.localcontext.update({
            'get_discount_description': self.get_discount_description,
        })

    def create_report_lines(self, invoice_lines, context=None):
        """ Overridden to add the discount lines.

        :param invoice_lines: Content of the field invoice_line of an invoice.
        :param context: Context of Odoo
        :return: 
        """
        report_lines = super(account_invoice_report_ext, self).\
            create_report_lines(invoice_lines, context=context)

        conf_obj = self.pool.get('configuration.data')
        precision_obj = self.pool.get('decimal.precision')

        conf = conf_obj.get(self.cr, self.uid, [], context=context)
        product_price_min_decimal = \
            1.0 / (10 ** precision_obj.precision_get(self.cr, self.uid,
                                                     'Product Price'))

        # The line which stores the subtotal (None if there are no discounts).
        subtotal_line = None

        # Stores those account.invoice.lines which are discount lines.
        discount_lines = []

        # If there is any discount, we keep track of the discount lines, and
        # compute on the go the amount saved because of it.
        total_amount_saved = 0
        for inv_line in invoice_lines:
            if hasattr(inv_line, 'is_discount') and inv_line.is_discount:
                # The discount of type 'subtotal' is special (since it's not
                # a discount at all) and we are going to render it differently
                # (see the line of type 'subtotal').
                if inv_line.discount_type != 'subtotal':
                    discount_lines.append(inv_line)
                else:
                    subtotal_line = inv_line
            else:
                amount_saved = inv_line.quantity * inv_line.price_unit - \
                               inv_line.price_total_less_disc

                # If the difference is greater than the precision,
                # we assume we made some discount; otherwise we don't add it
                # to the amount discounted because we assume it's a
                # floating-point-related rounding-error.
                if amount_saved >= product_price_min_decimal:
                    total_amount_saved += amount_saved

        # Adds ReportLine objects into the correct part of the list of lines.
        # The portion for the discounts goes just before the part for taxes.
        num_line_tax_type = 0
        while num_line_tax_type < len(report_lines):
            line = report_lines[num_line_tax_type]
            if line.line_type == 'tax_line':
                break
            num_line_tax_type += 1

        report_discount_lines = []
        if discount_lines:
            report_discount_lines.append(ReportLine(line_type='subtotal',
                                                    data=subtotal_line))
            report_discount_lines.append(ReportLine.BlankLine())

        for discount_line in discount_lines:
            report_discount_lines.append(ReportLine(line_type='discount_line',
                                                    data=discount_line))
        if discount_lines:
            report_discount_lines.append(ReportLine.BlankLine())
        if (total_amount_saved > 0) and \
           conf.invoice_report_discounted_total_amount_active:
            report_discount_lines.append(
                ReportLine(line_type='total_amount_saved',
                           data=total_amount_saved))

        # Fits the discount elements into the old ones.
        report_lines = \
            report_lines[:num_line_tax_type] + \
            report_discount_lines + \
            report_lines[num_line_tax_type:]

        return report_lines

    def get_discount_description(self, discount_line, context=None):
        """ Gets the discount's description depending on the type of discount.
                The only special case is when the type of discount is 'product': in that case
            we get the product and return its name. In order to translate the name of the product,
            we must receive the language within the context (using the key 'lang').
        """
        if discount_line.discount_type == 'product':
            description = discount_line.product_id.name
        else:
            description = discount_line.name

        return description or ''


# We reuse the mako from pc_account.
delete_report_from_db('invoice.stage_discount.report')
report_sxw_ext.report_sxw_ext('report.invoice.stage_discount.report',
                              'account.invoice',
                              mako_path,
                              parser=account_invoice_report_ext)

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
