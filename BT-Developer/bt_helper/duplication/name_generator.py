# b-*- encoding: utf-8 -*-
##############################################################################
#
#    Copyright (c) 2010 brain-tec AG (http://www.brain-tec.ch) 
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


logger = logging.getLogger(__name__)
# logger.setLevel(logging.DEBUG)
logger.setLevel(logging.INFO)
# logger.setLevel(logging.WARNING)
# logger.setLevel(logging.ERROR)
# logger.setLevel(logging.NOTSET)

try:
    import rstr
except ImportError:
    logger.debug('For an additional feature of generating name of bt_helper,please, install Python library rstr: pip install rstr')



class name_generator(osv.osv):
    _name = 'bt_helper.name_generator'
    _description = 'BT Helper Name Generator'

    _columns = {
        'name': fields.char('Generator name', size=64, required=True),
        'python_code': fields.text('Python code', required=True,),
    }

    def _gen_value_partner(self, cr,uid,res_id, model, field, old_value, obj, globals_dict):
        if model == 'res.partner':
            if field == 'lastname':
                old_value = old_value.replace('(copy)','')
                return old_value+' '+eval(str(obj.python_code), globals_dict=globals_dict)
            if field == 'firstname':
                return old_value+' '+eval(str(obj.python_code), globals_dict=globals_dict)
            elif field == 'street':
                if (old_value.split()[-1]).isdigit():
                    old_value = old_value.replace(old_value.split()[-1], eval(str(obj.python_code),globals_dict=globals_dict)) 
                    return old_value
            elif field == 'email':
                email = old_value.split('@')
                return email[0]+'.'+eval(str(obj.python_code),globals_dict=globals_dict)+'@'+email[1]
            elif field == 'phone':
                country = self.pool.get(model).read(cr,uid,res_id,['country_id'])['country_id']
                if country and country[0] == 44: # Swiss phone
                    return rstr.xeger("^(\+41) \d{2} \d{3} \d{2} \d{2}$")
                else:
                    old_value = old_value.replace(old_value.split()[-1],eval(str(obj.python_code),globals_dict=globals_dict))
                    return old_value

    def gen_value(self, cr, uid, ids, model, field, res_id, context=None):
        '''
        It generates a new value based on Python Code.
        -- We introduce an object:
             model (@model),
             field (@field),
             id (@res_id)
        -- We make a browse of the object and get the current value of the field.
        -- A python function is called and generates a new value for this field.
        @param model: Represents the model that we are going to use
                      for generating the values.
                      If model == 'res.partner' extra functionality is included.
        @type model: ir.model (Str)
        @param field: Name of the field that will be use for generating new code.
        @type field: ir.field (Str)
        @param res_id:
        @type res_id:
        @rtype: The computed new value. If with the input data we do not have 
                a source value, then we return False.
        '''
        if context is None:
            context = {}
        if not isinstance(ids, list):
            ids = [ids]

        obj = self.browse(cr, uid, ids[0], context)
        globals_dict = {'rstr': rstr,
                        'self': self,
                        'cr': cr,
                        'uid': uid,
                        'ids': ids,
                        'context': context,
                        'MODEL': model,
                        'FIELD': field,
                        'RES_ID': res_id}
        # Get the old value.
        # If it does not exists => We return False.
        old_value = False
        try:
            old_value = self.pool.get(model).read(cr,
                                                  uid,
                                                  res_id,
                                                  [field])[field]
        except:
            pass

        if not old_value:
            return old_value

        if model == 'res.partner':
            return self._gen_value_partner(cr,
                                           uid,
                                           res_id,
                                           model,
                                           field,
                                           old_value,
                                           obj,
                                           globals_dict)

        return eval(str(obj.python_code), globals_dict=globals_dict)