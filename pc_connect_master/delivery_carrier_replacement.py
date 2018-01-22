# b-*- encoding: utf-8 -*-
##############################################################################
#
#    Copyright (c) 2017 brain-tec AG (http://www.braintec-group.com)
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

from openerp.osv import osv, fields, orm


class delivery_carrier_replacement(osv.Model):
    """ A prioritized list of possible replacement for a delivery.carrier
    """
    _name = 'delivery.carrier.replacement'

    _columns = {
        'sequence': fields.integer(
            'Sequence', help='Sequence for reordering.'),
        'original_carrier_id': fields.many2one(
            'delivery.carrier', 'Original Carrier', required=True),
        'replacement_carrier_id': fields.many2one(
            'delivery.carrier', 'Replacement Carrier', required=True),
    }

    _defaults = {
        'sequence': lambda *a: 1,
    }

    _order = 'sequence ASC'

    _sql_constraints = [
        ('Replacement Carriers Can Not Be Duplicated',
         'unique (original_carrier_id,replacement_carrier_id)',
         'A carrier used for replacement can not be duplicated.'),

        ('Carrier Can Not Replace Itself',
         'check(original_carrier_id <> replacement_carrier_id)',
         'A carrier can not replace itself.'),
    ]

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
