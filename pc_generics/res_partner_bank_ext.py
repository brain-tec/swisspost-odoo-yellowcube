# b-*- encoding: utf-8 -*-
##############################################################################
#
#    Copyright (c) 2015 brain-tec AG (http://www.braintec-group.com)
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
import generics


class res_partner_bank_ext(osv.Model):
    _inherit = 'res.partner.bank'

    def __get_html_address(self, cr, uid, ids, css_linebreak_class=None, context=None):
        ''' Gets the address as an HTML layout.
            This is used for the mako reports.
        '''
        if context is None:
            context = {}

        company = self.browse(cr, uid, ids, context=context)[0]

        address_format = company.country_id and company.country_id.address_format
        if not address_format:
            address_format = "%(address_special_type)s %(address_special_type_no)s\n%(street)s %(street_no)s\n%(street2)s\n%(po_box)s\n%(zip)s %(city)s %(state_code)s\n%(country_name)s"

        # Gets the country name. If the country name is Switzerland, then it is not inserted into
        # the address: Post's sendings withing Switzerland do not contain the country in the address.
        switzerland_id = self.pool.get('res.country').search(cr, uid, [('code', '=', 'CH')], context=context)[0]
        country_name = ''
        if company.country_id and company.country_id.id != switzerland_id:
            country_name = company.country_id and company.country_id.name or ''

        args = {
            'address_special_type': '',  # Banks do not have this kind of special addresses.
            'address_special_type_no': '',  # Banks do not have this kind of special addresses.
            'state_code': company.state_id and company.state_id.code or '',
            'state_name': company.state_id and company.state_id.name or '',
            'country_code': company.country_id and company.country_id.code or '',
            'company_name': '',  # Banks do not have a parent_id.
            'street': company.street or '',
            'street_no': company.street_no or '',
            'street2': company.street2 or '',
            'po_box': company.po_box or '',
            'zip': company.zip or '',
            'city': company.city or '',
            'state_code': company.state_id and company.state_id.code or '',
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

        result_ = result_.rstrip()
        if (len(result_) > 0) and (result_[-1] == ','):
            result_ = result_[:-1]
        return result_

    def get_html_full_address(self, cr, uid, ids, css_linebreak_class=None, separate_salutation=False, context=None):
        ''' Gets the address as an HTML layout, including the name of the bank.
            This is used mainly for the mako reports.
        '''
        if context is None:
            context = {}

        partner = self.browse(cr, uid, ids, context=context)[0]

        delivery_address = partner.__get_html_address(css_linebreak_class).strip()

        separator = ', '
        if css_linebreak_class:
            separator = '<span class="{0}" />'.format(css_linebreak_class)

        full_delivery_address = '{0}{1}{2}'.format(partner.owner_name or '', separator, delivery_address)
        full_delivery_address = full_delivery_address.rstrip()
        if (len(full_delivery_address) > 0) and (full_delivery_address[-1] == ','):
            full_delivery_address = full_delivery_address[:-1]
        return full_delivery_address


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
