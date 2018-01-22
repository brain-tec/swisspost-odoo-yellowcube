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


class config_setting_ext(osv.osv_memory):

    _name = 'config.setting.ext'

    def stock_default_config_setup(self, cr, uid, ids=None, context=None):
        stock_settings_obj = self.pool.get('stock.config.settings')
        values = {"group_stock_production_lot": True,
                  "group_stock_tracking_lot": True,
                  "group_stock_multiple_locations": True,
                  "group_uom": True,
                  }

        stock_settings_id = stock_settings_obj.create(cr, uid, values, context=context)
        stock_settings = stock_settings_obj.browse(cr, uid, stock_settings_id, context=context)
        stock_settings.execute()  # This calls the wizard method to apply the new configuration.
        return True


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
