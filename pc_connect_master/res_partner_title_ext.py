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

from openerp.osv import osv


class res_partner_title_ext(osv.Model):
    _inherit = 'res.partner.title'

    def keep_only_mister_and_madam_titles(self, cr, uid, context=None):
        ''' If the client has indicated that he/she does not want
            the default res.partner.title that comes with the core,
            but only Mister and Madam, then in each update it removes
            all those res.partner.title which are not those two.
        '''
        if context is None:
            context = {}

        configuration_data = self.pool.get('configuration.data').get(cr, uid, [], context=context)

        if configuration_data.keep_only_mister_and_madam_titles:
            # Searches for the IDs corresponding to Mister and Madam,
            # because we are going to keep only those ones.
            ir_model_data_obj = self.pool.get('ir.model.data')
            mister_object_reference = ir_model_data_obj.get_object_reference(cr, uid, 'base', 'res_partner_title_mister')
            madam_object_reference = ir_model_data_obj.get_object_reference(cr, uid, 'base', 'res_partner_title_madam')
            titles_to_keep_ids = []
            if mister_object_reference:
                titles_to_keep_ids.append(mister_object_reference[1])
            if madam_object_reference:
                titles_to_keep_ids.append(madam_object_reference[1])

            titles_to_remove_ids = self.search(cr, uid, [('id', 'not in', titles_to_keep_ids),
                                                         ('domain', '=', 'contact'),
                                                         ], context=context)
            self.unlink(cr, uid, titles_to_remove_ids, context=context)

        return True

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
