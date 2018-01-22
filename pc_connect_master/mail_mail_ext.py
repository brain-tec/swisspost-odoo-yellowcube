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
########################### ####################################################

from osv import osv
from openerp.tools.safe_eval import safe_eval
import logging
_logger = logging.getLogger(__name__)


class mail_mail_ext(osv.Model):
    _inherit = "mail.mail"

    def process_email_queue(self, cr, uid, ids=None, context=None):
        """ Overridden so that it can be indicated a maximum amount of emails to process.
        """
        _logger.debug("Executing an overridden version of the method process_email_queue from module mail_mail.")

        if context is None:
            context = {}
        if not ids:
            filters = ['&', ('state', '=', 'outgoing'), ('type', '=', 'email')]
            if 'filters' in context:
                filters.extend(context['filters'])

            process_email_queue_limit = safe_eval(self.pool.get('ir.config_parameter').get_param(cr, uid, 'process_email_queue_limit', 'None'))
            ids = self.search(cr, uid, filters, limit=process_email_queue_limit, context=context)

        res = None
        try:
            # Force auto-commit - this is meant to be called by
            # the scheduler, and we can't allow rolling back the status
            # of previously sent emails!
            res = self.send(cr, uid, ids, auto_commit=True, context=context)
        except Exception:
            _logger.exception("Failed processing mail queue")
        return res

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
