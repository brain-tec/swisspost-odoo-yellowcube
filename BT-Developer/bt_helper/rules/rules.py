# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program. If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

from osv import fields, osv, expression
from openerp.tools.translate import _
import logging

logger = logging.getLogger(__name__)


class rules(osv.osv):
    _name = 'bt_helper.rules'
    _description = 'BT Duplication models'

    _columns = {
        'model': fields.char(_('Model Name'), size=64, required=True),
        'is_global': fields.boolean(_('Global rule (all groups)'), help="If this flag is set, then all groups can duplicate"),
        'res_groups_id': fields.many2one('res.groups', _('Groups'), help="This are the groups that can duplicate", required=True),
        'condition': fields.text(_('Condition rule')),
    }

    _defaults = {
        'condition': '',
        'is_global': False,
    }

    def check_all(self, cr, uid, context={}):
        if uid == 1:
            return False
        user = self.pool.get('res.users').browse(cr, 1, uid)
        uid = 1
        groups = [x.id for x in user.groups_id]
        rules_ids = self.search(cr, uid, [('model', '=', context['model']), ('is_global', '=', True)])
        rules_ids.extend(self.search(cr, uid, [('model', '=', context['model']), ('res_groups_id', 'in', groups)]))
        for rule in self.browse(cr, uid, rules_ids):
            logger.debug('Found this rule:', rule.model)
            if not rule.condition or rule.condition == '':
                return True
            else:
                conditions = expression.normalize(eval(rule.condition, {}))
                conditions.append(('id', 'in', context['ids']))
                objects_ids = self.pool.get(context['model']).search(cr, uid, conditions)
                if len(objects_ids) == len(context['ids']):
                    return True
                # Check if all elements holds the condition
        return False
