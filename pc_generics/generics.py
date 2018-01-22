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

import os
from datetime import datetime
#from openerp.report import report_sxw
from openerp.addons.report_webkit import report_sxw_ext
from openerp.addons.report_webkit import report_helper
from openerp.tools import mod10r
import logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class report_ext(report_sxw_ext.rml_parse):
    def __init__(self, cr, uid, name, context):
        super(report_ext, self).__init__(cr, uid, name, context=context)
        self.localcontext.update({
            'cr': cr,
            'uid': uid,
            'ctx': context,
            'mod10r': mod10r,
            'get_date_today': self.get_date_today,
            'get_configuration_data': self.get_configuration_data,
            'get_address_salutation': self.get_salutation,
            'assign_lines_to_pages': self.assign_lines_to_pages,
            'reassign_elements_in_last_page': self.reassign_elements_in_last_page,
            'get_page_num': self.get_page_num,
            'increment_page_num': self.increment_page_num,
            'is_first_page': self.is_first_page,
            'is_last_page': self.is_last_page,
            'clean_url': self.clean_url,
            'split_into_html_lines': self.split_into_html_lines,
        })

        self._page_num = 0
        self._num_pages = None

    def get_page_num(self, context=None):
        return self._page_num

    def increment_page_num(self, context=None):
        self._page_num += 1

    def is_first_page(self, context=None):
        return (self._page_num == 0)

    def is_last_page(self, context=None):
        assert(self._num_pages is not None)
        return (self._page_num == self._num_pages - 1)

    def get_date_today(self, context=None):
        ''' Gets the date of today.
        '''
        now = datetime.now()
        return now

    def get_configuration_data(self, context=None):
        ''' Gets the default configuration data for the company's parameters.
        '''
        if context is None:
            context = {}
        return self.pool.get('configuration.data').get(self.cr, self.uid, [], context=context)

    def get_salutation(self, partner_obj, context=None):
        address_salutation = ''
        if (not partner_obj.is_company) and partner_obj.title:
            address_salutation = partner_obj.title.name
        return address_salutation

    def get_bank_account(self, cr, uid, context=None):
        if context is None:
            context = {}

        company_id = self.pool.get('res.users').browse(cr, uid, uid, context=context).company_id.id
        company_obj = self.pool.get('res.company').browse(cr, uid, company_id, context=context)
        account_number = None
        if len(company_obj.bank_ids) > 0:
            account_number = company_obj.bank_ids[0].acc_number
        return account_number

    def assign_lines_to_pages(self, invoice_lines, num_lines_per_page_first, num_lines_per_page_not_first=None, context=None):
        ''' Returns a list of list, each element of that later list containing an
            object of type account.invoice.line. This way we know which lines
            must be printed in any of the pages.
        '''

        if num_lines_per_page_not_first is None:
            num_lines_per_page_not_first = num_lines_per_page_first

        lines_to_pages = []
        lines_in_current_page = []
        for line in invoice_lines:
            # The number of lines allowed differs on the first page w.r.t. the other ones.
            if len(lines_to_pages) == 0:
                num_lines_allowed = num_lines_per_page_first
            else:
                num_lines_allowed = num_lines_per_page_not_first

            if len(lines_in_current_page) != num_lines_allowed:
                lines_in_current_page.append(line)
            else:
                lines_to_pages.append(lines_in_current_page)
                lines_in_current_page = [line]
        if len(lines_in_current_page) > 0:
            lines_to_pages.append(lines_in_current_page)

        self._num_pages = len(lines_to_pages)
        return lines_to_pages

    def reassign_elements_in_last_page(self, lines_to_pages, maximum_lines_last_page, context=None):
        ''' It could be that the last page is special and that we need it to have less elements.
            In that case, we split the elements of the last page into two pages.
        '''
        # If the number of elements in the last page is greater than the indicated, split it into two.
        if len(lines_to_pages[-1]) > maximum_lines_last_page:
            lines_last_page = lines_to_pages.pop()
            penultimate_page_elements = lines_last_page[:-maximum_lines_last_page]
            last_page_elements = lines_last_page[-maximum_lines_last_page:]

            lines_to_pages.append(penultimate_page_elements)
            lines_to_pages.append(last_page_elements)

        self._num_pages = len(lines_to_pages)
        return lines_to_pages

    def clean_url(self, url, context=None):
        """ Returns the URL without the protocol and without any trailing "/".
        """
        cleaned_url = url
        if cleaned_url:
            cleaned_url = cleaned_url.split('://')[-1].rstrip('/')
        return cleaned_url

    def split_into_html_lines(self, text, context=None):
        """ Replaces any line break in the text by "<br/>".
        """
        return (text or '').replace(os.linesep, '<br />')


def __get_logo(self, cr, uid, ids, webkit_logo_id, width=None, height=None, context=None):
    ''' - Returns the logo stored in OpenERP (in Settings > Companies > Webkit Logos).
        - If it does not exist, then instead of blocking the generation of the report
          it puts no logo on it.
        - Receives an ir.header_img.

        The width and height are optional, and are set in millimetres. Turns
        out that the method embed_logo_by_name requires those measurements
        in pixels, so we make a change of units.
    '''
    if context is None:
        context = {}

    helper = report_helper.WebKitHelper(cr, uid, 'followup_rml_parser', context=context)
    if webkit_logo_id:
        if type(webkit_logo_id) is list:
            webkit_logo_id = webkit_logo_id[0]
        webkit_logo_name = self.pool.get('ir.header_img').browse(cr, uid, webkit_logo_id.id, context).name
        image = helper.embed_logo_by_name(webkit_logo_name)

        # embed_logo_by_name returns the measurements in px, and we want it
        # in mm because we are going to print a paper obviously, so we do
        # the change. However the width of the image has to be set with a style
        # in order to not use pixels, so we inject the CSS-style inline.
        styles = ""
        if width or height:
            styles = 'style="'
            if width:
                styles += "width: {0}mm; ".format(width)
            if height:
                styles += "height: {0}mm; ".format(height)
            styles += '"'
        if styles:
            image = image.replace("<img", "<img {0} ".format(styles))

    else:
        image = '<span>&nbsp;</span>'
    return image


def __get_company_address(self, cr, uid, ids, css_linebreak_class=None, context=None):
    ''' Gets the address of the company of the user who is logged in.
    '''
    if context is None:
        context = {}

    # Gets the res.company associated to the current res.user
    company_id = self.pool.get('res.users').browse(cr, uid, uid, context=context).company_id.id
    company_obj = self.pool.get('res.company').browse(cr, uid, company_id, context=context)

    address_format = company_obj.country_id and company_obj.country_id.address_format
    if not address_format:
        address_format = "%(address_special_type)s %(address_special_type_no)s\n%(street)s %(street_no)s\n%(street2)s\n%(po_box)s\n%(zip)s %(city)s %(state_code)s\n%(country_name)s"

    # Gets the country name. If the country name is Switzerland, then it is not inserted into
    # the address: Post's sendings withing Switzerland do not contain the country in the address.
    switzerland_id = self.pool.get('res.country').search(cr, uid, [('code', '=', 'CH')], context=context)[0]
    country_name = ''
    if company_obj.country_id and company_obj.country_id.id != switzerland_id:
        country_name = company_obj.country_id and company_obj.country_id.name or ''

    args = {
        'address_special_type': '',  # Companies do not have mypost24 nor things like that.
        'address_special_type_no': '',  # Companies do not have mypost24 nor things like that.
        'state_code': company_obj.state_id and company_obj.state_id.code or '',
        'state_name': company_obj.state_id and company_obj.state_id.name or '',
        'country_code': company_obj.country_id and company_obj.country_id.code or '',
        'company_name': company_obj.parent_id and company_obj.parent_id.name or '',
        'street': company_obj.street or '',
        'street_no': company_obj.street_no or '',
        'street2': company_obj.street2 or '',
        'po_box': company_obj.po_box or '',
        'zip': company_obj.zip or '',
        'city': company_obj.city or '',
        'state_code': company_obj.state_id and company_obj.state_id.code or '',
        'country_name': country_name,
    }
    result = address_format % args

    # Removes blank lines from the address
    result_ = ''
    lines = result.split('\n')
    for line in lines:
        if len(line.strip()) > 0:
            if css_linebreak_class:
                result_ += '{0} <span class="{1}" />'.format(line.strip(), css_linebreak_class)
            else:
                result_ += '{0}, '.format(line.strip())

    if (len(result_) > 0) and (result_[-1] == ','):
        result_ = result_[:-1]
    return result_


def __get_address_fields(self, cr, uid, ids, context=None):
    if context is None:
        context = {}

    # Gets the res.company associated to the current res.user
    company_id = self.pool.get('res.users').browse(cr, uid, uid, context=context).company_id.id
    company_obj = self.pool.get('res.company').browse(cr, uid, company_id, context=context)

    address_fields = {}
    address_fields['zip'] = company_obj.zip or ''
    address_fields['country_code'] = company_obj.country_id and company_obj.country_id.code or ''
    address_fields['town'] = company_obj.city or ''

    return address_fields


def has_mako_header():
    def _has_mako_header(_class):
        logger.debug("Decorating class {0}".format(_class))
        params = {
            'get_company_address': __get_company_address,
            'get_logo': __get_logo,
            'get_address_fields': __get_address_fields,
        }
        for k in params:
            if not hasattr(_class, k):
                setattr(_class, k, params[k])
        return _class
    return _has_mako_header

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
