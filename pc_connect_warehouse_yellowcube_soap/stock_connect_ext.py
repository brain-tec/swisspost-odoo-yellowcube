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
from openerp.tools import DEFAULT_SERVER_DATETIME_FORMAT, DEFAULT_SERVER_DATE_FORMAT
from datetime import datetime
import pytz
import os


OFFLINE_WSDL_PATH = mako_path = os.path.abspath(os.path.join(os.path.dirname(__file__), 'wsdl_offline/yellowcube-test.xml'))


_EXCEPTION_CONSTRAINT_YC_SOAP = """
YellowCube connections must:
1) Only run over a unique warehouse.
2) Have no selected connection transport
3) Define the URL into the SOAP endpoint
4) Have a positive value for the ART periodicy
5) Fill in 'YC Depositor No', 'YC PlantID', 'YC Sender', 'YC SupplierNo', 'YC PartnerNo', 'YC OperatingMode'
7) Set all security parameters, or empty Cert and Key paths
"""


class stock_connect_ext(osv.Model):
    _inherit = 'stock.connect'

    def _constraints_for_yellowcube_soap(self, cr, uid, ids):
        for connect in self.browse(cr, uid, ids):
            if connect.type == 'yellowcubesoap':
                if connect.yc_soapsec_key_path or connect.yc_soapsec_cert_path:
                    if not connect.yc_soapsec_key_path and connect.yc_soapsec_cert_path:
                        return False
                if len(connect.warehouse_ids) > 1:
                    return False
                if connect.connect_transport_id:
                    return False
                if connect.yc_hours_between_art_files <= 0:
                    return False
                if not connect.yc_wsdl_endpoint:
                    return False
                if (not connect.yc_depositor_no) or \
                   (not connect.yc_plant_id) or \
                   (not connect.yc_sender) or \
                   (not connect.yc_supplier_no) or \
                   (not connect.yc_partner_no) or \
                   (not connect.yc_operating_mode):
                    return False
        return True

    def _datefield_encodes_today_date(self, cr, uid, ids, date_field, current_time, current_time_timezone, context=None):
        ''' Returns whether a datetime field (parameter 'date_field') encodes a date which is in
            the same day of the date encoded by parameter 'current_time'.
                'date_field' must be an Odoo field, thus its date must be stored in UTC-0.
                'current_time' is in the timezone indicated by parameter 'timezone'.
        '''
        if context is None:
            context = {}
        if type(ids) is not list:
            ids = [ids]

        stock_connect = self.browse(cr, uid, ids[0], context=context)
        date_field_value = stock_connect[date_field]
        if not date_field_value:  # If we don't have a field value, we assume never was done.
            return False
        else:
            current_time_str = current_time.strftime(DEFAULT_SERVER_DATE_FORMAT)
            date_field_str = datetime.strptime(date_field_value, DEFAULT_SERVER_DATETIME_FORMAT).replace(tzinfo=pytz.timezone(current_time_timezone)).strftime(DEFAULT_SERVER_DATE_FORMAT)
            return current_time_str == date_field_str

    _columns = {
        'yc_soap_debugfile': fields.text("Debug file for soap messages. Empty=Ignore feature",
                                         required=False,
                                         help="Available parameters: date, time, dbname, action. Eg.: '/tmp/soap_{dbname}_{date}_{time}_{action}.log'"),
        'yc_soapsec_key_path': fields.char("Private key for signature", required=False),
        'yc_soapsec_cert_path': fields.char("Private cert for signature", required=False),

        'yc_wsdl_endpoint': fields.char("URL into WSDL endpoint for SOAP transport", required=False),
        'yc_last_bur_check': fields.datetime("Last BUR check", help="Repetead when elapsed at least one day"),
        'yc_bar_check_starting_hour': fields.float("BAR's start of downloading window", help="A BAR must be not downloaded before this hour."),
        'yc_bar_check_ending_hour': fields.float("BAR's end of downloading window", help="A BAR must not be downloaded after this hour."),
        'yc_bar_last_check': fields.datetime("Last BAR download", help="Date of the last time we downloaded a BAR file."),
        'yc_bur_send_elapsed_days': fields.boolean("BUR: Send ElapsedDays"),
        'yc_war_last_check': fields.datetime("Last WAR download", help="Date of the last time we downloaded a WAR file."),
        'yc_wba_last_check': fields.datetime("Last WBA download", help="Date of the last time we downloaded a WBA file."),
    }

    _defaults = {
        'yc_wsdl_endpoint': OFFLINE_WSDL_PATH,
        'yc_bar_check_starting_hour': 4.0,
        'yc_bar_check_ending_hour': 6.0,
        'yc_bur_send_elapsed_days': True,
    }

    _constraints = [
        (_constraints_for_yellowcube_soap, _EXCEPTION_CONSTRAINT_YC_SOAP, ['warehouse_ids', 'connect_transport_id', 'type']),
    ]

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
