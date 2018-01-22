# b-*- encoding: utf-8 -*-
##############################################################################
#
#    Copyright (c) 2017 brain-tec AG (http://www.braintec-group.com)
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

import netsvc
from openerp.osv import fields, osv
from openerp.tools.translate import _
from openerp.addons.pc_log_data.log_data import write_log


class account_invoice_ext(osv.osv):
    _inherit = 'account.invoice'

    def get_followup_report(self, cr, uid, ids, context=None):
        """ Takes the name of the report defined in the follow-up level
            of the invoice, or the default one if none is indicated.
        """
        if context is None:
            context = {}
        if not isinstance(ids, list):
            ids = [ids]

        inv = self.browse(cr, uid, ids[0], context=context)
        if inv.followup_level_id and \
                inv.followup_level_id.report_account_invoice:
            # Gets the report indicated for the given follow-up level.
            report_name = 'report.{0}'.format(
                inv.followup_level_id.report_account_invoice.report_name)
        else:
            # Gets the default report name to use.
            report_name = super(account_invoice_ext, self).get_followup_report(
                cr, uid, ids, context=None)

        return report_name

    def do_print_followup_report(self, cr, uid, ids, context=None):
        """ Overridden to tag the attachments created for follow-ups.
        """
        if context is None:
            context = {}
        if not isinstance(ids, list):
            ids = [ids]

        attach_obj = self.pool.get('ir.attachment')
        attachment_tag_obj = self.pool.get('ir.attachment.tag')

        attach_ids = super(account_invoice_ext, self).do_print_followup_report(
            cr, uid, ids, context=context)

        # Caches the attachment's tags per follow-up level.
        attach_tags_ids = {}

        for attach in attach_obj.browse(cr, uid, attach_ids, context=context):

            inv = self.browse(cr, uid, attach.res_id, context=context)

            # Gets the ID of the tag to use in the attachment. Uses a cache
            # just in case several attachments are printed at the same time.
            followup_level = inv.followup_level_id.get_followup_level_number()
            if followup_level not in attach_tags_ids:
                attach_tag = 'follow-up-{0}'.format(followup_level)
                attach_tag_id = attachment_tag_obj.get_tag_id(
                    cr, uid, [], attach_tag, context=context)
                attach_tags_ids[followup_level] = attach_tag_id

            attach_tag_id = attach_tags_ids[followup_level]
            attach.write(
                {'tags_ids': [(4, attach_tag_id, False)]},
                context=context)

        return attach_ids

    def do_handle_followup(self, cr, uid, ids, context=None):
        """ Overridden to consider the routing options.
        """
        if context is None:
            context = {}

        attach_obj = self.pool.get('ir.attachment')

        # We handle the follow-ups, but we take control over the doc-out
        # because in the case of PF it will be taken over by the routing.
        ctx = context.copy()
        ctx['do_default_docout_followup_sending'] = False
        attach_ids = super(account_invoice_ext, self).do_handle_followup(
            cr, uid, ids, context=ctx)

        # Does the routing for all the attachments generated, which eventually
        # will set the doc-out if it has to be needed.
        inv_with_attch_ids = []
        for attach in attach_obj.browse(cr, uid, attach_ids, context=context):
            inv_with_attch_ids.append(attach.res_id)
        self.do_followup_routing(cr, uid, inv_with_attch_ids, context=context)

        return attach_ids

    def do_followup_routing(self, cr, uid, ids, context=None):
        """ Does the part for the follow-up routing.
        """
        if not isinstance(ids, list):
            ids = [ids]
        if context is None:
            context = {}

        ir_attachment_obj = self.pool.get('ir.attachment')
        ir_attachment_tag_obj = self.pool.get('ir.attachment.tag')
        mail_template_obj = self.pool.get("email.template")
        mail_mail_obj = self.pool.get('mail.mail')
        conf_obj = self.pool.get('configuration.data')
        followup_errors_obj = self.pool.get('followup.errors')

        conf = conf_obj.get(cr, uid, [], context=context)

        for inv in self.browse(cr, uid, ids, context=context):

            # The routing is only active if we are going to send a letter
            # with the current follow-up level.
            if inv.followup_level_id.send_letter:
                foll_level = inv.followup_level_id
                foll_level_num = foll_level.get_followup_level_number()
                foll_routing = inv.followup_level_id.invoice_routing
                inv_routing = inv.invoice_routing

                # Determines the routing to use: or email or docout.
                if foll_routing == 'same_as_invoice':
                    if inv_routing in ('email', 'docout'):
                        routing = inv_routing
                    else:
                        routing = False  # We need a routing, so raise.
                elif foll_routing == 'force_email':
                    routing = 'email'
                else:  # if foll_routing == 'force_docout':
                    routing = 'docout'

                # Finds the attachment to route.
                attach_tag = 'follow-up-{0}'.format(foll_level_num)
                tag_id = ir_attachment_tag_obj.get_tag_id(
                    cr, uid, [], attach_tag, context=context)
                followup_attachment_ids = ir_attachment_obj.search(cr, uid, [
                    ('tags_ids', 'in', tag_id),
                    ('res_id', '=', inv.id),
                    ('res_model', '=', 'account.invoice'),
                ], limit=1, context=context)
                if not followup_attachment_ids:
                    error_message = _("No attachment was found for invoice "
                                      "with ID={0} and follow-up level with "
                                      "ID={1}").format(inv.id, foll_level.id)
                    followup_errors_obj.create_error_entry(
                        cr, uid, [], inv.id, error_message, context=context)
                    write_log(self, cr, uid, 'account.invoice', 'Follow-up',
                              inv.id, _('Error on routing of follow-ups'),
                              error_message)

                # If the routing is by email, an email, generated using the
                # provided email template set on the follow-up level, and
                # having as an attachment the letter corresponding to the
                # follow-up level, is preared to be sent when possible.
                if routing == 'email':
                    ctx = context.copy()
                    ctx['lang'] = inv.partner_id.lang or False
                    values = mail_template_obj.generate_email(
                        cr, uid, foll_level.docout_email_template_id.id,
                        inv.id, context=ctx)
                    # If we don't set the type to be 'email', it won't be sent
                    # automatically by the scheduler.
                    ctx['type'] = 'email'
                    values['type'] = 'email'
                    msg_id = mail_mail_obj.create(cr, uid, values, context=ctx)
                    mail_mail_obj.write(cr, uid, msg_id, {
                        'attachment_ids': [(6, 0, followup_attachment_ids)],
                    }, context=ctx)

                # If the routing is by doc-out, sets the corresponding flags
                # according to the configuration set for the doc-out in the
                # Post Configuration, and waits for the scheduler to run it
                # after so that they are actually sent.
                elif routing == 'docout':
                    docout_filename = inv.get_docout_filename_followups()
                    docout_write = {
                        'docout_file_type': 'followup',
                        'docout_exported_file_name_email': docout_filename,
                        'docout_exported_file_name_remote_folder': docout_filename,
                        'docout_state_email': 'not_applicable',
                        'docout_state_remote_folder': 'not_applicable',
                    }
                    do_docout_write = False
                    if conf.docout_followup_activate_send_to_email:
                        docout_write['docout_state_email'] = 'to_send'
                        do_docout_write = True
                    if conf.docout_followup_activate_send_to_server:
                        docout_write['docout_state_remote_folder'] = 'to_send'
                        do_docout_write = True

                    if do_docout_write:
                        ir_attachment_obj.write(
                            cr, uid, followup_attachment_ids, docout_write,
                            context=context)

                else:  # if routing is False:
                    error_message = _("No correct combination of routing "
                                      "options was set: Inv. Routing = {0}, "
                                      "Follow-up Routing = {1}").format(
                        inv_routing, foll_routing)
                    followup_errors_obj.create_error_entry(
                        cr, uid, [], inv.id, error_message, context=context)
                    write_log(self, cr, uid, 'account.invoice', 'Follow-up',
                              inv.id, _('Error on routing of follow-ups'),
                              error_message)

        return True

    def _vals_to_create_penalization_invoice(self, cr, uid, ids, context=None):
        """ Overridden so that the carrier of the new penalisation invoice
            is taken from the one indicated in the follow-up level.
        """
        if context is None:
            context = {}
        if not isinstance(ids, list):
            ids = [ids]

        vals = super(account_invoice_ext, self).\
            _vals_to_create_penalization_invoice(cr, uid, ids, context=context)

        inv = self.browse(cr, uid, ids[0], context=context)
        if inv.followup_level_id.carrier_id:
            vals.update({
                'carrier_id': inv.followup_level_id.carrier_id.id,
            })

        return vals

    def _create_penalization_invoice(self, cr, uid, invoice_id, context=None):
        """ Overridden so that the penalisation invoice is opened instead
            of pro-forma.
        """
        new_invoice_id = super(account_invoice_ext, self).\
            _create_penalization_invoice(cr, uid, invoice_id, context=context)

        wf_service = netsvc.LocalService('workflow')
        wf_service.trg_validate(uid, 'account.invoice', new_invoice_id,
                                'invoice_open', cr)

        return new_invoice_id

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
