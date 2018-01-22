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


from openerp.addons.delivery_carrier_label_postlogistics.postlogistics.web_service import PostlogisticsWebService 
import re

def __prepare_recipient(self, picking):
    ''' Overwritten from delivery_carrier_label_postlogistics.postlogistics.web_service
        so that HouseNo is added.
    '''
    partner = picking.partner_id

    recipient = {
        'Name1': partner.name,
        'Street': partner.street,
        'ZIP': partner.zip,
        'City': partner.city,
        'Country': partner.country_id.code,
        'EMail': partner.email or '',
    }

    if partner.street2:
        recipient['AddressSuffix'] = partner.street2

    if partner.street_no:
        recipient['HouseNo'] = partner.street_no

    if partner.title:
        recipient['Title'] = partner.title.name

    if partner.po_box:
        recipient['POBox'] = partner.po_box

    if partner.company:
        recipient['Name2'] = partner.company
        recipient['PersonallyAddressed'] = False

    # Trim all fields to the permitted max-length to avoid errors
    if recipient.get('Name1'):
        recipient['Name1'] = recipient['Name1'][:35]

    if recipient.get('Name2'):
        recipient['Name2'] = recipient['Name2'][:35]

    if recipient.get('Street'):
        recipient['Street'] = recipient['Street'][:35]

    if recipient.get('AddressSuffix'):
        recipient['AddressSuffix'] = recipient['AddressSuffix'][:35]

    if recipient.get('POBox'):
        recipient['POBox'] = recipient['POBox'][:35]

    if recipient.get('HouseNo'):
        recipient['HouseNo'] = recipient['HouseNo'][:10]

    if recipient.get('ZIP'):
        recipient['ZIP'] = recipient['ZIP'][:10]

    if recipient.get('City'):
        recipient['City'] = recipient['City'][:35]

    if recipient.get('EMail'):
        recipient['EMail'] = recipient['EMail'][:160]

    # Phone and / or mobile should only be diplayed if instruction to
    # Notify delivery by telephone is set
    is_phone_required = [option for option in picking.option_ids
                         if option.code == 'ZAW3213']
    if is_phone_required:
        wsbc_phone = re.compile(r'[^\d+$]')
        if partner.phone:
            recipient['Phone'] = wsbc_phone.sub('', partner.phone)
            if recipient['Phone'][0:2] == '41':
                recipient['Phone'] = '00' + recipient['Phone']
            if recipient['Phone'][0:1] != '+' and recipient['Phone'][0:1] != '0':
                recipient['Phone'] = '0' + recipient['Phone']

        if partner.mobile:
            recipient['Mobile'] = wsbc_phone.sub('', partner.mobile)
            if recipient['Mobile'][0:2] == '41':
                recipient['Mobile'] = '00' + recipient['Mobile']
            if recipient['Mobile'][0:1] != '+' and recipient['Mobile'][0:1] != '0':
                recipient['Mobile'] = '0' + recipient['Mobile']

    return recipient

PostlogisticsWebService._prepare_recipient = __prepare_recipient


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
