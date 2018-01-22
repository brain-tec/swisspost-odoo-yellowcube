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
from osv import osv, fields
from openerp import SUPERUSER_ID
from openerp.tools.translate import _
from openerp.addons.pc_connect_master.utilities.others import format_exception
from xsd.xml_tools import create_element, validate_xml, xml_to_string
import urllib
import urllib2
from lxml import etree
import logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


_PAYMENTMETHOD = [
    ('PENDING', 'PENDING'),
    ('INVOICE', 'INVOICE'),
    ('DIRECT-DEBIT', 'DIRECT-DEBIT'),
    ('CREDIT-CARD', 'CREDIT-CARD'),
    ('PRE-PAY', 'PER-PAY'),
    ('CASH-ON-DELIVERY', 'CASH-ON-DELIVERY'),
    ('E-PAYMENT', 'E-PAYMENT'),
    ('INSTALLMENT', 'INSTALLMENT'),
]


class intrum_request(osv.Model):
    _name = 'intrum.request'

    def create_request_xml(self, cr, uid, ids, intrum_client_id, intrum_user_id, intrum_password, context=None):
        ''' Creates the XML to be sent as the request to Intrum.
        '''
        if type(ids) is list:
            ids = ids[0]
        request = self.browse(cr, uid, ids, context=context)
        # Starts creating the root of the XML.
        xml_root = create_element('Request', attrib={'ClientId': intrum_client_id,  # Required.
                                                     'Version': '1.00',  # Required.
                                                     # 'xmlns:xsi': 'http://www.w3.org/2001/XMLSchema-instance',
                                                     # 'xsi:noNamespaceSchemaLocation': 'http://site.intrum.ch/schema/CreditDecisionRequest140.xsd',
                                                     'RequestId': str(request.id),  # Optional.
                                                     # 'Email': '',  # Optional.
                                                     'UserID': intrum_user_id,  # Optional.
                                                     'Password': intrum_password})  # Optional.

        # Starts creating the XML.
        logger.info("Creating XML for: {0}".format(request))

        # Customer
        customer_xml = create_element('Customer', attrib={'Reference': str(request.id)})
        xml_root.append(customer_xml)

        configuration_data = self.pool.get('configuration.data').get(cr, uid,
                                                                     [],
                                                                     context)

        if configuration_data.intrum_contract_type == 'company' and \
                request.partner_id.company:

            # Customer > Company
            company_xml = create_element('Company')
            customer_xml.append(company_xml)
            company_xml.append(
                create_element('CompanyName1', request.partner_id.company))

            # Customer > Company > CurrentAddress
            current_address_xml = create_element('CurrentAddress')
            current_address_xml.append(
                create_element('FirstLine', request.partner_id.street))
            if request.partner_id.street_no:
                current_address_xml.append(create_element('HouseNumber',
                                                          request.partner_id.street_no))
            current_address_xml.append(create_element('CountryCode',
                                                      request.partner_id.country_id.code))
            current_address_xml.append(
                create_element('PostCode', request.partner_id.zip))
            current_address_xml.append(
                create_element('Town', request.partner_id.city))
            company_xml.append(current_address_xml)

            # Customer > Company > ExtraInfo
            orderclosed_xml = create_element('ExtraInfo')
            orderclosed_xml.append(create_element('Name', 'ORDERCLOSED'))
            orderclosed_xml.append(create_element('Value',
                                                  request.order_closed and
                                                  'YES' or 'NO'))
            company_xml.append(orderclosed_xml)

            # Customer > Company > ExtraInfo
            order_amount_xml = create_element('ExtraInfo')
            order_amount_xml.append(create_element('Name', 'ORDERAMOUNT'))
            order_amount_xml.append(
                create_element('Value', request.order_amount))
            company_xml.append(order_amount_xml)

            # Customer > Company > ExtraInfo
            order_currency_xml = create_element('ExtraInfo')
            order_currency_xml.append(create_element('Name', 'ORDERCURRENCY'))
            order_currency_xml.append(
                create_element('Value', request.order_currency))
            company_xml.append(order_currency_xml)

            if request.order_closed and request.order_id:
                # Customer > Company > ExtraInfo
                order_id_xml = create_element('ExtraInfo')
                order_id_xml.append(create_element('Name', 'ORDERID'))
                order_id_xml.append(
                    create_element('Value', request.order_id.name))
                company_xml.append(order_id_xml)

                # Customer > Company > ExtraInfo
                payment_method_xml = create_element('ExtraInfo')
                payment_method_xml.append(
                    create_element('Name', 'PAYMENTMETHOD'))
                payment_method_xml.append(
                    create_element('Value', request.payment_method))
                company_xml.append(payment_method_xml)

        else:
            # Customer > Person
            person_xml = create_element('Person')
            customer_xml.append(person_xml)
            person_xml.append(create_element('LastName', request.partner_id.lastname))
            person_xml.append(create_element('FirstName', request.partner_id.firstname))
            if request.partner_id.birthdate:
                person_xml.append(create_element('DateOfBirth', request.partner_id.birthdate))
    
            # Customer > Person > CurrentAddress
            current_address_xml = create_element('CurrentAddress')
            current_address_xml.append(create_element('FirstLine', request.partner_id.street))
            if request.partner_id.street_no:
                current_address_xml.append(create_element('HouseNumber', request.partner_id.street_no))
            current_address_xml.append(create_element('CountryCode', request.partner_id.country_id.code))
            current_address_xml.append(create_element('PostCode', request.partner_id.zip))
            current_address_xml.append(create_element('Town', request.partner_id.city))
            person_xml.append(current_address_xml)
    
            # Customer > Person > ExtraInfo
            orderclosed_xml = create_element('ExtraInfo')
            orderclosed_xml.append(create_element('Name', 'ORDERCLOSED'))
            orderclosed_xml.append(create_element('Value', request.order_closed and 'YES' or 'NO'))
            person_xml.append(orderclosed_xml)
    
            # Customer > Person > ExtraInfo
            order_amount_xml = create_element('ExtraInfo')
            order_amount_xml.append(create_element('Name', 'ORDERAMOUNT'))
            order_amount_xml.append(create_element('Value', request.order_amount))
            person_xml.append(order_amount_xml)
    
            # Customer > Person > ExtraInfo
            order_currency_xml = create_element('ExtraInfo')
            order_currency_xml.append(create_element('Name', 'ORDERCURRENCY'))
            order_currency_xml.append(create_element('Value', request.order_currency))
            person_xml.append(order_currency_xml)
    
            if request.order_closed and request.order_id:
                # Customer > Person > ExtraInfo
                order_id_xml = create_element('ExtraInfo')
                order_id_xml.append(create_element('Name', 'ORDERID'))
                order_id_xml.append(create_element('Value', request.order_id.name))
                person_xml.append(order_id_xml)
    
                # Customer > Person > ExtraInfo
                payment_method_xml = create_element('ExtraInfo')
                payment_method_xml.append(create_element('Name', 'PAYMENTMETHOD'))
                payment_method_xml.append(create_element('Value', request.payment_method))
                person_xml.append(payment_method_xml)
        


        return xml_root

    def __get_company_currency_name(self, cr, uid, ids, context=None):
        ''' Gets the company's currency's name of the user currently logged in.
        '''
        if context is None:
            context = {}

        admin = self.pool.get('res.users').browse(cr, uid, uid, context=context)
        return admin.company_id.currency_id.name

    def do_credit_worthiness_request(self, cr, uid, ids, partner_id, order_id, amount, context=None):
        ''' Does a request to Intrum: generates the XML, sends it, and waits for the response.
                Returns the Intrum's code received as the response code, and a dictionary with the
            summary of the response.
        '''
        if context is None:
            context = {}

        try:
            # If it finds any error message it'll put it here. This way we
            # know if something went wrong.
            error = False

            # Creates the new request to Intrum in the database.
            new_cr = self.pool.db.cursor()
            values_create = {'partner_id': partner_id,
                             'order_id': order_id,
                             'order_amount': amount,
                             'order_currency': self.__get_company_currency_name(cr, uid, ids, context=context),
                             }

            if 'currency_name' in context:
                values_create.update({'order_currency': context['currency_name']})

            if order_id:
                sale_order = self.pool.get('sale.order').browse(cr, uid, 
                                                                order_id,
                                                                context=context)
                if sale_order.currency_id:
                    values_create.update({'order_currency': sale_order.currency_id.name})

            intrum_request_id = self.create(new_cr, uid, values_create, context=context)

            # Gets the credentials to connect to Intrum.
            configuration_data = self.pool.get('configuration.data').get(new_cr, uid, [], context)
            intrum_client_id = configuration_data.intrum_client_id
            intrum_user_id = configuration_data.intrum_user_id
            intrum_password = configuration_data.intrum_password

            error = False

            # If we don't have the credentials, we raise an exception.
            if not (intrum_client_id and intrum_user_id and intrum_password):
                raise osv.except_osv(_("Intrum is not configured"),
                                     _("For using the Intrum module, you need to define the intrum credentials, else uninstall this module."))

            logger.debug("Logging intrum_request.id={0}".format(intrum_request_id))
            values = {'description': '',
                      'response_code': 0,
                      'response_id': False}

            # Attempts to create the XML for a request.
            try:
                xml_root = self.create_request_xml(new_cr, uid, intrum_request_id, intrum_client_id, intrum_user_id, intrum_password, context=context)
            except Exception as e:
                error = "Error while creating the XML for the " \
                        "request: {0}".format(format_exception(e))

            # Attempts to validate the XML. If it validates, we send it to Intrum;
            # otherwise we write the error on the 'description' field.
            if not error:
                try:
                    xsd_error = validate_xml('intrum_request', xml_root)
                except Exception as e:
                    error = "Error while validating " \
                            "XML: {0}".format(format_exception(e))

            if xsd_error and (not error):
                error = 'XSD validation error: {0}'.format(xsd_error)

            # Sends the XML to Intrum if no errors happened.
            if (not xsd_error) and (not error):
                try:
                    # Converts the XML to string to send it.
                    xml_str = xml_to_string(xml_root)

                    # Stores the request sent to Intrum.
                    self.write(new_cr, uid, intrum_request_id,
                               {'request_xml': xml_str}, context=context)

                    # Sends the request to Intrum and gets the response.
                    logger.debug('XML file is going to be sent to Intrum.')
                    params = urllib.urlencode({'REQUEST': xml_str})
                    request = urllib2.Request(configuration_data.intrum_url, params)

                except Exception as e:
                    error = 'An error occurred while sending the XML ' \
                                'file with content {0}:\n{1}'.format(
                        xml_str, format_exception(e))

            # Reads the response from Intrum if no errors happened.
            if not error:
                try:
                    response = urllib2.urlopen(request)
                    content = response.read()
                except Exception as e:
                    error = 'An error occurred while reading the ' \
                                'response from Intrum for the file {0}:\n' \
                                '{1}'.format(xml_str, format_exception(e))

            # Parses the response from Intrum if no errors happened.
            if not error:
                try:
                    # Checks the request status for the client
                    # (we create the XML in a way that
                    # assures that only one client is sent each time).
                    xml = etree.XML(content)
                    response = xml.xpath("//Response")
                    response = response[0]
                    response_id = response.attrib['ResponseId']
                    customers = xml.xpath("//Customer")
                    customer = customers[0]
                    request_id = int(customer.attrib['Reference'])
                    request_status = customer.xpath("RequestStatus")[0].text
                    logger.debug('Request_id={0}, Request_status={1}'.format(request_id, request_status))

                    request = self.browse(new_cr, uid, intrum_request_id, context=context)
                    new_description = '{0} ({1} {2})'.format(self.pool.get('intrum.response_code').get_response_text(cr, uid, ids, int(request_status), context=context),
                                                             request.order_amount,
                                                             request.order_currency)

                    values['description'] = new_description
                    values['response_code'] = int(request_status)
                    values['response_id'] = response_id

                except Exception as e:
                    error = 'An error occurred while parsing the XML ' \
                                'file with content {0}:\n{1}'.format(
                        content, format_exception(e))

            if error:
                logger.error(error)
                values['description'] = error

            # Creates the results of the Intrum request that we did.
            self.write(new_cr, uid, intrum_request_id, values, context=context)
            intrum_data = self.browse(new_cr, uid, intrum_request_id, context)

            res = {'decision': intrum_data.positive_feedback}
            if intrum_data.description:
                res['description'] = intrum_data.description
            else:
                res['description'] = \
                    'Intrum Creditworthiness Check: {0} ' \
                    '(amount requested: {1} {2})'.format(
                        intrum_data.response_text,
                        intrum_data.order_amount,
                        intrum_data.order_currency)

            intrum_response_code = values['response_code']

        except Exception as e:
            logger.error('An exception happened: {0}'.format(
                format_exception(e)))

        finally:
            new_cr.commit()
            new_cr.close()

        return intrum_response_code, res

    def _fun_positive_feedback(self, cr, uid, ids, field_name, args, context=None):
        ''' Functional method. Returns whether an Intrum's request was positive or not.
            See the documentation for the auxiliary method __positive_feedback.
        '''
        if context is None:
            context = {}

        configuration_data = self.pool.get('configuration.data').get(cr, uid, [], context)

        # Gets the list of Intrum's codes which are considered as positive.
        positive_codes_intrum = []
        for intrum_positive_response_code in configuration_data.intrum_positive_response_codes_ids:
            positive_codes_intrum.append(intrum_positive_response_code.intrum_response_code_id.intrum_response_code)
        positive_codes_intrum = set(positive_codes_intrum)

        result = {}
        for request in self.browse(cr, uid, ids, context=context):
            result[request.id] = self.__positive_feedback(cr, uid, int(request.response_code), positive_codes_intrum, context)
        return result

    def __positive_feedback(self, cr, uid, response_code, positive_response_codes, context=None):
        ''' Returns if a response code is considered as positive, negative, or null.
            - If the response_code is ZERO, then we return NULL (i.e. None)
            - If the response_code is not on the set of codes considered as positive,
              or if that list is empty, we return NEGATIVE (i.e. False).
            - Otherwise: If the response code is on the set of codes considered as positive,
              we return POSITIVE (i.e. True).
        '''
        if context is None:
            context = {}

        result = True
        if response_code == 0:
            result = None
        elif len(positive_response_codes) == 0:
            result = False
        elif response_code not in positive_response_codes:
            result = False
        return result

    def _check_constraint_closed(self, cr, uid, ids):
        ''' We only allow a request to Intrum to be closed if it has an associated sale.order,
            OR if it has an associated sale order the payment method of which is not PENDING.
        '''
        for request in self.browse(cr, uid, ids):
            if request.order_closed:
                if not request.order_id.id:
                    return False
                if request.payment_method == 'PENDING':
                    return False
        return True

    def _fun_response_text(self, cr, uid, ids, field, args, context=None):
        ''' Functional which gets the descriptive text message for an Intrum's response_code.
        '''
        if context is None:
            context = {}
        intrum_response_code_obj = self.pool.get('intrum.response_code')

        res = {}
        for request in self.browse(cr, uid, ids, context=context):
            res[request.id] = intrum_response_code_obj.get_response_text(cr, uid, ids, request.response_code, context=context)

        return res

    def _fun_transaction_reported(self, cr, uid, ids, field, args, context=None):
        ''' Returns whether an intrum.transaction was reported to Intrum.
            We store the sale.order's ID, so a transaction was reported to Intrum if all
            its associated invoices (if any) were reported to Intrum.
        '''
        if context is None:
            context = {}

        result = {}
        for request in self.browse(cr, uid, ids, context=context):
            if request.order_closed:
                transaction_reported = True
                for account_invoice in request.order_id.invoice_ids:
                    if not account_invoice.reported_to_intrum:
                        transaction_reported = False
                        break
            else:
                transaction_reported = False
            result[request.id] = transaction_reported

        return result

    def get_description(self, cr, uid, ids, context=None):
        result = {}
        for request in self.browse(cr, uid, ids, context=context):
            if request.description:
                result[request.id] = request.description
            else:
                result[request.id] = '{0} ({1} {2})'.format(request.response_text,
                                                            request.order_amount,
                                                            request.order_currency)
        return result

    _log_access = True

    _columns = {
        'response_text': fields.function(_fun_response_text, type='text', store=False, string='Response code'),
        'create_uid': fields.many2one('res.users', string="Requested by", readonly=True),
        'write_date': fields.datetime('Request updated on', readonly=True),
        'partner_id': fields.many2one('res.partner', ondelete='cascade', string='Customer', required=True, readonly=True),
        'order_id': fields.many2one('sale.order', ondelete='cascade', string='Sale order', required=False, readonly=True),
        'name': fields.related('partner_id', 'ref', type="text", string="Customer reference", readonly=True),
        'response_code': fields.integer('Response code', readonly=True),
        'transaction_reported': fields.function(_fun_transaction_reported, type='boolean', store=False, string='Is the transaction reported to Intrum?'),
        'order_closed': fields.boolean('Is the order closed?', readonly=False),
        'order_amount': fields.float('Cost of the sale order', readonly=True),
        'order_currency': fields.text('Currency code', readonly=True),
        'payment_method': fields.selection(_PAYMENTMETHOD, string="Payment method",),
        'positive_feedback': fields.function(_fun_positive_feedback,
                                             string="Has positive feedback?",
                                             type='boolean',
                                             store={'intrum.request': (lambda self, cr, uid, ids, context=None: ids,
                                                                       ['response_code'],
                                                                       10)
                                                    }),
        'description': fields.text('Description', readonly=True),
        'response_id': fields.text('ID of the response', readonly=True),
        'write_date': fields.datetime('Write date', required=False),
        'request_xml': fields.text('XML request sent to Intrum', readonly=True),
    }

    _defaults = {
        'order_closed': False,
        'order_amount': 0,
        'order_currency': 'CHF',
        'response_code': 0,
        'payment_method': 'PENDING',
    }

    _constraints = [
        (_check_constraint_closed, _('A request may be closed only if it has a sale.order which is closed, or opened and with its payment method set.'), ['payment_method', 'order_closed', 'order_id']),
    ]

    _order = 'write_date DESC'

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
