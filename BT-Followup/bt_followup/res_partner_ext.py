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

from osv import fields, osv, orm
from openerp.osv.orm import except_orm
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT
from tools.translate import _
from bt_helper.log_rotate import get_log
import datetime
from .report import invoice_followup_report
logger = get_log("DEBUG")


class res_partner_ext(osv.osv):

    """ Adding follow-up information to res_partner.

    Show invoices added to follow-up process, followups created,
    mails sent and penalization invoices.

    """

    _inherit = "res.partner"

    def create(self, cr, uid, values, context=None):
        """ Overrides the create so that:
            1) The dunning block is set correctly on the children.
            2) The dunning block's date is set correctly on the children.
        """
        if context is None:
            context = {}

        # We set this flag to True so that users not belonging to the financial groups which allow
        # for a user of bt_followup (listed in method can_use_followups()) can create a partner (which sets the two fields
        # dunning_block and dunning_block_date).
        context['allow_exceptional_use_of_followups'] = True

        new_partner_id = super(res_partner_ext, self).create(cr, uid, values, context=context)

        # Sets the dunning block on this partner and its children.
        if values.get('dunning_block', False):
            self.__set_dunning_block_on_family(cr, uid, new_partner_id, values['dunning_block'], context=None)

        # Sets the dunning block date on this partner and its children.
        if 'dunning_block_date' in values:
            self.__set_dunning_block_date_on_family(cr, uid, new_partner_id, values['dunning_block_date'], context)

        del context['allow_exceptional_use_of_followups']
        return new_partner_id

    def write(self, cr, uid, ids, values, context=None):
        """ Overrides the write so that:
            1) The end date of the dunning block is no set in the past.
            2) The date of the next action to perform is not set in the past.
            3) The dunning block is set correctly on the children.
            4) The dunning block's date is set correctly on the children.
        """
        if context is None:
            context = {}

        date_today_str = datetime.date.today().strftime(DEFAULT_SERVER_DATE_FORMAT)
        errors = []

        # Checks that the end date of the dunning block is not set in the past.
        if 'dunning_block_date' in values:
            if values['dunning_block_date'] and (values['dunning_block_date'] < date_today_str):
                errors.append(_('- The end of the dunning block can not be set in the past, please change it.'))

        # Checks that the date of the next action is not set in the past.
        if 'followup_payment_next_action_date' in values:
            if values['followup_payment_next_action_date'] and (values['followup_payment_next_action_date'] < date_today_str):
                errors.append(_('- The date of the next action can not be set in the past, please change it.'))

        # Sets the dunning block on this partner and its children.
        if 'dunning_block' in values:
            self.__set_dunning_block_on_family(cr, uid, ids, values['dunning_block'], context)

        # Sets the dunning block date on this partner and its children.
        if 'dunning_block_date' in values:
            self.__set_dunning_block_date_on_family(cr, uid, ids, values['dunning_block_date'], context)

        if errors:
            raise orm.except_orm(_('Data Error'), '\n'.join(errors))

        return super(res_partner_ext, self).write(cr, uid, ids, values, context)

    def __set_dunning_block_date_on_family(self, cr, uid, ids, dunning_block_date_value, context=None):
        """ Sets the field 'dunning_block_date' an a family of res.partners. The user interface
            must assure this field is only set on the parent.
        """
        self.__set_field_on_family(cr, uid, ids, 'dunning_block_date', dunning_block_date_value, True, context=context)

    def __set_dunning_block_on_family(self, cr, uid, ids, dunning_block_value, context=None):
        """ Sets the field 'dunning_block' an a family of res.partners. The user interface
            must assure this field is only set on the parent.
        """
        self.__set_field_on_family(cr, uid, ids, 'dunning_block', dunning_block_value, False, context=context)

        # If we clear out the dunning block, then we clear out its date also.
        if dunning_block_value is False:
            self.write(cr, uid, ids, {'dunning_block_date': False}, context=context)

    def __set_field_on_family(self, cr, uid, ids, field_name, field_value, field_is_date, context=None):
        """ Sets the same value of a field over all the children of the partners the ID of which are received.
        """
        if context is None:
            context = {}
        if type(ids) is not list:
            ids = [ids]

        if not self.pool.get('res.users').can_use_followups(cr, uid, uid, context=context):
            raise orm.except_orm(_('Not Enough Permissions'),
                                 _('You must belong to group_account_manager or group_account_user to make use of Follow-Ups in order to modify the dunning block fields.'))

        # Setting dates to False is tricky because Odoo sends us False even if the field is NULL, but we can not
        # set a datetime in PostgreSQL to be 'False', but NULL.
        if not field_value and field_is_date:
            field_value_str = 'NULL'
        elif type(field_value) is str:
            field_value_str = "'{0}'".format(field_value)
        else:
            field_value_str = str(field_value)
        ids_str = ','.join(map(str, ids or [0]))  # [0] In the case ids is empty (which should never happen, but...)
        sql_query = "UPDATE res_partner SET {field_name}={field_value} WHERE id IN ({ids_str}) OR parent_id IN ({ids_str})".format(field_name=field_name,
                                                                                                                                   field_value=field_value_str,
                                                                                                                                   ids_str=ids_str)
        cr.execute(sql_query)

    def get_partner_date_format(self, cr, uid, ids, context=None):
        ''' Gets the format for dates according to the
            res.partner's language, in the case it is not null;
            otherwise uses the default date format.
        '''
        if context is None:
            context = {}
        partner_language = DEFAULT_SERVER_DATE_FORMAT  # The default date format.

        if type(ids) is not list:
            ids = [ids]
        partner = self.browse(cr, uid, ids[0], context=context)

        res_lang_obj = self.pool.get('res.lang')
        languages_ids = res_lang_obj.search(cr, uid, [('code', '=', partner.lang)], context=context, limit=1)
        languages = res_lang_obj.browse(cr, uid, languages_ids, context)
        if languages:
            partner_language = languages[0].date_format

        return partner_language

    def _fun_get_partner_followup_info(self, cr, uid, ids, names, arg, context=None, company_id=None):
        ''' Sets some fields for a res.partner, which informs:
            - if the partner is in a follow-up process,
            - if some follow-up levels require a handling.

            If any of the res.partners of the 'family tree' satisfies any of its conditions, then
            it affects all the partners of the 'family'.
        '''
        res = {}

        account_invoice_pool = self.pool.get('account.invoice')

        if company_id is None:
            company = self.pool.get('res.users').browse(cr, uid, uid,
                                                        context=context).company_id
        else:
            company = self.pool.get('res.company').browse(cr,
                                                          uid,
                                                          company_id,
                                                          context=context)

        for partner in self.browse(cr, uid, ids, context=context):
            # Gets the parent of this partner.
            parent_partner_obj = self.browse(cr, uid, partner.id, context)
            while parent_partner_obj.parent_id:
                parent_partner_obj = parent_partner_obj.parent_id

            # Gets the follow-up invoices of the parent (which include all those of its family)
            followup_invoices = parent_partner_obj.followup_ids

            in_followup_process = False
            pending_followup = False
            already_checked_invoices = []

            for followup_obj in followup_invoices:
                # Prevents duplicates and improves the performance of the for loop.
                invoice = account_invoice_pool.browse(cr, uid, followup_obj.followup_parent_id.id, context)
                if invoice.id in already_checked_invoices:
                    continue
                else:
                    already_checked_invoices.append(invoice.id)
                if in_followup_process and pending_followup:
                    break

                if (invoice.company_id == company):
                    if invoice.state == 'open' and invoice.followup_level_id:
                        in_followup_process = True
                        if not invoice.followup_level_handled:
                            pending_followup = True

            # Sets the values for all the res.partners of the family.
            family_ids = self._get_family_partners_ids(cr, uid, partner.id, context)
            for partner_id in family_ids:
                res[partner_id] = {'in_followup_process': in_followup_process,
                                   'pending_followup': pending_followup}
        return res

    def _get_partner(self, cr, uid, ids, context=None):
        if context is None:
            context = {}

        partner_ids = set()
        for invoice in self.pool.get('account.invoice').browse(cr,
                                                               uid,
                                                               ids,
                                                               context=context):
            partner_ids.add(invoice.partner_id.id)

        return list(partner_ids)

    def _fun_has_parent(self, cr, uid, ids, field_name, arg, context=None):
        if context is None:
            context = {}
        res = {}
        for partner_obj in self.browse(cr, uid, ids, context=context):
            if partner_obj.parent_id:
                res[partner_obj.id] = True
            else:
                res[partner_obj.id] = False
        return res

    def _get_dunned_invoice_ids(self, cr, uid, partner_ids, name, arg, context=None):
        ''' Returns the list of invoices for a given partner which are under a dunning-block.
            If the partner has children, it displays its invoices and those of its children.
        '''
        ret = {}
        res_partner_pool = self.pool.get('res.partner')
        invoice_pool = self.pool.get('account.invoice')

        for partner_id in partner_ids:
            partner_obj = res_partner_pool.browse(cr, uid, partner_id, context)
            family_ids = [partner_id]
            if partner_obj.child_ids:
                family_ids.extend(res_partner_pool.get_descendants(cr, uid, partner_id, context))

            domain = [('partner_id', 'in', family_ids),
                      ('type', '=', 'out_invoice'),
                      ('state', '=', 'open'),
                      ('dunning_block', '=', True),
                      ('followup_level_id', '!=', False)]

            ret[partner_id] = invoice_pool.search(cr, uid, domain, context=context)
        return ret

    def _get_penalization_invoices(self, cr, uid, partner_ids, name, arg, context=None):
        ''' Returns the list of penalisation invoices associated to a res.partner.
            If the partner has children, it displays its invoices and those of its children.
        '''
        ret = {}
        res_partner_pool = self.pool.get('res.partner')
        invoice_pool = self.pool.get('account.invoice')

        for partner_id in partner_ids:
            partner_obj = res_partner_pool.browse(cr, uid, partner_id, context)
            family_ids = [partner_id]
            if partner_obj.child_ids:
                family_ids.extend(res_partner_pool.get_descendants(cr, uid, partner_id, context))

            domain = [('partner_id', 'in', family_ids),
                      ('type', '=', 'out_invoice'),
                      ('followup_parent_id', '!=', False)]

            ret[partner_id] = invoice_pool.search(cr, uid, domain, context=context)
        return ret

    def _get_followup_ids(self, cr, uid, partner_ids, name, arg, context=None):
        ''' Returns the list of follow-ups for a given partner.
            If the partner has children, it displays its invoices and those of its children.
        '''
        ret = {}
        res_partner_pool = self.pool.get('res.partner')
        followup_pool = self.pool.get('followup')

        for partner_id in partner_ids:
            partner_obj = res_partner_pool.browse(cr, uid, partner_id, context)
            family_ids = [partner_id]
            if partner_obj.child_ids:
                family_ids.extend(res_partner_pool.get_descendants(cr, uid, partner_id, context))

            ret[partner_id] = followup_pool.search(cr, uid, [('followup_partner_id', 'in', family_ids)], context=context)
        return ret

    def _get_email_ids(self, cr, uid, partner_ids, name, arg, context=None):
        ''' Returns the list of emails for a given partner.
            If the partner has children, it displays its emails and those of its children.
        '''
        ret = {}
        res_partner_pool = self.pool.get('res.partner')
        mail_pool = self.pool.get('mail.mail')

        for partner_id in partner_ids:
            partner_obj = res_partner_pool.browse(cr, uid, partner_id, context)
            family_ids = [partner_id]
            if partner_obj.child_ids:
                family_ids.extend(res_partner_pool.get_descendants(cr, uid, partner_id, context))

            ret[partner_id] = mail_pool.search(cr, uid, [('followup_partner_id', 'in', family_ids)], context=context)
        return ret

    def get_descendants(self, cr, uid, partner_id, context=None):
        ''' Gets a list of the descendantsi IDs of a res.partner.
            For example, given this tree of partners:
                             A
                            / \
                           B  C
                          / \
                         D  E
            then the descendants of A are [B.id, C.id, D.id, E.id],
            the descendants of B are [D.id, E.id],
            the descendants of D are [].
            (Of course, the order is not assured).
        '''
        list_of_descendants = []

        if type(partner_id) is list:
            partner_id = partner_id[0]

        # Gets the list of all the res.partners of the family.
        partner_obj = self.browse(cr, uid, partner_id, context)
        partners_to_consider = partner_obj.child_ids

        while len(partners_to_consider) > 0:
            child_obj = partners_to_consider.pop()
            list_of_descendants.append(child_obj.id)
            partners_to_consider.extend(child_obj.child_ids)

        return list_of_descendants

    def _get_family_partners_ids(self, cr, uid, ids, context=None):
        ''' Returns the IDs of all the partners related to a given one.
            It works with hierarchies of an arbitrary number of levels.
            For example, given this tree of partners:
                             A
                            / \
                           B  C
                          / \
                         D  E
            it returns [A.id, B.id, C.id, D.id, E.id] (or course the order is not assured) no matter it receives A, B, C, D, E, etc.
        '''
        if context is None:
            context = {}

        if type(ids) is not list:
            ids = [ids]

        # Gets who is the parent.
        parent_partner_obj = self.browse(cr, uid, ids, context)[0]
        while parent_partner_obj.parent_id:
            parent_partner_obj = parent_partner_obj.parent_id

        # Gets the descendants of the partner, and adds itself to the family.
        family_partners_ids = parent_partner_obj.get_descendants()
        family_partners_ids.append(parent_partner_obj.id)

        return family_partners_ids

    def do_handle_followup(self, cr, uid, customer_ids, context=None):
        """Calls the method do_handle_followup from acount_invoice

        Note:
          Translates the list of customers to list of customer invoices
          to be handeled and call invoice handle followup action.

        Args:
          customer_ids: All customers to be handeled.

        Returns:
          List with the ir.attachment's IDs of the reports generated.
          If context['exception'] = False is not set, otherwise logger.

        If the method is called from a server action, the ids are specified in the context
        If the method is called from a button, the ids are specified in the ids parameter
        """
        if context is None:
            context = {}
        context = context.copy()
        if context.get('active_ids', False):
            customer_ids = context['active_ids']
            # remove active_ids from context
            del context['active_ids']
        send_exception = context.get('exception', True)
        # =======================================================================
        # context['origin_model'] = 'res.partner'
        # ======================================================================

        if not customer_ids:
            return {}

        invoice_pool = self.pool.get('account.invoice')
        res_partner_pool = self.pool.get('res.partner')

        # If the partner has contacts (children), it handles its invoices and those of all its children.
        # If the partner has no children, then it only handles its invoices.
        extended_customer_ids = []
        for customer_id in customer_ids:
            customer_obj = res_partner_pool.browse(cr, uid, customer_id, context)
            if customer_obj.child_ids:
                family_ids = res_partner_pool.get_descendants(cr, uid, customer_id, context)
                extended_customer_ids.append(customer_id)
                extended_customer_ids.extend(family_ids)
            else:
                extended_customer_ids.append(customer_id)

        invoices = invoice_pool.search(
            cr, uid, [('partner_id', 'in', extended_customer_ids),
                      ('type', '=', 'out_invoice'),
                      ('state', '=', 'open'),
                      ('dunning_block', '=', False),
                      ('followup_level_id', '!=', False),
                      ('followup_level_handled', '=', False)
                      ], context=context)

        if not invoices:
            if send_exception:
                raise except_orm(_('Warning'),
                                 _('No invoices to handle!'))
            else:
                logger.warning("No invoices to handle!")
            return {}

        reports_printed_ids = invoice_pool.do_handle_followup(cr, uid, invoices, context=context)

        return reports_printed_ids

    def get_invoice_followup_table_html(self, cr, uid, ids, context=None):
        """Returns the html table with all invoices in ids

        Note:
          Build the html table with invoice to follow up to be included
          in email send to partners in invoice follow up process.

        Args:
          ids: [id] of the invoice to follow up.

        Returns:
          html table
        """
        assert len(ids) == 1
        if context is None:
            context = {}

        partner = self.browse(cr, uid, ids[0], context=context)

        context = dict(context, lang=partner.lang)

        company = self.pool.get(
            'res.users').browse(cr,
                                uid,
                                uid,
                                context=context).company_id

        customer_level_data = context.get('customer_level_data', False)
        if not customer_level_data:
            # We may be accessing this method from the outside, e.g. from the 'Preview' button of an email.template.
            # In this case, we do not have the list of invoices of this partner, thus we must create it ourselves.
            # The difference here is that, when generated here, it lists the invoices for all the follow-up levels.
            customer_level_data = []
            invoices_of_partner = self.pool.get('account.invoice').search(cr, uid, [('partner_id', '=', partner.id)], context=context)
            for invoice_of_partner in invoices_of_partner:
                inv_obj = self.pool.get('account.invoice').browse(cr, uid, invoice_of_partner, context=context)
                if (inv_obj.followup_level_id and not inv_obj.followup_level_handled
                        and inv_obj.followup_level_id.send_email and not inv_obj.followup_skip_email_sending):
                    customer_level_data.append(inv_obj)

        followup_table = ''
        if customer_level_data:
            followup_table = '''
                    <table width=100%%  style="font-size:8pt;border-collapse:collapse;">
                    <tr>
                        <td style="border-top: solid 1px #000; border-bottom: solid 1px #000;padding-top:5px; padding-bottom:5px;">''' + _("Invoice No.") + '''</td>
                        <td style="border-top: solid 1px #000; border-bottom: solid 1px #000;padding-top:5px; padding-bottom:5px;">''' + _("Date") + '''</td>
                        <td style="border-top: solid 1px #000; border-bottom: solid 1px #000;padding-top:5px; padding-bottom:5px;">''' + _("Due Date") + '''</td>
                        <td style="border-top: solid 1px #000; border-bottom: solid 1px #000;padding-top:5px; padding-bottom:5px;">''' + _("Amount") + " (%s)" % (company.currency_id.symbol) + '''</td>
                        <td style="border-top: solid 1px #000; border-bottom: solid 1px #000;padding-top:5px; padding-bottom:5px;">''' + _("Unpaid") + " (%s)" % (company.currency_id.symbol) + '''</td>
                        <td style="border-top: solid 1px #000; border-bottom: solid 1px #000;padding-top:5px; padding-bottom:5px;">''' + _("Dunning Level") + '''</td>
                        <td style="border-top: solid 1px #000; border-bottom: solid 1px #000;padding-top:5px; padding-bottom:5px;">''' + _("Dunning Charge") + '''</td>
                        <td style="border-top: solid 1px #000; border-bottom: solid 1px #000;padding-top:5px; padding-bottom:5px;">''' + _("Total") + '''</td>
                    </tr>'''

            total = 0
            currency = ''
            for inv in customer_level_data:

                invoice = self.pool.get(
                    'account.invoice').browse(cr,
                                              uid,
                                              inv['invoice_id'],
                                              context)

                currency = invoice.currency_id.symbol if invoice.currency_id else ''

                penalization_total = 0
                for penalization_invoice in invoice.followup_penalization_invoice_ids:
                    penalization_total += penalization_invoice.amount_total

                followup_total = penalization_total + invoice.residual

                total = total + followup_total

                rml_parse = invoice_followup_report.invoice_followup_report(
                    cr, uid, "followup_rml_parser", context=context)

                # todo get currency from invoice
                followup_table += '''
                        <tr>
                            <td style="padding-top:5px; padding-bottom:5px;">''' + invoice.number + '''</td>
                            <td style="padding-top:5px; padding-bottom:5px;">''' + invoice.date_invoice + '''</td>
                            <td style="padding-top:5px; padding-bottom:5px;">''' + invoice.date_due + '''</td>
                            <td style="padding-top:5px; padding-bottom:5px;">''' + rml_parse.formatLang(invoice.amount_total) + '''</td>
                            <td style="padding-top:5px; padding-bottom:5px;">''' + rml_parse.formatLang(invoice.residual) + '''</td>
                            <td style="padding-top:5px; padding-bottom:5px;">''' + invoice.followup_level_id.name + '''</td>
                            <td style="padding-top:5px; padding-bottom:5px;">''' + rml_parse.formatLang(penalization_total) + '''</td>
                            <td style="padding-top:5px; padding-bottom:5px;">''' + rml_parse.formatLang(followup_total) + '''</td>
                        </tr>
                        '''

            followup_table += '''

                            <tr>
                                <td colspan = "7"  style="border-top: solid 1px #000;font-size:8pt;padding-top:5px;">''' + _("Total") + '''</td>
                                <td  style="border-top: solid 1px #000;font-size:8pt;padding-top:5px;" >''' + rml_parse.formatLang(total) + '''&nbsp;''' + currency + '''</td>
                            </tr>
                    </table>
                    '''

        return followup_table

    # Functions for MAKO
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

    def migrate_dunning_block_fields(self, cr, uid):
        """ This method is to avoid people forget about executing the following sentences just once over all the databases that
            have bt_followup installed:
                update res_partner set dunning_block = dunning_block_value;
                alter table res_partner drop column dunning_block_value;
                update res_partner set dunning_block_date = dunning_block_date_value;
                alter table res_partner drop column dunning_block_date_value;

            So, instead, this method will be automatically executed every time an update of the module is done.

        """
        # We only check for dunning_block_value, and not dunning_block_date_value, because both fields are going to be removed simultaneously.
        cr.execute("select count(*) from information_schema.columns where table_name='res_partner' and column_name='dunning_block_value'")
        old_fields_still_exist = cr.fetchone()[0]

        if old_fields_still_exist:
            cr.execute("""UPDATE res_partner SET dunning_block = dunning_block_value;
                          ALTER TABLE res_partner DROP COLUMN IF EXISTS dunning_block_value;
                          UPDATE res_partner SET dunning_block_date = dunning_block_date_value;
                          ALTER TABLE res_partner DROP COLUMN IF EXISTS dunning_block_date_value;""")

    _columns = {
        'dunned_invoice_ids': fields.function(_get_dunned_invoice_ids, type='one2many', relation='account.invoice', string='Dunned Invoices', readonly=True),
        'penalization_invoice_ids': fields.function(_get_penalization_invoices, type='one2many', relation='account.invoice',
                                                    string='Penalization Invoices', readonly=True),
        'followup_ids': fields.function(_get_followup_ids, type='one2many', relation='followup', string='Follow-ups', readonly=True),
        'followup_mail_ids': fields.function(_get_email_ids, type="one2many", relation='mail.mail', string='Follow-up Emails', readonly=True),
        'followup_responsible_id': fields.many2one('res.users', ondelete='set null',
                                                   string='Follow-up Responsible',),


        'in_followup_process': fields.function(_fun_get_partner_followup_info, method=True,
                                               type='boolean', string="In Follow-up Process",
                                               help="One or more invoices of customer is included in follow-up process.",
                                               store={'account.invoice': (_get_partner, None, 50),
                                                      'res.partner': (lambda self, cr, uid, ids, c={}: ids, None, 50),
                                                      },
                                               multi="followup_info"),

        'pending_followup': fields.function(_fun_get_partner_followup_info, method=True,
                                            type='boolean', string="Pending Follow-up",
                                            help="One or more invoices of customer are pending to handle the follow-up level.",
                                            store={'account.invoice':
                                                   (_get_partner, None, 50),
                                                   'res.partner': (lambda self, cr, uid, ids, c={}: ids, None, 50),
                                                   },
                                            multi="followup_info"),

        'invoice_followup_notes': fields.text('Invoice Follow-up Notes'),

        'followup_payment_note': fields.text('Customer Payment Promise', help="Payment Note",
                                             track_visibility="onchange"),
        'followup_payment_next_action': fields.text('Next Action',
                                                    help="This is the next action to be taken. "
                                                         "It will automatically be set when the partner gets a "
                                                         "follow-up level that requires a manual action.",
                                                    track_visibility="onchange"),
        'followup_payment_next_action_date': fields.date('Next Action Date',
                                                         help="This is when the manual follow-up is needed. "
                                                         "The date will be set to the current date when the partner "
                                                         "gets a follow-up level that requires a manual action. "
                                                         "Can be practical to set manually e.g. to see if he keeps his promises."),

        'dunning_block_date': fields.date('Dunning Block Ending Date'),
        'dunning_block': fields.boolean('Dunning Block', help="Block the follow up process for this user"),

        'has_parent':
            fields.function(
                _fun_has_parent,
                string='Has parent',
                type="boolean",
                method=True),


    }

    _defaults = {
        'dunning_block': False,
        'dunning_block_date': False,
    }

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
