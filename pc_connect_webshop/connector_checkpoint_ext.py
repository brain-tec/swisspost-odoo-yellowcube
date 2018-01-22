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
from openerp.tools.translate import _
import logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


class connector_checkpoint_ext(osv.Model):
    _inherit = 'connector.checkpoint'
    _name = 'connector.checkpoint'

    def cron_connector_checkpoint(self, cr, uid):
        logger.debug("Updating connector checkpoints")
        connector_management_obj = self.pool.get('checkpoint.management')
        connector_checkpoint_obj = self.pool.get('connector.checkpoint')

        connector_management_ids = connector_management_obj.search(cr, uid, [('automatic_process', '=', True)])
        ir_model_ids = [x.ir_model_id.id for x in connector_management_obj.browse(cr, uid, connector_management_ids)]
        connector_checkpoint_ids = connector_checkpoint_obj.search(cr, uid, [('state', '=', 'need_review'), ('model_id', 'in', ir_model_ids)])

        connector_checkpoint_obj.reviewed(cr, uid, connector_checkpoint_ids)
        return True

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
