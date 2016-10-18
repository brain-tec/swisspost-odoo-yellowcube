# b-*- encoding: utf-8 -*-
##############################################################################
#
#    Copyright (c) 2014 brain-tec AG (http://www.brain-tec.ch)
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
import logging
logger = logging.getLogger(__name__)
from openerp.tools.translate import _


class purchase_order_ext(osv.Model):
    _inherit = "purchase.order"
    _name = "purchase.order"

    def _set_destination_location(self, cr, uid, context=None):
        ''' Gets all the purchase orders which are in state draft and sets its destination to
            be the input location of its destination warehouse.
        '''
        if context is None:
            context = {}

        purchase_order_draft_ids = self.search(cr, uid, [('state', '=', 'draft')], context=context)
        for purchase_order in self.browse(cr, uid, purchase_order_draft_ids, context=context):
            input_location_of_warehouse = purchase_order.picking_type_id.default_location_dest_id
            if purchase_order.location_id != input_location_of_warehouse:
                self.write(cr, uid, purchase_order.id, {'location_id': input_location_of_warehouse.id}, context=context)
        return True

    def cron_merge_similar_orders(self, cr, uid):
        context = {}
        not_merged_purchase_orders_domain = [('purchase_order_merged', '=', False),
                                             ('state', '=', 'draft'),
                                             ]

        self._set_destination_location(cr, uid, context)

        purchase_ids = self.search(cr, uid, not_merged_purchase_orders_domain, context=context)
        logger.debug("Purchase orders to merge and send e-mails: {0}".format(purchase_ids))
        if not purchase_ids:
            return True

        ids = self.do_merge(cr, uid, purchase_ids, context=context)
        logger.debug("Purchase orders merged: {0}".format(ids))

        purchase_ids = self.search(cr, uid, not_merged_purchase_orders_domain, context=context)
        logger.debug("Purchase orders to send e-mails: {0}".format(purchase_ids))
        if not purchase_ids:
            return True

        issue_obj = self.pool.get('project.issue')
        for order_id in ids:
            # mail_id = mail_template_obj.send_mail(cr, uid, mail_template_id, order_id, force_send=False, context=context)
            issue_ids = issue_obj.find_resource_issues(cr,
                                                       uid,
                                                       'purchase.order',
                                                       order_id,
                                                       tags=['purchase.order', 'procurements'],
                                                       create=True,
                                                       reopen=True,
                                                       context=context)
            for issue in issue_obj.browse(cr, uid, issue_ids, context=context):
                issue.message_post(_('Purchase order, merged and ready to submit to provider'))
            self.write(cr, uid, order_id, {'purchase_order_merged': True})

        return True

    _columns = {
        # This field 'purchase_order_merged' was before named 'procurement_mail_sent, which
        # obviously (having a look at the code) was a confusing name.
        'purchase_order_merged': fields.boolean('Purchase Order Merged')
    }

    _defaults = {
        'purchase_order_merged': False
    }

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
