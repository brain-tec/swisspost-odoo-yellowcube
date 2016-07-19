# b-*- encoding: utf-8 -*-
##############################################################################
#
#    Copyright (c) 2015 brain-tec AG (http://www.brain-tec.ch)
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
from openerp.addons.base.res.res_partner import res_partner
from openerp.addons.base.res.res_partner import _lang_get
import logging
logger = logging.getLogger(__name__)


class res_partner_ext(osv.Model):
    _inherit = 'res.partner'

    def default_get(self, cr, uid, fields, context=None):
        # getting the value from the default_get
        ret = super(res_partner_ext, self).default_get(cr, uid, fields, context)

        # If the partner has no selected a main category
        if 'main_category_id' not in ret:
            #             # if the partner has parent we are going get the main_category of his parent
            #             if 'default_parent_id' in context:
            #                 parent = self.browse(cr, uid, context['default_parent_id'], context)
            if context.get('main_category_id', False):
                ret['main_category_id'] = context['main_category_id']
        return ret

    def get_salutation(self, cr, uid, ids, context=None):
        ''' Returns a salutation for templates.
            The salutation is different depending on if the res.partner is company, has known gender, etc.
        '''
        if context is None:
            context = {}
        if isinstance(ids, list):
            ids = ids[0]

        salutation = ''
        partner = self.browse(cr, uid, ids, context=context)

        # If the partner is a company...
        if partner.is_company:
            salutation = _('Dear Sirs/Mesdames')

        # If the partner is a person...
        else:
            if partner.gender == 'male':
                salutation = _('Dear Mr')
            elif partner.gender == 'female':
                salutation = _('Dear Ms')
            else:  # Gender agnostic.
                salutation = _('Dear')
            salutation = '{0} {1}'.format(salutation, partner.lastname).strip()

        return salutation

    def _get_negative_of(self, cr, uid, ids, field_name, arg, context=None):
        ret = {}
        vals = self.read(cr, uid, ids, [arg], context=context)
        for val in vals:
            ret[val['id']] = not val[arg]
        return ret

    def _set_negative_of(self, cr, uid, ids, field_name, value, arg, context=None):
        return self.write(cr, uid, ids, {arg: not value}, context=context)

    def onchange_main_category_id(self, cr, uid, ids, main_category, category, parent_id=None, context=None):
        """
        This method assures there is a selected main category
        """
        # Get tags in the screen
        categs = category[0][2] or []

        # If there is a selected main category
        if main_category:
            # We make sure it is part of the other tags
            if main_category not in categs:
                # If not, we append it to the selected tags
                categs.append(main_category)
                return {'value': {'category_id': [[6, False, categs]]}}

        # If there is no main tag
        if not main_category:
            # We make the main tag to be the tag of the company
            # or the last tag
            # (remember, it is a required field)
            if parent_id:
                parent = self.pool.get('res.partner').browse(cr, uid, parent_id, context=context)
                logger.debug('value of parent {0}'.format(parent.main_category_id))
                main_category = parent.main_category_id.id
            elif categs:
                main_category = categs[-1]

            return {'value': {'main_category_id': main_category}}

        # Else, do nothing.
        return {}

    def _check_zip_code_ch(self, cr, uid, ids, context=None):
        """
        Ensure that the zip code is a number between 1000 and 9999.
        """
        # Iteration over the partners
        for partner in self.browse(cr, uid, ids, context=context):
            # Checking if it's a Swiss partner
            if partner.country_id.code == 'CH':
                if partner.zip:
                    _zip = partner.zip.strip()
                    # We have to check if it's numeric
                    if not _zip or not _zip.isnumeric():
                        logger.debug("Faulty ZIP res.partner:{0}".format(partner.id))
                        return False
                    # It's necessary to be a number between 1000 and 9999
                    if not 1000 <= int(_zip) <= 9999:
                        logger.debug("Faulty ZIP res.partner:{0}".format(partner.id))
                        return False
                    if ' ' in partner.zip:
                        partner.write({'zip': _zip})
        return True

    def check_credit(self, cr, uid, ids, amount, priority=None, priorities=None, context=None):
        ''' Checks if a quantity can be paid by this res.partner.
        '''
        if priority is not None:
            return {}

        if context is None:
            context = {}
        if isinstance(ids, list):
            ids = ids[0]

        res = self.check_credit_base(cr, uid, ids, amount, context=context)

        # If the internal check fails, then we don't keep investigating.
        if priorities and res['decision']:
            priorities = sorted(set(priorities))
            for p in priorities:
                res_aux = self.pool.get('res.partner').check_credit(cr, uid, ids, amount, p, priorities, context=context)
                if res_aux != {}:
                    if res_aux['decision'] is False:
                        return res_aux
                    else:
                        str_aux = '\n'.join([res['description'], res_aux['description']])
                        res = res_aux
                        res['description'] = str_aux

        return res

    def check_credit_base(self, cr, uid, ids, amount, context=None):
        ''' Base credit check for a res.partner. It checks that the amount asked is still under the
            amount the res.partner can ask for, taking into account its credit.
        '''
        if context is None:
            context = {}
        if isinstance(ids, list):
            ids = ids[0]

        res = {}

        partner = self.pool.get('res.partner').browse(cr, uid, ids, context=context)

        # Start of 1st stage: Internal credit limit
        # get the parent's credit
        while partner.parent_id:
            partner = partner.parent_id
        credit_limit = partner.credit_limit
        credit = partner.credit

        if not credit_limit:
            config = self.pool.get('configuration.data').get(cr, uid, [], context=context)
            credit_limit = config.default_credit_limit

        # Check if the amount is smaller than the difference between credit_limit and credit
        if not credit:
            credit = 0.0
        if amount <= (credit_limit - credit):
            res['decision'] = True
            res['description'] = _("Internal credit check is positive.")
        else:
            res['decision'] = False
            res['description'] = _("Internal credit limit failed, remaining credit is: {0} for a request of {1}.").format(credit_limit - credit, amount)

        return res

    _columns = {
        'main_category_id': fields.many2one('res.partner.category', string='Main Tag', required=False),
        'newsletter_allowed': fields.function(_get_negative_of,
                                              arg='opt_out',
                                              fnct_inv=_set_negative_of,
                                              fnct_inv_arg='opt_out',
                                              type='boolean',
                                              store=False,
                                              string='Newsletter Allowed',
                                              help='The user allows the communication for mass mailing, and marketing campaigns.'),

        'gender': fields.selection([('other', _('Other')),
                                    ('male', _('Male')),
                                    ('female', _('Female')),
                                    ], 'Gender',
                                   required=False,
                                   help='Gender of the partner, other if unknown'),

        'po_box': fields.char('P.O. Box', size=35, help='P.O. Box Number'),
        'street_no': fields.char('Street number', size=10, help='Street number'),

        'type': fields.selection([('default', _('Default')),
                                  ('invoice', _('Invoice')),
                                  ('delivery', _('Shipping')),
                                  ('contact', _('Contact')),
                                  ('other', _('Other')),
                                  ('pickpost', _('PickPost')),
                                  ('mypost24', _('MyPost24')),
                                  ], _('Address Type'),
                                 help="Used to select automatically the right address according to the context in sales and purchases documents."),
        'pickpost_mypost24_no': fields.char('PickPost/MyPost24 Customer No.', size=50, help="Customer number for PickPost/MyPost24"),

        # Field 'company' was originally defined in the module 'magentoerpconnect', but it has been placed
        # here so that we can use it without depending on that module.
        'company': fields.char('Company'),

        'po_box': fields.char('P.O. Box', size=35, help='P.O. Box Number'),

        # Redefines the language to be mandatory for a res.partner.
        'lang': fields.selection(_lang_get, 'Language', required=True,
                                 help='If the selected language is loaded in the system, all documents related to this contact will be printed in this language. If not, it will be English.'),
    }

    _defaults = {
        'notification_email_send': 'none',
        'lang': lambda self, cr, uid, ctx: ctx.get('lang', 'en_US'),
        'credit_limit': 0.0,
    }

    _constraints = [(_check_zip_code_ch, 'The Zip code from CH must be a number between 1000 and 9999', ['zip']),
                    ]


def _new_display_address(self, cr, uid, address, without_company=False, context=None):
    '''
    The purpose of this function is to build and return an address formatted accordingly to the
    standards of the country where it belongs.

    :param address: browse record of the res.partner to format
    :returns: the address formatted in a display that fit its country habits (or the default ones
        if not country is specified)
    :rtype: string
    '''

    if isinstance(address, list):
        address = self.pool.get('res.partner').browse(cr, uid, address[0], context=context)
    elif isinstance(address, int):
        address = self.pool.get('res.partner').browse(cr, uid, address, context=context)

    address_special_type_args = {'address_special_type': '',
                                 'address_special_type_no': '',
                                 }

    address_format = address.country_id and address.country_id.address_format
    if not address_format:
        address_format = "%(address_special_type)s %(address_special_type_no)s\n%(street)s %(street_no)s\n%(street2)s\n%(po_box)s\n%(zip)s %(city)s %(state_code)s\n%(country_name)s"

    if address.type == 'pickpost':
        address_special_type_args['address_special_type'] = 'PickPost'
        address_special_type_args['address_special_type_no'] = address.pickpost_mypost24_no
    elif address.type == 'mypost24':
        address_special_type_args['address_special_type'] = 'MyPost24'
        address_special_type_args['address_special_type_no'] = address.pickpost_mypost24_no

    # Gets the country name. If the country name is Switzerland, then it is not inserted into
    # the address: Post's sendings withing Switzerland do not contain the country in the address.
    switzerland_id = self.pool.get('res.country').search(cr, uid, [('code', '=', 'CH')], context=context)[0]
    country_name = ''
    if address.country_id and address.country_id.id != switzerland_id:
        country_name = address.country_id and address.country_id.name or ''

    args = {
        'address_special_type': address_special_type_args.get('address_special_type', ''),
        'address_special_type_no': address_special_type_args.get('address_special_type_no', ''),
        'state_code': address.state_id and address.state_id.code or '',
        'state_name': address.state_id and address.state_id.name or '',
        'country_code': address.country_id and address.country_id.code or '',
        'company_name': address.parent_id and address.parent_id.name or '',
        'street': address.street or '',
        'street_no': address.street_no or '',
        'street2': address.street2 or '',
        'po_box': address.po_box or '',
        'zip': address.zip or '',
        'city': address.city or '',
        'state_code': address.state_id and address.state_id.code or '',
        'country_name': country_name,
    }

    for field in self._address_fields(cr, uid, context=context):
        args[field] = getattr(address, field) or ''
    if without_company:
        args['company_name'] = ''
    elif hasattr(address, 'company') and address.company:
        address_format = '%(company_name)s\n' + address_format
    result = address_format % args
    return result


res_partner._display_address = _new_display_address

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
