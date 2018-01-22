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

from openerp.osv import orm, osv, fields
from openerp.tools.translate import _


class stock_connect_ext(osv.Model):
    _inherit = 'stock.connect'

    def get_event_codes_to_ignore(self, cr, uid, ids, context=None):
        """ Returns the list of event_code to ignore AND mark as ignored.
        """
        if context is None:
            context = {}
        if type(ids) is not list:
            ids = [ids]

        this = self.browse(cr, uid, ids[0], context=context)
        if this.type == 'external_email':
            ret = [
                'new_picking_state_draft',
                'new_picking_state_auto',
                'new_picking_state_confirmed',
                'new_picking_state_done',
                'new_picking_state_cancel',
                'warehouse_connection_set',
            ]
        else:
            ret = super(stock_connect_ext, self).get_event_codes_to_ignore(
                cr, uid, ids, context=context)
        return ret

    def open_action_mail(self, cr, uid, ids, context=None):
        if context is None:
            context = {}

        return {
            'type': 'ir.actions.act_window',
            'res_model': 'mail.mail',
            'domain': [['stock_connect_id', 'in', ids]],
            'view_mode': 'tree,form',
            'context': {'tree_view_ref': 'pc_connect_warehouse_external_email.view_stock_connect_email_tree',
                        'form_view_ref': 'mail.view_mail_form'},
        }

    _columns = {
        'stock_connect_email_ids': fields.one2many('mail.mail', 'stock_connect_id', 'Emails'),
    }

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
