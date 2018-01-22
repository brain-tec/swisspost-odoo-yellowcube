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


class fields(osv.osv):
    _name = 'bt_helper.fields'
    _description = 'BT Helper Fields'

    _columns = {
        'model_id': fields.many2one('ir.model', 'Model', required=True),
        'fields_not_duplicated': fields.many2one('ir.model.fields',
                                                 'Field to Modify',
                                                 required=True),

        'type': fields.selection([('regular_expression', 'Regular Expression'),
                                  ('char', 'Char'),
                                  ('text', 'Text'),
                                  ('integer', 'Integer'),
                                  ('float', 'Float'),
                                  ('boolean', 'Boolean'),
                                  ('date', 'Date'),
                                  ('datetime', 'Date Time'),
                                  ('selection', 'Selection'),
                                  ('many2one', 'Many To One'),
                                  ('one2many', 'One To Many'),
                                  ('many2many', 'Many To Many'),
                                  ('binary', 'Binary'),
                                  ], 'Field Type', required=True),
 
        'name_generator_id': fields.many2one('bt_helper.name_generator', 'Default Value Generator'),

        'set_null': fields.boolean('Set Null',
                                   help='''If checked, this field is given value 'null' when duplicating the object.'''),
        'default_value': fields.text('Default Value',),
        'overwrite': fields.boolean('Overwrite', help="If checked this field is given the value resulting from this rule instead of that given as default value."),

    }

    def onchange_field(self, cr, uid, ids, field_id=False, context=None):
        res = {}
        type = self.pool.get('ir.model.fields').read(cr, uid, [field_id], ['ttype'])[0]['ttype']
        res['value'] = {'type': type}
        return res
        

    _defaults = {
        'set_null': False,
        'default_value': '',
        'type': 'char',
        'overwrite': True,
    }

