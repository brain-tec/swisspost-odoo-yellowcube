# b-*- encoding: utf-8 -*-
##############################################################################
#
#    Copyright (c) 2014 brain-tec AG (http://www.brain-tec.ch)
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


class ir_attachment_ext(osv.Model):
    _inherit = 'ir.attachment'

    def assure_filestore_system_parameter(self, cr, uid, ids=None, context=None):
        ''' Assures the existance of the system's parameter ir_attachment.filestore.
            If it does not exist, creates it.
        '''
        if context is None:
            context = {}

        ir_config_parameter_obj = self.pool.get('ir.config_parameter')
        if not ir_config_parameter_obj.get_param(cr, uid, 'ir_attachment.location'):
            ir_config_parameter_obj.set_param(cr, uid, 'ir_attachment.location', 'file:///filestore')

        return True

    def export_to_xml(self, cr, uid, ids, context):
        TEMPLATE = """
                    <document>
                        <name>{name}</name>
                        <datas_fname>{datas_fname}</datas_fname>
                        <path>{store_fname}</path>
                        <res_name>{res_name}</res_name>
                    </document>
                    """
        result = ""
        for elem in self.read(cr, uid, ids, ['name', 'datas_fname', 'store_fname', 'res_name']):
            result += TEMPLATE.format(name=elem['name'],
                                      datas_fname=elem['datas_fname'],
                                      store_fname=elem['store_fname'],
                                      res_name=elem['res_name'],
                                      )

        return result

    def _sel_get_document_type(self, cr, uid, context=None):
        ''' - Returns the list of possible values for the selection field which indicates
              the documen- type of the attachment.
            - The idea is that this method is extended so that the list of types increases.
            - EVERY TIME this method is extended, the field 'docout_file_type' must be redefined
              to assure the recalculation of the list of options.
        '''
        ret = [('invoice_report', 'Invoice Report'),
               ('picking_out_report', 'Picking Out Report'),
               ]
        return ret

    def __sel_get_document_type(self, cr, uid, context=None):
        return self._sel_get_document_type(cr, uid, context)

    _columns = {
        'document_type': fields.selection(__sel_get_document_type, 'Document Type',
                                          help='Helps categorise the attachment.'),
    }

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
