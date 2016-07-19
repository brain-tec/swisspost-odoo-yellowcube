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
from openerp.osv import osv, fields
from openerp.tools.translate import _
import logging
from openerp import api
logger = logging.getLogger(__name__)

FILE_STATE_DRAFT = 'draft'
FILE_STATE_READY = 'ready'
FILE_STATE_DONE = 'done'
FILE_STATE_CANCEL = 'cancel'


_FILE_STATE = [
    (FILE_STATE_DRAFT, 'Waiting'),
    (FILE_STATE_READY, 'Ready'),
    (FILE_STATE_DONE, 'Finished'),
    (FILE_STATE_CANCEL, 'Ignored'),
]


class stock_connect_file(osv.Model):
    _name = 'stock.connect.file'
    _inherit = 'mail.thread'

    def lock_file(self, cr, uid, ids, context):
        pass

    def unlock_file(self, cr, uid, ids, context):
        pass

    def add_attachment(self, cr, uid, ids, data, filename, context=None):
        if not isinstance(ids, list):
            ids = [ids]
        for _id in ids:
            self.pool.get('ir.attachment').create(cr, uid, {'res_model': 'stock.connect.file',
                                                            'res_id': _id,
                                                            'name': filename,
                                                            'datas_fname': filename,
                                                            'datas': data.encode('base64'),
                                                            }, context)

    def default_get(self, cr, uid, fields_list, context=None):
        ret = super(stock_connect_file, self).default_get(cr, uid, fields_list, context=context)
        for k in ['stock_connect_id', 'warehouse_id']:
            if k in context and k not in ret:
                ret[k] = context[k]
        return ret

    def create(self, cr, uid, vals, context=None):
        if 'related_ids' not in vals:
            if 'model' in vals:
                vals['related_ids'] = ',{0}:{1},'.format(vals['model'],
                                                         vals.get('res_id', ''))
            else:
                vals['related_ids'] = ','
        return super(stock_connect_file, self).create(cr, uid, vals, context=context)

    def write(self, cr, uid, ids, vals, context=None):
        ret = super(stock_connect_file, self).write(cr, uid, ids, vals, context=context)
        if 'model' in vals or 'res_id' in vals:
            for item in self.browse(cr, uid, ids, context=context):
                k = ',{0}:{1},'.format(item.model, item.res_id or '')
                if k not in item.related_ids:
                    item.write({'related_ids': item.related_ids + k[1:]})
        return ret

    def update_related_ids(self, cr, uid):
        pending_ids = self.search(cr, uid, [('related_ids', 'in', [False, ','])])
        for pending in self.browse(cr, uid, pending_ids):
            if pending.model:
                pending.write({'related_ids': ',{0}:{1},'.format(pending.model, pending.res_id or '')})

    def update_priorities(self, cr, uid, model_dict, min_priority, context=None):
        """
        @param model_dict: Dictionary of models and IDs
        @param min_priority: min value of priority to set

        This function sets the priority of any unsent files with a lower priority,
         so they are processed always before than others
        """
        for model in model_dict:
            domain = [
                ('model', '=', model),
                ('priority', '<', min_priority),
                ('state', '!=', FILE_STATE_DONE)
            ]
            object_ids = model_dict[model]
            if object_ids is not None:
                # If the value is None, it means ANY item of the model
                domain.append(('res_id', 'in', model_dict[model]))
            ids = self.search(cr, uid, domain, context=context)
            self.write(cr, uid, ids, {'priority': min_priority}, context=context)

    _columns = {
        'server_ack': fields.boolean("Received Acknowledge", help="By default is True, so special cases can set to False when waiting for ACK"),
        'type': fields.char("Type"),
        'input': fields.boolean("Input file"),
        'create_date': fields.datetime('Create date', required=False),
        'state': fields.selection(_FILE_STATE, 'state', required=True),
        'error': fields.boolean('Stopped by error'),
        'warehouse_id': fields.many2one('stock.warehouse', 'Warehouse', help='Warehouse related to this file', required=False),
        'stock_connect_id': fields.many2one('stock.connect', 'Connection', help='Connection related to this file', required=False),
        'model': fields.char('res.model'),
        'res_id': fields.integer('resource ID'),
        'related_ids': fields.char('related IDs'),
        'name': fields.char('Filename', required=True),
        'binary_content': fields.boolean('Is the content binary?'),
        'content': fields.text('Content', required=False),
        'parent_file_id': fields.many2one('stock.connect.file', 'Parent file', required=False),
        'child_file_ids': fields.one2many('stock.connect.file', 'parent_file_id', 'Child files'),
        'info': fields.text('Info message', required=False),
        'attachments': fields.one2many('ir.attachment', 'res_id', domain=[('res_model', '=', 'stock.connect.file')], string="Binary files"),
        'internal_index': fields.integer('Internal index of a file processed by items', required=False),
        'priority': fields.integer('Priority', required=False),
    }

    _defaults = {
        'state': FILE_STATE_DRAFT,
        'input': False,
        'internal_index': 0,
        'priority': 0,
        'server_ack': True,
    }

    _sql_constraints = [
        ('warehouse_xor_connect',
         'CHECK (warehouse_id <> NULL OR stock_connect_id <> NULL)',
         'It is required to define a related Warehouse, or a related Connection'),
        ('name_uniq', 'unique(name, stock_connect_id)', 'The name of the file must be unique per connection.'),
    ]

    _order = 'priority DESC, name ASC'

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
