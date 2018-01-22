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


class product_alternative(osv.osv):
    ''' Links to products that could be displayed as alternative
        or replacement in the case the stock runs out.
    '''

    _name = 'product.alternative'

    def unlink(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        elif 'symmetric_related_unlinked' in context:
            return super(product_alternative, self).unlink(cr, uid, ids, context)
        context['symmetric_related_unlinked'] = True

        all_unlinked = True
        for _id in ids:
            # Gets the ID of the source and the alternative products.
            source_product_id = self.browse(cr, uid, ids[0], context=context).product_id.id
            alternative_product_id = self.browse(cr, uid, ids[0], context=context).product_alternative_id.id

            # Checks if the symmetric exists, and if that is the case removes it also.
            symmetric_relation_ids = self.search(cr, uid, [('product_id', '=', alternative_product_id),
                                                           ('product_alternative_id', '=', source_product_id)],
                                                 context=context)
            if symmetric_relation_ids:
                unlinked = self.unlink(cr, uid, symmetric_relation_ids, context=context)
                all_unlinked = all_unlinked and bool(unlinked)

            unlinked = super(product_alternative, self).unlink(cr, uid, _id, context)
            all_unlinked = all_unlinked and bool(unlinked)

        del context['symmetric_related_unlinked']
        return all_unlinked

    def create(self, cr, uid, values, context=None):
        if context is None:
            context = {}
        elif 'symmetric_related_created' in context:
            return super(product_alternative, self).create(cr, uid, values, context=context)
        context['symmetric_related_created'] = True

        # Gets the ID of the source and the alternative products.
        source_product_id = values['product_id']
        alternative_product_id = values['product_alternative_id']

        # Finds if this relation already exists.
        relation_exists = self.search(cr, uid, [('product_id', '=', source_product_id),
                                                ('product_alternative_id', '=', alternative_product_id)],
                                      context=context, count=True)

        _id = -1
        if not relation_exists:
            # Creates the relation.
            _id = super(product_alternative, self).create(cr, uid, values, context=context)

            # Finds if the symmetric relation exists.
            symmetric_relation_exists = self.search(cr, uid, [('product_id', '=', alternative_product_id),
                                                              ('product_alternative_id', '=', source_product_id)],
                                                    context=context, count=True)

            # If the symmetric relation does not exist, creates it.
            if not symmetric_relation_exists:
                self.create(cr, uid, {'product_id': alternative_product_id,
                                      'product_alternative_id': source_product_id},
                            context=context)

        del context['symmetric_related_created']
        return _id

    _columns = {
        'product_id': fields.many2one('product.product', 'Source Product', required=True),
        'product_alternative_id': fields.many2one('product.product', 'Alternative Product', required=True, ondelete='restrict'),
    }

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: