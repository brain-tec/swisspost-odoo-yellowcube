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
logger = logging.getLogger(__name__)


class ir_filters_ext(osv.Model):
    _inherit = 'ir.filters'

    def create(self, cr, uid, vals, context=None):
        if not vals.get('user_id', None):
            logger.debug("Removing ir.filter '{0}':'{1}'".format(vals['model_id'], vals['name']))
            ids = self.search(cr, uid, [('name', '=', vals['name']),
                                        ('model_id', '=', vals['model_id']),
                                        ('user_id', '=', None),
                                        ], context=context)
            self.unlink(cr, uid, ids, context)
        return super(ir_filters_ext, self).create(cr, uid, vals, context=context)

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
