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
from osv import osv, fields
from openerp.tools.translate import _
from pc_generics import generics


class res_partner_ext(osv.osv):
    _inherit = "res.partner"

    def get_partner_email(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        partner_obj = self.browse(cr, uid, ids, context)[0]
        return partner_obj.email

    def set_email(self, cr, uid, ids, email, context=None):
        if context is None:
            context = {}
        self.write(cr, uid, ids, {'email': email}, context=context)
        return True

    def create(self, cr, uid, values, context=None):
        ''' Overrides the create method so that if the partner created has a parent,
            then its under_followup_block field is taken from the parent.
        '''
        if context is None:
            context = {}

        id_ = super(res_partner_ext, self).create(cr, uid, values, context=context)

        partner = self.browse(cr, uid, id_, context)
        if partner.parent_id:
            # Sets the field 'under_followup_block'.
            partner._fun_under_followup_block('under_followup_block', context)

        return id_

    def _fun_under_followup_block(self, cr, uid, ids, field_name, args, context=None):
        ''' -  Checks if a partner has any invoice with a follow-up level which has been handled and
               which implies blocking new invoices.
            -  It does not only checks the invoices of the partner, but also the invoices of his/her
               'family tree' (itself and all the res.parents which are its children/siblings).
            - Also, if one member of the 'family' has to be blocked, all of the partners of the family are blocked.
        '''
        result = {}
        invoice_pool = self.pool.get('account.invoice')

        for partner in self.browse(cr, uid, ids, context):

            # Gets the family tree of a parent.
            family_partners_ids = partner._get_family_partners_ids()

            # Initially, they are not blocked.
            for partner_id in family_partners_ids:
                result[partner_id] = False

            # Gets the invoices with a handled follow-up associated to this partner.
            invoice_ids = invoice_pool.search(cr, uid, [('partner_id', 'in', family_partners_ids),
                                                        ('type', '=', 'out_invoice'),
                                                        ('state', '=', 'open'),
                                                        ('dunning_block', '=', False),
                                                        ('followup_level_handled', '=', True),
                                                        ('followup_level_id', '!=', False),
                                                        ('followup_level_id.block_new_invoice', '=', True),
                                                        ], limit=1, count=True, context=context)
            if invoice_ids > 0:
                for partner_id in family_partners_ids:
                    result[partner_id] = True

        return result

    def _sto_followup_partner(self, cr, uid, _id, context):
        cr.execute("SELECT followup_partner_id FROM followup WHERE id in ({0})".format(','.join([str(x)for x in _id])))
        return [x[0] for x in cr.fetchall()]

    def _sto_invoice_partner(self, cr, uid, _id, context):
        cr.execute("SELECT partner_id FROM account_invoice WHERE id in ({0})".format(','.join([str(x)for x in _id])))
        return [x[0] for x in cr.fetchall()]

    _columns = {
        # Hack the original one with responsible_id instead of partner_id
        'dunned_invoice_ids': fields.one2many('account.invoice', 'responsible_id',
                                              domain=[('type', '=', 'out_invoice'),
                                                      ('state', '=', 'open'),
                                                      ('dunning_block', '=', False),
                                                      ('followup_level_id', '!=', False)], string='Dunned Invoices', readonly=True),
        # Hack the original one with responsible_id instead of partner_id
        'penalization_invoice_ids': fields.one2many('account.invoice', 'responsible_id',
                                                    domain=[('type', '=', 'out_invoice'),
                                                            ('followup_parent_id', '!=', False)], string='Penalization Invoices', readonly=True),


        'under_followup_block': fields.function(_fun_under_followup_block,
                                                string='Under followup block',
                                                type='boolean',
                                                readonly=True,
                                                store={'followup': (_sto_followup_partner, ['followup_partner_id'], 10),
                                                       'account.invoice': (_sto_invoice_partner, ['state', 'followup_level_handled'], 10),
                                                       'res.partner': ((lambda self, cr, uid, _id, context: _id), ['in_followup_process', 'pending_followup', 'dunning_block'], 10)
                                                       }),
    }

    def check_credit(self, cr, uid, ids, amount, priority=None, priorities=None, context=None):
        ''' Checks if the followup process allows to buy something by invoice.
            Checks if a partner has previous dunning processes
            Priority stores the priority level of this check: 50
            Priorities is used to send the number of implemented priorities
        '''
        if context is None:
            context = {}

        # If this is not our priority, we add it to the list of priorities to consider.
        if priority != 50:
            if priorities is None:
                # We use a set because priorities must not be repeated
                priorities = []
            priorities.append(50)
            res = super(res_partner_ext, self).check_credit(cr, uid, ids, amount, priority, priorities, context)
        else:
            if type(ids) is list:
                ids = ids[0]

            res = {}

            # We store the IDs of all the res.partners related to this one.
            res_partner_obj = self.pool.get('res.partner')
            partner = res_partner_obj.browse(cr, uid, ids, context=context)
            while partner.parent_id and partner.id != partner.parent_id.id:
                partner = partner.parent_id
            partner_to_consider_ids = [partner.id] + partner.get_descendants(context=context)

            # We search for those follow-up levels which are blocking.
            # This table is so small that we do not filter by company_id, but just consider whether it blocks or not.
            blocking_followup_level_ids = self.pool.get('followup.level').search(cr, uid, [('block_new_invoice', '=', True)], context=context)

            # We search for those invoices which belong to the list of partners, which are opened,
            # and which are under a follow-up level which is blocking.
            are_invoices_blocked = self.pool.get('account.invoice').search(cr, uid, [('state', '=', 'open'),
                                                                                     ('partner_id', 'in', partner_to_consider_ids),
                                                                                     ('followup_level_id', 'in', blocking_followup_level_ids),
                                                                                     ], context=context, limit=1, count=True)
            if are_invoices_blocked:
                res['decision'] = False
                res['description'] = _("Payment method invoice is blocked because of open invoice(s) in dunning process.")

            else:
                res['decision'] = True
                res['description'] = _("No invoices in a blocking dunning process.")

        return res

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
