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


class packaging_type(osv.Model):
    _name = 'packaging_type'

    def unlink(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        if type(ids) is not list:
            ids = [ids]

        product_ids = self.pool.get('product.product').search(cr, uid, [('packaging_type_id', 'in', ids)], context=context)
        if product_ids:
            packaging_types = []
            for packaging in self.browse(cr, uid, ids, context=context):
                packaging_types.append(packaging.name)
            packaging_types = ', '.join(packaging_types)

            raise orm.except_orm(_('Can not remove the Packaging Type.'),
                                 _('The Packaging Types {0} can not be removed because the products with the '
                                   'following IDs have it set: {1}').format(packaging_types,
                                                                            ', '.join(map(str, product_ids))))

        return super(packaging_type, self).unlink(cr, uid, ids, context=context)

    def _get_configuration_id(self, cr, uid, ids, context=None):
        ''' Returns the-only-one configuration to be used with the packaging.
        '''
        return self.pool.get('configuration.data').get(cr, uid, ids, context=context).id

    _columns = {
        'configuration_id': fields.many2one('configuration.data', 'Configuration Data', required=True),
        'name': fields.char('Name', required=True, select=True, help='The name of the package type.'),
    }

    _defaults = {
        'configuration_id': _get_configuration_id,
    }

    _sql_constraints = [
        ('uniq_configuration_packaging_type',
         'UNIQUE(configuration_id, name)',
         'A given configuration can not have duplicated packaging types.'),
    ]

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
