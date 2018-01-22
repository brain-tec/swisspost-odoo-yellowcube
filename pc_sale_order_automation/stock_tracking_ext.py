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


class stock_tracking_ext(osv.Model):
    _inherit = 'stock.tracking'

    def make_sscc(self, cr, uid, context=None):
        ''' Overridden so that we strip the checksum digit.
        '''
        ir_sequence_obj = self.pool.get('ir.sequence')

        sequence = super(stock_tracking_ext, self).make_sscc(cr, uid, context=context)

        # If the checksum computation fails, make_sscc will return just the sequence
        # number without the checksum appended to it, so first we check if the
        # checksum is appended or not.
        sequence_id = ir_sequence_obj.search(cr, uid, [('code', '=', 'stock.lot.tracking')], context=context)[0]
        sequence_length_without_checksum = ir_sequence_obj.browse(cr, uid, sequence_id, context=context).padding
        if len(sequence) == (sequence_length_without_checksum + 1):
            sequence = sequence[:-1]  # We strip the checksum (its last character).

        return sequence

    _columns = {
        'packaging_type_id': fields.many2one('packaging_type', 'Packaging Type'),
    }

    _defaults = {
        'name': make_sscc,
    }

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
