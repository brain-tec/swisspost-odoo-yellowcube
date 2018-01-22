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
from openerp.tools.translate import _
import time
import random
import logging
logger = logging.getLogger(__name__)
# logger.setLevel(logging.DEBUG)
logger.setLevel(logging.WARNING)
# logger.setLevel(logging.WARNING)
# logger.setLevel(logging.ERROR)
# logger.setLevel(logging.NOTSET)

class duplicate_model(osv.osv):
    _name = 'bt_helper.duplicate_model'
    _columns = {
        'model_id': fields.many2one('ir.model', 'Model', required=True),
        'num_repetitions': fields.integer('Number of repetitions',
                                          required=True,
                                          help="Number of times to make a new record")
    }

    def duplicate_entries_model(self, cr, uid, ids, context=None):
        '''
        Action to duplicate entries
            a) Get the model of ir.model.
        '''
        logger.warning("This method is deprecated! Do not use it")
        if context is None:
            context = {}
        if not isinstance(ids, list):
            ids = [ids]
        if not ids:
            return
        ir_model_mod = self.pool.get('ir.model')
        for duplicate_model in self.browse(cr, uid, ids, context=context):

            ir_model = ir_model_mod.read(cr,
                                         uid,
                                         duplicate_model.model_id.id,
                                         context=context)
            if not ir_model:
                continue
            model_name = ir_model.model
            object_ids = self.pool.get(model_name).search(cr, uid, [('customer','=',True)])
            partner_ids = random.sample(object_ids, len(object_ids))
            print partner_ids
            num_repetitions = self.read(cr, uid, ids[0], ['num_repetitions'])['num_repetitions']

            partner_ids = [x for x in partner_ids if x < 812]
            partner_obj = self.pool.get(model_name)


            for rep in range(1,num_repetitions+1):
                time_total = 0.0
                for partner in partner_ids:

                    cr = self.pool.db.cursor()
                    #cr._cnx.set_isolation_level(ISOLATION_LEVEL_READ_COMMITTED)
                    t1 = time.time()
                    try:
                        partner_obj.copy(cr,uid,partner)
                    except:
                        cr.close()
                        continue
                    cr.commit()
                    

                    print str(partner) +' '+ str(rep) + '- Total Time:' + str(time.time() - t1) + " seconds"
                    time_total = time_total+ (time.time() - t1)
                    cr.close()
                print 'Total Time Rep' + str(rep) + ' : '+ str(time_total) + " seconds"


        return True
