# b-*- encoding: utf-8 -*-
#
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
#

from osv import osv


class res_users_ext(osv.osv):

    _inherit = "res.users"

    def can_use_followups(self, cr, uid, ids, context=None):
        ''' Returns whether a res.user belongs to the groups:
            - group_account_manager,
            - group_account_user,
            which are the group that can use the follow-ups.
        '''
        if context is None:
            context = {}
        if type(ids) is not list:
            ids = [ids]

        if 'allow_exceptional_use_of_followups' in context:
            user_can_use_followups = context['allow_exceptional_use_of_followups']

        else:
            target_user_uid = ids[0]

            ir_model_data_obj = self.pool.get('ir.model.data')

            # Gets the IDs of the groups allowed to make use of follow-ups.
            # TODO: Make a real group for this a user can belong to.
            followup_allowed_group_ids = []
            for group_xmlid in ('group_account_manager', 'group_account_user'):
                group_ref = ir_model_data_obj.get_object_reference(cr, uid, 'account', group_xmlid)
                if group_ref:
                    followup_allowed_group_ids.append(group_ref[1])

            groups_of_user_ids = self.search(cr, uid, [('id', '=', target_user_uid),
                                                       ('groups_id', 'in', followup_allowed_group_ids),
                                                       ], context=context, count=True)
            user_can_use_followups = (groups_of_user_ids > 0)

        return user_can_use_followups

    def get_list_of_invoices_user_is_responsible_from(self, cr, uid, ids, context=None):
        ''' Returns the list of IDs for the invoices this res.user is responsible from.
        '''
        if context is None:
            context = {}
        if type(ids) is not list:
            ids = [ids]

        invoice_ids = self.pool.get('account.invoice').search(cr, uid, [('state', '=', 'open'),
                                                                        ('followup_level_id', '!=', None),
                                                                        ('followup_responsible_id', 'in', ids),
                                                                        ], context=context)
        return invoice_ids

    def get_html_list_of_invoices_responsible(self, cr, uid, ids, context=None):
        ''' Return a string encoding an HTML unordered list containing the invoices
            this res.user is responsible from, because of being under a follow-up process.
        '''
        if context is None:
            context = {}
        if type(ids) is not list:
            ids = [ids]

        # Gets the object.
        res_user = self.browse(cr, uid, ids[0], context=context)

        # Gets the list of invoices he/she is responsible from.
        invoice_ids = res_user.get_list_of_invoices_user_is_responsible_from(context=context)

        # Fills-in the list.
        html_list = '<ul>\n'
        for invoice in self.pool.get('account.invoice').browse(cr, uid, invoice_ids, context=context):
            manual_action = invoice.get_manual_action(context=context)
            html_list = '{0}\t<li><strong>Invoice {1}</strong> (id={2}) --- Action: {3}</li>\n'.format(html_list, invoice.number, invoice.id, manual_action or '-')
        html_list = '{0}\n</ul>\n'.format(html_list)

        return html_list

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
