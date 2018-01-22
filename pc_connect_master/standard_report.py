# b-*- encoding: utf-8 -*-
##############################################################################
#
#    Copyright (c) 2015 brain-tec AG (http://www.braintec-group.com)
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
from openerp.osv import osv, fields, orm
from openerp.tools.translate import _
from datetime import datetime
from dateutil import relativedelta
from openerp.addons.base.ir.ir_model import _get_fields_type


class standard_report(osv.Model):
    _name = 'report.file'

    def export_file(self, cr, uid, ids, context=None):
        """
        This method creates a report using the best technique for the kind of data to represent

        If an aggregate function is required, data will be gathered using SQL.
        """
        ctx = {} if context is None else context.copy()

        export_obj = self.pool.get('report.file.exporter')

        if type(ids) is not list:
            ids = [ids]

        report = self.browse(cr, uid, ids, ctx)[0]
        if not report.domain:
            report.domain = report.fitler_id.domain
        # The filter may impose some context info, that must be kept
        if report.filter_id:
            ctx.update(eval(report.filter_id.context))
        # The report generator requires a target model
        ctx['active_model'] = report.model_id.model
        if report.sql:
            # In case we use sql, we pass the sentence by context, and an array of model names
            #  for id translation into names
            ctx['sql'] = report.sql
            ctx['models'] = {}
            pos = 0
            for field in report.fields:
                if field.model_name and field.sql_search:
                    ctx['models'][pos] = field.model_name
                elif not field.field_id:
                    ctx['models'][pos] = report.model_id.model
                pos += 1

        # here we computethe domain to used, based on the filter
        domain = []
        _globals = globals().copy()
        _globals['context_today'] = datetime.today
        _globals['relativedelta'] = relativedelta.relativedelta
        str_domain = report.domain
        for part in eval(str_domain, _globals):
            if type(part) is list:
                left_leaf = part[0]
                operator = part[1]
                right_leaf = part[2]
                if type(right_leaf) is list:
                    right_leaf = tuple(right_leaf)
                domain.append((left_leaf, operator, right_leaf))
            else:
                domain.append(part)

        # The resulting ids are obtained by a search, so access rules are applied
        ctx['active_ids'] = self.pool.get(ctx['active_model']).search(cr, uid, domain, context=ctx)

        # Here we get the standard odoo name of the fields, and the labels to show
        ctx['var_fields'] = []
        ctx['var_fields_label'] = []
        for field in report.fields:
            t = field.field_id and field.field_id.field_description or 'ID'
            if not field.field_id:
                ctx['var_fields'].append('id')
            elif field.field_id2:
                ctx['var_fields'].append('{0}/{1}'.format(field.field_id.name, field.field_id2.name))
                t = '{0}: {1}'.format(t, field.field_id2.field_description)
            else:
                ctx['var_fields'].append(field.field_id.name)

            if field.groupby:
                ctx['var_fields_label'].append('{0} ({1})'.format(t, field.groupby))
            else:
                ctx['var_fields_label'].append(t)

        # The wizard will create the report, and show the download pop-up
        wiz_id = export_obj.create(cr, uid, {'file_ext': report.file_type}, ctx)
        return export_obj.export_report(cr, uid, wiz_id, ctx)

    def fill_fields(self, cr, uid, ids, context=None):
        """
        This method applies an heuristic of most common fields for a report, based on required fields
         and those that appear in the group-by (if any)
        """
        if context is None:
            context = {}

        if type(ids) is list:
            ids = ids[0]

        report = self.browse(cr, uid, ids, context)
        if report.fields:
            # For this, the report must be a draft
            raise orm.except_orm("fields", _("Cannot add fields, once fields are added"))

        if not report.filter_id:
            # For this, the report must have a selected domain
            raise orm.except_orm("filter_id", _("Missing filter data"))

        # We include id (empty field) as a default field
        fields = [{'field_id': None}]
        fields_obj = self.pool.get('ir.model.fields')
        report_field_obj = self.pool.get('report.file.fields')

        for fid in fields_obj.search(cr, uid, [('required', '=', True), ('model_id', '=', report.model_id.id)], context=context):
            fields.append({'field_id': fid})

        # If group_by we add those fields
        if 'group_by' in report.filter_id.context:
            # First, we move the aggregate fields to last position
            order_pos = 1000
            for f in fields:
                # count is a safe aggregate. User must select the one he wants
                f['groupby'] = 'count'
                f['order_priority'] = order_pos
                order_pos += 1
            order_pos = 1
            for x in eval(report.filter_id.context)['group_by']:
                fields.append({
                    'order_priority': order_pos,
                    'field_id': fields_obj.search(cr, uid, [('name', '=', x), ('model_id', '=', report.model_id.id)], context=context)[0]
                })
                order_pos += 1

        ret_fields = []
        for f in fields:
            f['report_id'] = ids
            ret_fields.append(report_field_obj.create(cr, uid, f, context))

        return

    def onchange_filter(self, cr, uid, ids, filter_id, field_ids, name, context=None):
        if field_ids:
            raise orm.except_orm("fitler_id", _("Cannot change filter, once fields are selected"))

        if not filter_id:
            return {'value': {'model_id': False, 'domain': False}}

        vals = self.pool.get('ir.filters').read(cr, uid, filter_id, ['name', 'model_id', 'context', 'domain'], context)
        if not name:
            name = vals['name']

        model_id = self.pool.get('ir.model').search(cr, uid, [('model', '=', vals['model_id'])], context=context)[0]

        return {'value': {
            'model_id': model_id,
            'domain': vals['domain'],
            'name': name,
        }}

    def _get_sql(self, cr, uid, ids, field='sql', arg=None, context=None):
        """
        This method creates an sql query for group-by reports
        """
        ret = {}
        for report in self.browse(cr, uid, ids, context):
            # group-by elements
            group = []
            # columns an their final names
            select = []
            # inner join sentences
            inner = []
            needs_sql = False
            for field in report.fields:
                if not field.sql_search:
                    select.append('\'ignored\' as "{0}"'.format(field.field_id.field_description))
                else:
                    text = field.sql_name
                    if field.groupby:
                        select.append(text.format('{0}( '.format(field.groupby), ' )'))
                        # if there is at least one group-by, we must use SQL
                        needs_sql = True
                    else:
                        text = text.format('', '')
                        select.append(text)
                        group.append(text.split(' ')[0])
                    if field.sql_join and field.sql_join not in inner:
                        inner.append(field.sql_join)
            _from = report.model_id.name
            if not needs_sql:
                # We only use SQL if it is a must (standard odoo is better. e.g. i18n)
                ret[report.id] = None
                continue
            select = ',\n\t'.join(select)
            _from = report.model_id.model.replace('.', '_')
            where = 'WHERE id.id in ({ids})'
            group = ', '.join(group)
            if inner:
                where = '{0}\n{1}'.format('\n'.join(inner), where)
            ret[report.id] = 'SELECT\n\t{0}\nFROM {1} as id\n{2}\nGROUP BY {3}\nORDER BY {3};'.format(select,
                                                                                                      _from,
                                                                                                      where,
                                                                                                      group)
        return ret

    def get_script(self, cr, uid, ids, field_name=None, arg=None, context=None):
        """
        This method serializes the report fields, in a syntax easier to upload by xml

        Format:
        model_name
        # <-- This for inline comments
        field(/sub-field)? (aggregate)?
        ...
        field(/sub-field)? (aggregate)?
        """
        ret = {}
        for report in self.browse(cr, uid, ids, context):
            fields = [report.model_id.model]
            for f in report.fields:
                # field1, field2, aggregate
                t = f.field_id and f.field_id.name or 'id'
                if f.field_id2:
                    t = '{0}/{1}'.format(t, f.field_id2.name)
                if f.groupby:
                    t = '{0} {1}'.format(t, f.groupby)
                fields.append(t)
            ret[report.id] = '\n'.join(fields)
        return ret

    def set_script(self, cr, uid, ids, name, value, fnct_inv_arg, context=None):
        """
        This method de-serializes the report fields, in a syntax easier to upload by xml
        (priority is set by orderin the script)

        Format:
        model_name
        # <-- This for inline comments
        field(/sub-field)? (aggregate)?
        ...
        field(/sub-field)? (aggregate)?
        """
        if not value:
            return
        if type(ids) is not list:
            ids = [ids]
        fields_obj = self.pool.get('ir.model.fields')
        report_fields_obj = self.pool.get('report.file.fields')
        for report in self.browse(cr, uid, ids, context):
            lines = value.split('\n')
            model = lines[0]
            pos = 0
            fields_to_remove = [x.id for x in report.fields]
            report_fields_obj.unlink(cr, uid, fields_to_remove, context)
            for line in lines[1:]:
                try:
                    if not line or not(line.strip()) or line.strip()[0] == '#':
                        continue
                    line = line.strip().split(' ')
                    if line[0]:
                        pos += 10
                        order = pos
                        group_by = None
                        if len(line) > 1:
                            group_by = line[1]
                        line = line[0].split('/')
                        if line[0] != 'id':
                            field_id = fields_obj.search(cr, uid, [('model', '=', model), ('name', '=', line[0])], context=context)[0]
                            field_id2 = None
                            if len(line) > 1:
                                rel = fields_obj.read(cr, uid, [field_id], ['relation'], context=context)[0]['relation']
                                field_id2 = fields_obj.search(cr, uid, [('model', '=', rel), ('name', '=', line[1])], context=context)[0]
                        else:
                            field_id2 = field_id = None
                        vals = {'report_id': report.id,
                                'order_priority': order,
                                'field_id': field_id,
                                'field_id2': field_id2,
                                'groupby': group_by}
                        report_fields_obj.create(cr, uid, vals, context=context)
                except Exception as e:
                    raise orm.except_orm(line, e)
        return

    _columns = {
        'name': fields.char('Report profile name', required=True),
        'model_id': fields.many2one('ir.model', string="Table to export", required=True),
        'file_type': fields.selection([('csv', 'Comma-separated'), ('xlsx', 'Spreadsheet')], string="File format", required=True),
        'filter_id': fields.many2one('ir.filters', string="Filter for search", required=False),
        'domain': fields.char("Search domain", required=False),
        'fields': fields.one2many('report.file.fields', 'report_id', string="Fields", required=False, ondelete="cascade"),
        'sql': fields.function(_get_sql, string='Group-by SQL statement', type="text", store=False),
        'script': fields.function(get_script, fnct_inv=set_script, string="Fields by script", type="text", store=False),
    }

    _defaults = {
        'file_type': 'csv',
    }


class standard_report_field(osv.Model):
    _name = 'report.file.fields'

    _order = "order_priority ASC"

    def functionals(self, cr, uid, ids, field_name=None, arg=None, context=None):
        """
        This method calculates functional values, and on_change events
        """
        ret = {}

        fields_obj = self.pool.get('ir.model.fields')
        model_obj = self.pool.get('ir.model')

        # Iff call by API
        if arg is None:
            for field in self.browse(cr, uid, ids, context):
                f = field.field_id and field.field_id.id or False
                ret[field.id] = field.functionals(field_name=field_name, arg=f) or None
            return ret

        if field_name == 'sql_name':
            # sql name of the column, and column header
            field = self.browse(cr, uid, ids, context)[0]
            if not field.field_id:
                return '{0}id.id{1} as "{0}ID{1}"'
            if field.field_id2:
                return '{{0}}fk_{0}.{2}{{1}} as "{1}: {{0}}{3}{{1}}"'.format(field.field_id.name,
                                                                             field.field_id.field_description,
                                                                             field.field_id2.name,
                                                                             field.field_id2.field_description)
            else:
                return '{{0}}id.{0}{{1}} as "{{0}}{1}{{1}}"'.format(field.field_id.name,
                                                                    field.field_id.field_description)

        if field_name == 'sql_join':
            # sql inner join required
            field = self.browse(cr, uid, ids, context)[0]
            if field.field_id2:
                if field.field_id.relation_field:
                    return 'INNER JOIN {1} as fk_{0} ON id.id = fk_{0}.{2}'.format(field.field_id.name,
                                                                                   field.field_id.relation.replace('.', '_'),
                                                                                   field.field_id.relation_field)
                else:
                    return 'INNER JOIN {1} as fk_{0} ON id.{0} = fk_{0}.id'.format(field.field_id.name,
                                                                                   field.field_id.relation.replace('.', '_'))
            else:
                return None

        if field_name == 'model_name':
            # Model this field represents (only for ids)
            field = self.browse(cr, uid, ids, context)[0]
            if field.groupby:
                return None
            f = field.field_id2 or field.field_id
            if not f:
                return None
            return f.relation or None

        # Else, by on_change

        if arg:
            # arg must be a ir.model.fields id number
            field = fields_obj.browse(cr, uid, arg, context)
            ret['field_id2'] = None
            ret['ttype'] = field.ttype
            ret['model_id'] = field.relation and model_obj.search(cr, uid, [('model', '=', field.relation)], context=context)[0] or None

        if ret:
            if field_name:
                return ret.get(field_name, None)
            else:
                return {'value': ret}
        else:
            return {}

    def _sql_search(self, cr, uid, ids, field="sql_search", args=None, context=None):
        """
        Check for reachability of fields through SQL.
        (non-functionals and store=True)
        """
        ret = {}
        for field in self.browse(cr, uid, ids, context):
            ret[field.id] = True
            try:
                cr.execute("SAVEPOINT field_test;")
                cr.execute('SELECT {0} FROM {2} as id {1} LIMIT 0;'.format(field.sql_name.format('', ''), field.sql_join or '', field.report_id.model_id.model.replace('.', '_')))
                cr.fetchall()
            except:
                ret[field.id] = False
            finally:
                cr.execute("ROLLBACK TO field_test;")
        return ret

    _columns = {
        'order_priority': fields.integer('Field order'),
        'report_id': fields.many2one('report.file', string="Report", required=True, ondelete="cascade"),
        'field_id': fields.many2one('ir.model.fields', string="Field", required=False),
        'field_id2': fields.many2one('ir.model.fields', string="Sub-field", required=False),
        'groupby': fields.selection([('max', 'MAX'), ('min', 'MIN'), ('sum', 'SUM'), ('count', 'COUNT'), ('avg', 'AVERAGE')], string="group-by action", required=False),
        # Functional fields
        'sql_search': fields.function(_sql_search,
                                      string="SQL searchable",
                                      type="boolean",
                                      store=False,
                                      readonly=True),
        'sql_name': fields.function(functionals, type="char", string="sql_name", store=False),
        'sql_join': fields.function(functionals, type="char", string="sql_join", store=False),
        'model_name': fields.function(functionals, type="char", string="model_name", store=False),
        'ttype': fields.function(functionals, type="selection", selection=_get_fields_type, string='Field Type', store=False),
        'model_id': fields.function(functionals, type="many2one", relation='ir.model', string="Relation", store=False),
    }

    def _defaults_order_priority(self, cr, uid, context=None):
        max_id = 0
        if context and 'active_id' in context:
            report = self.pool.get('report.file').browse(cr, uid, context['active_id'], context)
            for f in report.fields:
                if f.order_priority > max_id:
                    max_id = f.order_priority
        return max_id + 10

    _defaults = {
        'groupby': None,
        'order_priority': _defaults_order_priority,
    }

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
