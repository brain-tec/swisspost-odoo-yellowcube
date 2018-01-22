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

from osv import fields, osv
from osv.orm import *
from openerp.tools.translate import _

from bt_helper.log_rotate import get_log
logger = get_log('DEBUG')


class ir_model_data_information(osv.osv):
    _name = 'bt_helper.ir_model_data_information'
    _description = 'BT Helper ir model data information'

    def action_compute(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        if not isinstance(ids, list):
            ids = [ids]
        ir_model_data_mod = self.pool.get('ir.model.data')
        for information in self.browse(cr, uid, ids, context):
            ir_model_data_ids = ir_model_data_mod.search(cr, uid, [])
            max = len(ir_model_data_ids)
            i = 1
            new_ids = []
            for ir_model_data in ir_model_data_mod.browse(cr, uid, ir_model_data_ids, context):

                try:
                    self.pool.get(ir_model_data.model).browse(cr, uid, ir_model_data.res_id).name_get()
                except:
                    new_ids.append(ir_model_data.id)
                logger.debug("Checking {0} / {1}".format(i, max))
                i += 1
            logger.debug("Adding these new_ids {0}".format(new_ids))
            information.write({'ir_model_data_ids': [(4, x) for x in new_ids]})
        return True


    _columns = {
            'name': fields.char('Name', size=64),
            'ir_model_data_ids': fields.many2many('ir.model.data', 'ir_model_data_information_information', 'information_id', 'data_id', 'Missing'),
    }
