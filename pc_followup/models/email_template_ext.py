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

import base64
import logging

from openerp import netsvc
from openerp.osv import osv, fields
from openerp.osv import fields
from openerp import tools
from openerp.tools.translate import _
from urllib import urlencode, quote as quote


class email_template_ext(osv.osv):
    _inherit = "email.template"

    def send_mail(self, cr, uid, template_id, res_id, force_send=False, context=None):
        # It extends the method from the core. The change is that now the
        # wildcards are filled-int on the body of the email.
        """Generates a new mail message for the given template and record,
           and schedules it for delivery through the ``mail`` module's scheduler.

           :param int template_id: id of the template to render
           :param int res_id: id of the record to render the template with
                              (model is taken from the template)
           :param bool force_send: if True, the generated mail.message is
                immediately sent after being created, as if the scheduler
                was executed for this message only.
           :returns: id of the mail.message that was created
        """

        if context is None:
            context = {}

        if 'followup' not in context:
            # Delegate if using old behaviour
            return super(email_template_ext, self).send_mail(cr, uid, template_id, res_id, force_send=force_send, context=context)

        mail_mail = self.pool.get('mail.mail')
        ir_attachment = self.pool.get('ir.attachment')

        # create a mail_mail based on values, without attachments
        values = self.generate_email(cr, uid, template_id, res_id, context=context)

        if not values.get('email_from'):
            raise osv.except_osv(_('Warning!'),_("Sender email is missing or empty after template rendering. Specify one to deliver your message"))

        # Retrieves the HTML tags.
        values['body'] = values['body'].replace("&gt;", ">").replace("&lt;", "<").replace("&amp;", "&")
        values['body_html'] = values['body_html'].replace("&gt;", ">").replace("&lt;", "<").replace("&amp;", "&")

        # Substitutes any wildcards present in the email text with their actual value.
        if 'wildcards' in context:
            for wildcard_rule in context['wildcards']:
                wildcard = wildcard_rule[0]
                if wildcard in values['body']:
                    text_to_substitute_with = str(wildcard_rule[1])
                    values['body'] = values['body'].replace(wildcard, text_to_substitute_with)
                    values['body_html'] = values['body_html'].replace(wildcard, text_to_substitute_with)

        # process email_recipients field that is a comma separated list of partner_ids -> recipient_ids
        # NOTE: only usable if force_send is True, because otherwise the value is
        # not stored on the mail_mail, and therefore lost -> fixed in v8
        recipient_ids = []
        email_recipients = values.pop('email_recipients', '')
        if email_recipients:
            for partner_id in email_recipients.split(','):
                if partner_id:  # placeholders could generate '', 3, 2 due to some empty field values
                    recipient_ids.append(int(partner_id))

        attachment_ids = values.pop('attachment_ids', [])
        attachments = values.pop('attachments', [])
        msg_id = mail_mail.create(cr, uid, values, context=context)
        mail = mail_mail.browse(cr, uid, msg_id, context=context)

        # manage attachments
        for attachment in attachments:
            attachment_data = {
                'name': attachment[0],
                'datas_fname': attachment[0],
                'datas': attachment[1],
                'res_model': 'mail.message',
                'res_id': mail.mail_message_id.id,
            }
            context.pop('default_type', None)
            attachment_ids.append(ir_attachment.create(cr, uid, attachment_data, context=context))
        if attachment_ids:
            values['attachment_ids'] = [(6, 0, attachment_ids)]
            mail_mail.write(cr, uid, msg_id, {'attachment_ids': [(6, 0, attachment_ids)]}, context=context)

        if force_send:
            mail_mail.send(cr, uid, [msg_id], recipient_ids=recipient_ids, context=context)
        return msg_id
