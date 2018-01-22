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
from osv import osv, fields
from openerp.tools.translate import _


class configuration_data_ext(osv.Model):
    _inherit = 'configuration.data'

    def check_intrum_credentials_are_set(self, cr, uid, ids, context=None):
        """ Returns whether the minimum Intrum credentials are set.
        """
        conf = self.get(cr, uid, ids, context=context)
        credentials_are_set = conf.intrum_client_id and \
            conf.intrum_user_id and \
            conf.intrum_password
        return credentials_are_set

    _columns = {
        'intrum_client_id': fields.char('Client ID', help='Client ID for the Intrum checker service.'),
        'intrum_user_id': fields.char('User', help='User for the Intrum checker service.'),
        'intrum_password': fields.char('Password', help='Password for the Intrum checker service.'),
        'intrum_max_days_since_last_check': fields.integer('Maximum Number Of Days Since Last Check',
                                                           help='Range of days in which data are considered correct since last check.'),
        'intrum_connect_transport_id': fields.many2one('connect.transport', 'Intrum Connection',
                                                       help="Connection required to send invoices files and payment transactions to Intrum. The connection Type is 'Local SFTP'."),
        'intrum_remote_folder': fields.char('Remote Folder',
                                            help='Remote folder where to put the files in the FTP of Intrum.'),
        'intrum_url': fields.char('URL To Send Intrum Requests'),

        'intrum_positive_response_codes_ids': fields.one2many('intrum.response_code_config_line', 'configuration_id', string="Positive Response Codes",
                                                              help="Response codes to be considered correct, i.e., these responses make credit check true."),
        'intrum_contract_type': fields.selection([('person','B2C'),
                                                  ('company','B2B')],
                                                 string='Contract type',
                                                 help='If B2C is selected only the person request is sent to Intrum. If B2B is selected, the person or the company XML is sent, depending if the partner has the company field set or not. To be able to send the company XML the respective channel must be activated at Intrum first.')

    }

    _defaults = {
        'intrum_max_days_since_last_check': 30,
        'intrum_remote_folder': './Registrations',
        # By default we set TEST responses
        # 'intrum_url': 'https://secure.intrum.ch/services/creditCheckDACH_01_40/response.cfm',
        'intrum_url': 'https://secure.intrum.ch/services/creditCheckDACH_01_41_TEST/response.cfm',
        'intrum_contract_type': 'company',
    }

    def _check_connection(self, cr, uid, ids):
        obj = self.browse(cr, uid, ids[0])
        if obj.intrum_connect_transport_id and obj.intrum_connect_transport_id.type != 'localsftp':
            return False
        return True

    _constraints = [
        (_check_connection, 'Connection used to send invoices to Intrum must be SFTP.', ['intrum_connect_transport_id']),
    ]

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
