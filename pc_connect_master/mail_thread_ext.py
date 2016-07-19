# b-*- encoding: utf-8 -*-
##############################################################################
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
##############################################################################

import HTMLParser
import logging
from openerp import tools
from openerp.addons.mail.mail_thread import mail_thread
from openerp.osv import osv
from openerp.tools.translate import _
from openerp.tools.misc import DEFAULT_SERVER_DATETIME_FORMAT
from openerp import api
from datetime import datetime
logger = logging.getLogger(__name__)


old_message_post = mail_thread.message_post


@api.cr_uid_id_context
def new_message_post(self, cr, uid, thread_id, body='', subject=None, type='notification',
                     subtype=None, parent_id=False, attachments=None, context=None,
                     content_subtype='html', **kwargs):
    ''' Overwritten because it is desired to avoid duplicated messages
        :arguments see the function "message_post" of the file "mail_thread": odoo/addons/mail/mail_thread.py
        :return int: ID of newly created mail.message OR the id of original message which would be duplicated
    '''
    if context is None:
        context = {}

    if not thread_id:
        raise osv.except_osv(_('Invalid thread_id'), _('Thread ID is not set'))
    if isinstance(thread_id, (list, tuple)):
        thread_id = thread_id[0]

    result = False
    call_old_message_post_flag = True

    if attachments is None:
        # As long as there are any attachments new messages will be created
        # Otherwise...
        if context.get('mail_thread_no_duplicate', False):
            mail_message_obj = self.pool.get('mail.message')

            # Handle content subtype: if plaintext, convert into HTML
            if content_subtype == 'plaintext':
                body_handled = tools.plaintext2html(body)
                # We need to modify <br/> to <br> since it is saved in this way in the data base, but handled with <br/> in the record
                body_handled = body_handled.replace("<br/>", "<br>")
            else:
                if "<span>" in body:
                    body_handled = "<div>" + HTMLParser.HTMLParser().unescape(body) + "</div>"
                else:
                    body_handled = HTMLParser.HTMLParser().unescape(body)

            domain = [('res_id', '=', thread_id),
                      ('model', '=', self._name),
                      ('body', '=', body_handled),
                      ]
            if not context['mail_thread_no_duplicate']:
                # If a timedelta is passed, we use it
                date = datetime.now() - context['mail_thread_no_duplicate']
                domain.append(('create_date', '>', date.strftime(DEFAULT_SERVER_DATETIME_FORMAT)))
            mail_message_id = mail_message_obj.search(cr, uid,
                                                      domain,
                                                      context=context, limit=1)
            if mail_message_id:
                # Do nothing
                call_old_message_post_flag = False
                result = mail_message_id[0]

                # Put a message in the logger to show that it was ignored on purpose
                logger.debug("The message: '{0}' has been ignored on purpose since it is duplicated".format(body_handled))

    if call_old_message_post_flag:
        result = old_message_post(self, cr, uid, thread_id, body, subject,
                                  type, subtype, parent_id, attachments,
                                  context, content_subtype, **kwargs)
    return result

mail_thread.message_post = new_message_post

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
