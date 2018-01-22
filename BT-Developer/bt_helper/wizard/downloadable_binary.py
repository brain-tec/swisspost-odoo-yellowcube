# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>).
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

from osv import osv, fields
from tools.translate import _


class downloadable_binary(osv.osv_memory):
    '''Use this wizard to allow the user to download a binary file generated on the fly by some
    action.

    Example of usage within a button's function:

        def do_generate_file(...):
            # Generate the binary and decide the name of the file
            binary = 'some sample text'.encode('base64')
            binary_name = 'Sample.txt'

            downloadable_binary_obj = self.pool.get('downloadable.binary')

            # Create an instance of the wizard, providing the binary and the binary name (= file name)
            wizard_id = downloadable_binary_obj.create(cr, uid, {'binary': binary,
                                                                 'binary_name': binary_name})

            # Return the action that will open the wizard just created
            return downloadable_binary_obj.get_returnable_dict(wizard_id, 'TXT File')
    '''

    _name = 'downloadable.binary'
    _description = 'Allows downloading a binary file'

    _columns = {
        'binary': fields.binary(_('File to Download'), readonly=True),
        'binary_name': fields.char(_('File Name'), size=128),
    }

    def get_returnable_dict(self, wizard_id, title=False):
        return {
                'type': 'ir.actions.act_window',
                'res_model': 'downloadable.binary',
                'name': title or _('File to Download'),
                'res_id': wizard_id,
                'view_type': 'form',
                'view_mode': 'form',
                'target': 'new',
        }

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
