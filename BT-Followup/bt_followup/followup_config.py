# b-*- encoding: utf-8 -*-
#
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
#

from openerp.osv import fields, osv

from openerp.tools.translate import _


class followup_config(osv.osv):
    _name = 'followup.config'
    _description = 'Invoice Follow-up Configuration'
    _rec_name = 'name'
    _columns = {
        'followup_level':
            fields.one2many(
                'followup.level',
                'followup_config_id',
                'Follow-up'),
        'company_id': fields.many2one('res.company', 'Company', required=True),
        'name': fields.related('company_id', 'name', string="Name"),
    }
    _defaults = {
        'company_id': lambda s, cr, uid, c:
            s.pool.get(
                'res.company')._company_default_get(
                    cr,
                    uid,
                    'followup',
                    context=c),
    }

    def copy(self, cr, uid, id, defaults, context={}):
        config_ids = self.search(cr, uid, [], context=context)
        configs = self.browse(cr, uid, config_ids, context=context)
        company_ids = [x.company_id.id for x in configs]
        possible_company_ids = self.pool.get('res.company').search(cr,
                                                                   uid,
                                                                   [('id', 'not in', company_ids)],
                                                                   context=context)
        if possible_company_ids: 
            defaults['company_id'] = possible_company_ids[0]
        return super(followup_config, self).copy(cr, uid, id, defaults, context)

    _sql_constraints = [(
                        'company_uniq',
                        'unique(company_id)',
                        _('Only one follow-up configuration per company is allowed'))]

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
