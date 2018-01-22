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

from openerp.osv import osv, fields, orm
from openerp.tools.translate import _


class delivery_carrier_ext(osv.Model):
    _inherit = 'delivery.carrier'

    def get_carrier_for_bulk_freight(self, cr, uid, ids, context=None):
        """ Gets the carrier defined to be used instead of the current carrier if
            a bulk freight has to be used. It implements a transient mapping so that
            if carrier A maps to carrier B, and carrier B maps to C, and C maps
            to none, then A maps to carrier C.
                It detects loops. In the case a loop is detected, it raises.
                It allows to mark a carrier as being used itself as a carrier for
            bulk-freight, by selecting itself as the carrier to use by bulk-freight.

            Must be called over just one ID. If a list of IDs is received, then
            it just takes the first element of the list and skips the others.
        """
        if context is None:
            context = {}
        if type(ids) is not list:
            ids = [ids]

        carrier_for_bulk_freight = False

        carrier = self.browse(cr, uid, ids[0], context=context)

        # If this carrier defines maps to another carrier for bulk-freight, then we
        # follow the transitions. We detect loops, and in the case a loop is detected
        # we raise. We detect loops using the easy & non-memory efficient way: by storing
        # all the traversed carriers into a set and checking if that carrier was already seen.
        # The memory-efficient, two-pointers approach, may not compensate given the low amount
        # of carriers. We make an exception when detecting loops: if a carrier maps to itself,
        # then that's not considered a loop, but an indication that the mapping ends in itself.
        original_carrier_id = carrier.id
        carriers_seen_ids = set()
        while carrier.carrier_for_bulk_freight_id:
            if carrier.id == carrier.carrier_for_bulk_freight_id.id:
                carrier_for_bulk_freight = carrier
                break
            elif carrier.id not in carriers_seen_ids:
                carriers_seen_ids.add(carrier.id)
                carrier = carrier.carrier_for_bulk_freight_id
                carrier_for_bulk_freight = carrier
            else:
                raise orm.except_orm(_('Error when finding a carrier for bulk freight'),
                                     _('An infinite loop was found while mapping carrier with ID={0} for a bulk-freight use.').format(original_carrier_id))

        return carrier_for_bulk_freight

    _columns = {
        'carrier_for_bulk_freight_id': fields.many2one('delivery.carrier', 'Carrier for Bulk Freight',
                                                       help='The carrier to use instead of this one if a bulk freight has to be used.'),

    }

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
