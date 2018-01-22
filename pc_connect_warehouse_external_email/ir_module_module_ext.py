from openerp.osv import osv, orm
from openerp.tools.translate import _


class ir_module_module_ext(osv.osv):
    _inherit = 'ir.module.module'

    def button_install(self, cr, uid, ids, context=None):
        ''' Overwritten so that we can prevent pc_connect_warehouse_external_email and
            pc_connect_warehouse_yellowcube at the same time.
        '''
        if context is None:
            context = {}

        if (any(module.name == 'pc_connect_warehouse_yellowcube' for module in self.browse(cr, uid, ids, context=context))):
            raise orm.except_orm(_('Error'), _('The currently installed module pc_connect_warehouse_external_email is incompatible '
                                               'with module pc_connect_warehouse_yellow_cube. Please uninstall this module first.'))

        return super(ir_module_module_ext, self).button_install(cr, uid, ids, context=context)

    def button_immediate_install(self, cr, uid, ids, context=None):
        ''' Overwritten so that we can prevent pc_connect_warehouse_external_email and
            pc_connect_warehouse_yellowcube at the same time.
        '''
        if context is None:
            context = {}

        if (any(module.name == 'pc_connect_warehouse_yellowcube' for module in self.browse(cr, uid, ids, context=context))):
            raise orm.except_orm(_('Error'), _('The currently installed module pc_connect_warehouse_external_email is incompatible '
                                               'with module pc_connect_warehouse_yellow_cube. Please uninstall this module first.'))

        return super(ir_module_module_ext, self).button_immediate_install(cr, uid, ids, context=context)

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
