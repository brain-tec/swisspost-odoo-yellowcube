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


class wizard_popup(osv.TransientModel):
    _name = 'wizard.popup'

    def default_get(self, cr, uid, fields_list, context=None):
        ret = super(wizard_popup, self).default_get(cr, uid, fields_list, context=context)
        if context is None:
            return ret
        ret.update(context.get('popup', {}))
        return ret

    def show(self, cr, uid, context):
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'wizard.popup',
            'res_id': self.create(cr, uid, {}, context),
            'target': 'new',
            'context': context,
            'view_mode': 'form',
            'name': context.get('popup', {'name': ''})['name']
        }

    _columns = {
        'name': fields.char('Title', readonly=True),
        'desc': fields.text('Description', readonly=True),
    }

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: