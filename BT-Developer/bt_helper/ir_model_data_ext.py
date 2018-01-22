# b-*- encoding: utf-8 -*-
##############################################################################
#
#    Copyright (c) 2015 brain-tec AG (http://www.brain-tec.ch)
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
from osv import osv, fields
from openerp import netsvc
from openerp.tools import ustr
import sys
import openerp.pooler as pooler
from log_rotate import get_log
logger = get_log()


class ir_model_data_ext(osv.osv):
    _inherit = 'ir.model.data'

    def _update(self, cr, uid, model, module, values, xml_id=False, store=True, noupdate=False, mode='init', res_id=False, context=None):
        '''
        In order to be able to add \n in xml.
        Bugfixed => Now we can write expressions like this in the context...
        '''
        if xml_id:
            xml_id = xml_id.strip()
        for value in values:
            try:
                values[value] = values[value].strip()
            except:
                pass
        return super(ir_model_data_ext, self)._update(cr, uid, model, module, values, xml_id, store, noupdate, mode, res_id, context)

    _columns = {
        'name': fields.char('External Identifier', required=True, size=256, select=1,
                            help="External Key/Identifier that can be used for "
                                 "data integration with third-party systems"),

    }

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
