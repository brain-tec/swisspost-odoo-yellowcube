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
from osv import osv, fields
from openerp.tools import DEFAULT_SERVER_DATETIME_FORMAT
from datetime import datetime, timedelta


class res_partner_ext(osv.Model):
    _inherit = 'res.partner'

    _columns = {
        'intrum_requests': fields.one2many('intrum.request', 'partner_id', string='intrum Requests', readonly=True),
        'last_check_date': fields.datetime(string='Last request of this partner to Intrum',
                                           help="Date of the last Intrum check, modify it in order to force a re-querying of the Intrum service (see Post configuration tab for more information)."),
    }

    def check_credit(self, cr, uid, ids, amount, priority=None, priorities=None, context=None):
        ''' Uses the intrum service to check the creditworthiness
            Priority stores the priority level of this check: 100
            Priorities is used to send the number of implemented priorities
        '''
        if context is None:
            context = {}
        # If this is not our priority, we add it to the list of priorities to
        # consider.
        if priority != 100:
            if priorities is None:
                # We use a set because priorities must not be repeated
                priorities = []
            priorities.append(100)
            res = super(res_partner_ext, self).check_credit(cr, uid, ids, amount, priority, priorities, context)
        else:
            if type(ids) is list:
                ids = ids[0]

            res = {}

            configuration_data = self.pool.get('configuration.data').get(cr, uid, [], context)
            intrum_request_obj = self.pool.get('intrum.request')
            now = datetime.now()

            # Retrieving the most updated value.
            # We don't call again Intrum over a partner if we have queried about him/her recently
            # and we got a meaningful response code.
            last_intrum_request_ids = intrum_request_obj.search(cr, uid, [('partner_id', '=', ids),
                                                                          ('response_code', '!=', 0)],
                                                                order='write_date DESC', limit=1, context=context)
            do_new_intrum_check = False
            if last_intrum_request_ids != []:

                last_request = intrum_request_obj.browse(cr, uid, last_intrum_request_ids[0], context=context)
                max_date_intrum_check = datetime.strptime(last_request.write_date, DEFAULT_SERVER_DATETIME_FORMAT) + \
                    timedelta(days=configuration_data.intrum_max_days_since_last_check)

                partner = self.browse(cr, uid, ids, context=context)
                max_date_intrum_check_partner = datetime.strptime(partner.last_check_date, "%Y-%m-%d %H:%M:%S.%f") + \
                    timedelta(days=configuration_data.intrum_max_days_since_last_check)

                # We first check for the last check to Intrum done for the partner. This way, we can force
                # an extra check if we manually change the date.
                partner = self.browse(cr, uid, ids, context=context)
                if (not max_date_intrum_check_partner) or (now > max_date_intrum_check_partner):
                    do_new_intrum_check = True

                # If the date of the partner is correct, we then check for the date in which the actual
                # last Intrum check was done.
                elif (not max_date_intrum_check) or (now > max_date_intrum_check) or (last_request.order_amount < amount):
                    do_new_intrum_check = True
            else:
                do_new_intrum_check = True

            if do_new_intrum_check:
                partner_id = ids
                order_id = context.get('order_id', None)
                if type(order_id) == list:
                    order_id = order_id[0]
                intrum_response_code, res = self.pool.get('intrum.request').do_credit_worthiness_request(cr, uid, [], partner_id, order_id, amount, context=context)

                # Updates the last check date of the partner (in the case that we got a response)
                if intrum_response_code != 0:
                    self.write(cr, uid, ids, {'last_check_date': now}, context=context)

            else:
                # We retrieve the last result obtained for that partner.
                last_request = intrum_request_obj.browse(cr, uid, last_intrum_request_ids[0], context=context)
                res = {'decision': last_request.positive_feedback, 'description': last_request.description}

        return res

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
