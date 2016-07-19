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
from openerp.osv import osv, fields
from openerp.tools.translate import _


class mapping_bur_transactiontypes(osv.Model):
    _name = 'mapping_bur_transactiontypes'

    def get_mapping(self, cr, uid, ids, transaction_type, context=None):
        ''' Searches for the indicated transaction type, in the case we have
            a mapping defined for it.

            Returns a tuple of three elements:
            (is_mapped, mapped_origin_location, mapped_destination_location)

            is_mapped is a boolean indicating if the mapping is mapped or not;
                if False, then the other parameters are set to False also.

            mapped_origin_location is the object for the stock.location which
                was defined on the mapping; or False if the location is not defined.

            mapped_destination_location is the object for the stock.location which
                was defined on the mapping; or False if the location is not defined.
        '''
        is_mapped = False
        mapped_origin_location = False
        mapped_destination_location = False

        mapping_ids = self.search(cr, uid, [('transaction_type', '=', transaction_type)], context=context)
        if mapping_ids:
            mapping = self.browse(cr, uid, mapping_ids[0], context=context)  # There must be just one per configuration (see the SQL constraint)
            is_mapped = True
            mapped_origin_location = mapping.location_id or False
            mapped_destination_location = mapping.location_dest_id or False

        return is_mapped, mapped_origin_location, mapped_destination_location

    _columns = {
        'configuration_id': fields.many2one('configuration.data', 'Configuration Data', select=True, required=True),
        'transaction_type': fields.char('TransactionType', length=10, select=True, required=True),
        'location_id': fields.many2one('stock.location', 'Source Location', domain="[('active', '=', True)]", select=True, required=True),
        'location_dest_id': fields.many2one('stock.location', 'Destination Location', domain="[('active', '=', True)]", select=True, required=True),
    }

    _sql_constraints = [
        ('uniq_configuration_transactiontype',
         'UNIQUE(configuration_id, transaction_type)',
         'A given configuration can not have duplicated TransactionTypes.'),
    ]

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
