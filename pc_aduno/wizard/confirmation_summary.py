# b-*- encoding: utf-8 -*-
##############################################################################
#
#    Copyright (c) 2016 brain-tec AG (http://www.braintec-group.com) 
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
from tools.translate import _
from osv import osv, fields

class confirmation_summary(osv.osv_memory):
    _name = 'confirmation.summary'
    _columns = {
        'summary':fields.text('Confirmation summary', readonly=True)
    }

    def default_get(self, cr, uid, fields, context):
        summary = context.get('summary', False)
        res = super(confirmation_summary, self).default_get(cr, uid, fields,context=context)
        res['summary'] = summary
        return res

confirmation_summary()
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:             
