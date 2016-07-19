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

from openerp.osv import osv, orm
from openerp.tools.translate import _


class ir_module_module_ext(osv.osv):
    _inherit = 'ir.module.module'

    def module_uninstall(self, cr, uid, ids, context=None):
        ''' Overwritten so that if the module pc_product_lifecycle is uninstalled,
            then the flag yc_enable_product_lifecycle is unchecked also.
        '''
        if context is None:
            context = {}

        if any(m.name == 'pc_product_lifecycle' for m in self.browse(cr, uid, ids, context=context)):
            stock_connect_obj = self.pool.get('stock.connect')
            stock_connect_ids = stock_connect_obj.search(cr, uid, [], context=context)
            stock_connect_obj.write(cr, uid, stock_connect_ids,
                                    {'yc_enable_product_lifecycle': False}, context=context)

        return super(ir_module_module_ext, self).module_uninstall(cr, uid, ids, context)

    def button_install(self, cr, uid, ids, context=None):
        ''' Overwritten so that we can prevent pc_connect_warehouse_external_email and
            pc_connect_warehouse_yellowcube at the same time.
        '''
        if context is None:
            context = {}

        if (any(module.name == 'pc_connect_warehouse_external_email' for module in self.browse(cr, uid, ids, context=context))):
            raise orm.except_orm(_('Error'), _('The currently installed module pc_connect_warehouse_yellowcube is incompatible '
                                               'with module pc_connect_warehouse_external_email. Please uninstall this module first.'))

        return super(ir_module_module_ext, self).button_install(cr, uid, ids, context=context)

    def button_immediate_install(self, cr, uid, ids, context=None):
        ''' Overwritten so that we can prevent pc_connect_warehouse_external_email and
            pc_connect_warehouse_yellowcube at the same time.
        '''
        if context is None:
            context = {}

        if (any(module.name == 'pc_connect_warehouse_external_email' for module in self.browse(cr, uid, ids, context=context))):
            raise orm.except_orm(_('Error'), _('The currently installed module pc_connect_warehouse_yellowcube is incompatible '
                                               'with module pc_connect_warehouse_external_email. Please uninstall this module first.'))

        return super(ir_module_module_ext, self).button_immediate_install(cr, uid, ids, context=context)

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
