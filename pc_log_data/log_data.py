# b-*- encoding: utf-8 -*-
##############################################################################
#
#    Copyright (c) 2014 brain-tec AG (http://www.braintec-group.com)
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


class log_data(osv.Model):
    """ Table used for logging import/export actions,
        whether they are successful, or not.

        Copied from bt_helper of repository BT-Developer by brain-tec AG.
    """
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


def write_log(delegate, cr_original, uid, table_name, object_name,
              object_id, information, correct=True, extra_information='',
              context=None):
    """
    This method creates a log entry, based on the filters defined for an specific table,
    and if such table does not have a related filter, a default one will be created.

    @param delegate: object with pool variable that called this method
    @type delegate: osv.Model
    @param cr_original: original cursor used by the delegate object
    @type cr_original: cursor
    @param uid: user ID
    @type uid: integer
    @param table_name: name of the table that is related to this log
    @type table_name: string
    @param object_name: identifier name of the related object
    @type object_name: string
    @param information: description of the log entry
    @type information: string
    @param correct: is the log entry for a correct behaviour?
    @type correct: Boolean
    @param extra_information:addiional information about this log entry
    @type extra_information: string

    @return: True

    Copied from bt_helper of repository BT-Developer by brain-tec AG.
    """
    filter_obj = delegate.pool.get('log.data.filter')
    model_obj = delegate.pool.get('ir.model')
    cr = delegate.pool.db.cursor()
    model_ids = model_obj.search(cr, uid, [('model', '=', table_name)])
    filter_id = filter_obj.search(cr, uid, [('model_id', 'in', model_ids)])
    if context is None:
        context = {}
    if not filter_id:
        # logger.debug("Filter does not exist for class {0}".format(table_name))
        if not filter_obj.search(cr, uid, [('model_id', 'in', model_ids)]):
            # logger.warning("This model does not contain a filter: {0}".format(model_ids[0]))
            filter_obj.create(cr, uid, {'model_id': model_ids[0]})
        cr.commit()
        cr.close()
        return True

    var_filter = filter_obj.browse(cr, uid, filter_id)[0]
    if correct and var_filter.log_normal_execution or not correct and var_filter.log_error:
        data = {
            'model_id': var_filter.model_id.id,
            'model_name': var_filter.model_id.name,
            'table_name': table_name,
            'object_name': object_name,
            'ref_id': object_id,
            'information': str(information),
            'correct': correct,
            'extra_information': str(extra_information)
        }
        delegate.pool.get('log.data').create(cr, uid, data,
                                             context=context)

    cr.commit()
    cr.close()
    return True

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
