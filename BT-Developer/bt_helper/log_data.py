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
from bt_helper.log_rotate import get_log
import sys
logger = get_log("DEBUG")
from openerp import SUPERUSER_ID
import traceback


class log_data(osv.Model):
    '''
    Table used for logging import/export actions, whatever they are successful, or not
    '''
    _name = 'log.data'
    _description = "Log Data"
    _order = 'create_date'

    def create(self, cr, uid, values, context=None):
        if context is None:
            context = {}
        ret = super(log_data, self).create(cr, uid, values, context=context)
        correct = values['correct']
        model_name = values['model_name']
        table_name = values['table_name']
        ref_id = values['ref_id']
        body = """<b>{type}</b>
        <br/>
        {model}#{id} [{name}]
        <br/>
        {info}
        <br/>
        <i>{extra}</i>
        """.format(type='Correct execution' if correct else 'Error on execution',
                   model=model_name,
                   id=ref_id,
                   name=values['object_name'],
                   info=values['information'].replace('\n', '<br/>'),
                   extra=values['extra_information'].replace('\n', '<br/>')
                   )
        context['thread_body'] = body
        if context.get('thread_model', None) is None and table_name is 'ir.cron' and context.get('thread_id', None) is None:
            context['thread_model'] = 'ir.cron'
            context['thread_id'] = ref_id
        if 'thread_id' in context:
            self.pool.get(context.get('thread_model', 'mail.thread')).message_post(cr, uid, context['thread_id'], body=body)

        return ret

    def name_get(self, cursor, uid, ids, context=None):
        res = []
        for var_log_data in self.browse(cursor, uid, ids, context=context):
            res.append((var_log_data.id, var_log_data.model_id.name))
        return res

    _columns = {
        'model_id': fields.many2one('ir.model', 'Model', required=True),
        'object_name': fields.text('Object name', required=False),
        'information': fields.text('Information', required=True),
        'extra_information': fields.text('Extra Information', required=True),
        'ref_id': fields.integer('Ref ID'),
        'create_date': fields.datetime('Create Date', select=True),
        'create_uid': fields.many2one('res.users', 'Create UID'),
        'write_uid': fields.many2one('res.users', 'Write UID'),
        'write_date': fields.datetime('Write Date', select=True),

        'active': fields.boolean('Active', required=True),
        'correct': fields.boolean('Correct execution', required=True),
    }
    _defaults = {
        'correct': True,
        'active': True
    }

    def unlink(self, cr, uid, ids, context=None, check=True):
        self.pool.get('log.data').write(cr, uid, ids, {'active': False})
        return True

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
