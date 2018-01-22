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

import pytz
from openerp.osv import osv, fields, orm
from openerp.tools.translate import _


class configuration_data(osv.Model):
    _name = "configuration.data"

    def get_available_timezones(self, cr, uid, context=None):
        ''' The server uses UTC+0 to work internally, but the user lives within a time-zone which may not be UTC+0.
            This function returns the fields of a selection field which is used by the user to select his/ser timezone.
        '''
        selection_timezones = []
        for timezone in pytz.all_timezones:
            selection_timezones.append((timezone, timezone))
        return selection_timezones

    def raise_error(self):
        raise orm.except_orm(_("Can't touch this"), _("You can't create/duplicate/remove this record"))

#     def default_get(self, cr, uid, fields, context=None):
#         self.raise_error()

    def unlink(self, cr, uid, ids, context=None):
        self.raise_error()

    def copy(self, cr, uid, ids, defaults, context=None):
        self.raise_error()

#     def create(self, cr, uid, values, context=None):
#         self.raise_error()

    def get(self, cr, uid, ids, context=None):
        return self.pool.get('ir.model.data').get_object(cr, uid, 'pc_config', 'default_configuration_data', context=context)

    def open(self, cr, uid, ids, context=None):
        return {
            'name': _('Configuration Data'),
            'context': context,
            'view_type': 'form',
            'view_mode': 'form,tree',
            'res_model': 'configuration.data',
            'res_id': self.pool.get('ir.model.data').get_object_reference(cr, uid, 'pc_config', 'default_configuration_data')[1],
            'type': 'ir.actions.act_window',
            'target': 'current',
            'multi': 'f',
        }

    def _check_unique_configuration_data(self, cr, uid, part_ids):
        conf_len = self.search(cr, uid, [], count=True)
        if conf_len > 1:
            return False
        return True

    _columns = {
        'name': fields.text('Name', required=True),
        'debug': fields.boolean('Debug mode', help='When possible, debug messages will be shown'),
    }

    _defaults = {
        'debug': False,
    }

    _constraints = [(_check_unique_configuration_data,
                    _('It is not possible to have more than one configuration data'),
                     ['name'])]

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
