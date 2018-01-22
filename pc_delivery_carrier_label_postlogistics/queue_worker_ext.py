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

from osv import orm, osv, fields
from openerp.tools.translate import _


class queue_worker_ext(orm.Model):
    _inherit = 'queue.worker'

    def get_error_messages_to_requeue(self, cr, uid, context):
        ''' Returns a list with error messages to requeue.
        '''
        error_messages_to_requeue = super(queue_worker_ext, self).get_error_messages_to_requeue(cr, uid, context)
        error_messages_to_requeue.append('%GATEWAY_TIMEOUT%')
        return error_messages_to_requeue

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
