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

from osv.orm import *
import logging

logger = logging.getLogger(__name__)
# logger.setLevel(logging.DEBUG)
logger.setLevel(logging.INFO)
# logger.setLevel(logging.WARNING)
# logger.setLevel(logging.ERROR)
# logger.setLevel(logging.NOTSET)



import time

old_copy_data = BaseModel.copy_data


def copy_data(self, cr, uid, ids, default={}, context={}):

    duplication_obj = self.pool.get('bt_helper.fields')
    try:
        fields_ids = duplication_obj.search(cr,
                                            uid,
                                            [('model_id', '=', self._name)],
                                            context=context)
    except:
        return old_copy_data(self, cr, uid, ids, default, context)

    for field in duplication_obj.browse(cr, uid, fields_ids, context=context):
        logger.debug('Creating this field by using duplicator', field)
        if field.fields_not_duplicated.name in default and not field.overwrite:
            continue

        if field.set_null:
            default[field.fields_not_duplicated.name] = None
        else:
            if field.type == 'char':
                default[field.fields_not_duplicated.name] = field.default_value
            elif field.type == 'boolean':
                default[field.fields_not_duplicated.name] = bool(field.default_value)
            elif field.type == 'float':
                default[field.fields_not_duplicated.name] = float(field.default_value)
            elif field.type == 'regular_expression':
                logger.warning("Field.type = regular_expression is deprecated! Do not use it")
                default[field.fields_not_duplicated.name] = field.name_generator_id.gen_value(field.model_id.model,field.fields_not_duplicated.name,ids)

    return old_copy_data(self, cr, uid, ids, default, context)

BaseModel.copy_data = copy_data
