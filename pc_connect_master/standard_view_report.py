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
from openerp.osv import osv, fields
from openerp.tools.translate import _
from datetime import datetime
from dateutil import relativedelta
import logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class standard_view_report(osv.Model):
    _name = 'report.view'

    def create_view_reports(self, cr, uid, model_names, context=None):
        """
        For each model in model_names, this method removes all view reports,
         and creates new view reports for them using all search filters (and
         the non filter) with each of the group-by filters (and also the non
         filter).
        """
        model_obj = self.pool.get("ir.model")
        filter_obj = self.pool.get("ir.filters")
        data_obj = self.pool.get('ir.model.data')
        logger.debug("Creating view reports: {0}".format(model_names))
        # First, all view reports will be removed if uncovered
        old_ids = self.search(cr, uid, [], context=context)
        for model_name in model_names:
            view_id = model_names.get(model_name, None)
            if view_id:
                view_id = view_id.split('.')
                view_id = data_obj.get_object_reference(cr, uid, view_id[0], view_id[1])[1]
            added = 0
            model_id = model_obj.search(cr, uid, [('model', '=', model_name)], context=context)[0]
            # Second, filters are search (only does that are public)
            search_filters = filter_obj.search(cr, uid, [('user_id', '=', False), ('model_id', '=', model_name), ('domain', 'not in', [False, '[]'])], context=context)
            search_filters.append(None)
            group_filters = filter_obj.search(cr, uid, [('user_id', '=', False), ('model_id', '=', model_name), ('context', 'not in', [False, '{}'])], context=context)
            group_filters.append(None)
            # Third, for each of them, a view report is created
            for search in search_filters:
                for group in group_filters:
                    vals = {
                        'model_id': model_id,
                        'filter_id': search,
                        'groupby_id': group,
                        'view_id': view_id,
                    }
                    domain = []
                    for t in vals:
                        domain.append((t, '=', vals[t]))
                    existing_ids = self.search(cr, uid, domain, context=context)
                    for i in existing_ids:
                        old_ids.remove(i)
                    if not existing_ids:
                        added += 1
                        self.create(cr, uid, vals, context)
            logger.debug("Created view reports for {0}: {1}".format(model_name, added))
        if old_ids:
            logger.debug("Removing {0} old view reports".format(len(old_ids)))
            self.unlink(cr, uid, old_ids, context=context)

    def open_view(self, cr, uid, ids, context=None):
        if type(ids) is list:
            ids = ids[0]
        _globals = globals().copy()
        _globals['context_today'] = datetime.today
        _globals['relativedelta'] = relativedelta.relativedelta
        obj = self.browse(cr, uid, ids, context)

        ret = {
            "type": "ir.actions.act_window",
            "res_model": obj.model_id.model,
            "views": [[obj.view_id and obj.view_id.id or False, 'tree']],
            "context": {},
            "domain": [],
            "target": "current",
        }

        if obj.filter_id:
            ret['domain'] = eval(obj.filter_id.domain, _globals)
        if obj.groupby_id:
            ret['context'].update(eval(obj.groupby_id.context, _globals))

        logger.debug("Opening view with action: {0}".format(ret))

        return ret

    def onchange_fields(self, cr, uid, ids, model_id, filter_id, context=None):
        ret = {
            'domain': {},
            'value': {},
        }
        if model_id:
            model_name = self.pool.get('ir.model').read(cr, uid, model_id, ['model'], context=context)['model']
            ret['domain']['view_id'] = [('model', '=', model_name), ('type', '=', 'tree')]
            ret['domain']['filter_id'] = [('model_id', '=', model_name), ('domain', '!=', False)]
            ret['domain']['groupby_id'] = [('model_id', '=', model_name), ('context', 'not in', [False, '{}'])]
        else:
            ret['value']['view_id'] = None
            ret['value']['filter_id'] = None
            ret['value']['groupby_id'] = None
        return ret

    _columns = {
        'model_id': fields.many2one('ir.model', 'Model', required=True),
        'view_id': fields.many2one('ir.ui.view', 'Tree view', required=False),
        'filter_id': fields.many2one('ir.filters', 'Filter', required=False),
        'groupby_id': fields.many2one('ir.filters', 'Group by', required=False),
    }

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
