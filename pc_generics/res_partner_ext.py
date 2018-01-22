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
from openerp.osv import osv, fields
from openerp.tools.translate import _
from generics import report_ext


class res_partner_ext(osv.Model):
    _inherit = 'res.partner'

    def get_ref(self, cr, uid, ids, context=None):
        ''' Returns the customer's reference.
        '''
        if context is None:
            context = {}
        partner = self.browse(cr, uid, ids, context=context)[0]
        while partner.parent_id and partner.id != partner.parent_id.id:
            partner = partner.parent_id
        return partner.ref

    def __get_html_address(self, cr, uid, ids, css_linebreak_class=None, context=None):
        if context is None:
            context = {}

        company = self.browse(cr, uid, ids, context=context)[0]

        address_special_type_args = {'address_special_type': '',
                                     'address_special_type_no': '',
                                     }
        address_format = company.country_id and company.country_id.address_format
        if not address_format:
            address_format = "%(address_special_type)s %(address_special_type_no)s\n%(street)s %(street_no)s\n%(street2)s\n%(po_box)s\n%(zip)s %(city)s %(state_code)s\n%(country_name)s"

        if company.type == 'pickpost':
            address_special_type_args['address_special_type'] = 'PickPost'
            address_special_type_args['address_special_type_no'] = company.pickpost_mypost24_no
        elif company.type == 'mypost24':
            address_special_type_args['address_special_type'] = 'MyPost24'
            address_special_type_args['address_special_type_no'] = company.pickpost_mypost24_no

        # Gets the country name. If the country name is Switzerland, then it is not inserted into
        # the address: Post's sendings withing Switzerland do not contain the country in the address.
        switzerland_id = self.pool.get('res.country').search(cr, uid, [('code', '=', 'CH')], context=context)[0]
        country_name = ''
        if company.country_id and company.country_id.id != switzerland_id:
            country_name = company.country_id and company.country_id.name or ''

        args = {
            'address_special_type': address_special_type_args.get('address_special_type', ''),
            'address_special_type_no': address_special_type_args.get('address_special_type_no', ''),
            'state_code': company.state_id and company.state_id.code or '',
            'state_name': company.state_id and company.state_id.name or '',
            'country_code': company.country_id and company.country_id.code or '',
            'company_name': company.parent_id and company.parent_id.name or '',
            'street': company.street or '',
            'street_no': company.street_no or '',
            'street2': company.street2 or '',
            'po_box': company.po_box or '',
            'zip': company.zip or '',
            'city': company.city or '',
            'state_code': company.state_id and company.state_id.code or '',
            'country_name': country_name,
        }
        args.update(address_special_type_args)
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
        if context is None:
            context = {}

        partner = self.browse(cr, uid, ids, context=context)[0]

        partner_generic = report_ext(cr, uid, 'res.partner', context)
        rows = []

        name = '{0} {1}'.format(partner.firstname or '', partner.lastname or '').strip()

        # Joins (or not) the salutation, depending on if it has to be separated/printed or not.
        salutation = (partner_generic.get_salutation(partner) or '').strip()
        separator_salutation = '<span class="{0}" />'.format(css_linebreak_class) if separate_salutation else ' '
        salutation_name = '{0}{1}{2}'.format(salutation, separator_salutation, name).strip()

        if not partner.company:
            # If the partner doesn't have a company, we do print the salutation (if any)
            if css_linebreak_class:
                # If a line-break is provided, we place the salutation on different lines.
                if salutation:
                    rows.append(salutation)
                rows.append(name)
            else:
                # If no line-break is provided, we join the salutation and the name.
                rows.append(salutation_name)
        else:
            # If the partner has a company, we print the salutation on the same line as the name
            rows.append(partner.company)
            rows.append(salutation_name)

        if partner.street2:
            rows.append(partner.street2)
        if partner.po_box:
            rows.append(' '.join([_('P.O. Box'), partner.po_box]))
        address = ' '.join([partner.street or '', partner.street_no or '']).strip(' ')
        if address:
            rows.append(address)
        country = partner.country_id.name or ''
        state = partner.state_id.code or ''
        if partner.country_id.code == 'CH':
            state = country = ''
        city = ' '.join([partner.zip or '', partner.city or '', state]).strip(' ')
        if city:
            rows.append(city)
        if country:
            rows.append(country)

        if css_linebreak_class:
            separator = '<span class="{0}" />'.format(css_linebreak_class)
        else:
            separator = ', '
        return separator.join(rows)

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
