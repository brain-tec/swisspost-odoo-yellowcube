# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>).
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
import openerp
import logging
logger = logging.getLogger(__name__)



class mail_mail_ext(osv.osv):
    _inherit = 'mail.mail'
    """
    Two new input parameters in the config file:
        -- bt_send_mail_filter = True | False
        -- bt_send_mail_db_names = string ( list of database, separated by comas)

    if bt_send_mail_filter does not exists:
        Send mails.
    else:
        if bt_send_mail_filter is True:
               if bt_send_mail_db_names does not exist:
                     Change destination emails to null and "send" the e-mail.
               else:
                    if current database is in bt_send_mail_db_names:
                           Send mails.
                    else:
                          Change destination emails to null and "send" the e-mail.
        else:
              Send mails.
    """

    def send(self, cr, uid, ids, auto_commit=False, recipient_ids=None, context=None):
        bt_send_mail_filter = False
        logger.debug("Sending mails!!")
        try:
            bt_send_mail_filter = openerp.tools.config['bt_send_mail_filter']
            logger.debug("There is the bt_send_mail_filter variable in the config file with value {0}.".format(openerp.tools.config['bt_send_mail_filter']))
        except:
            logger.debug("There is not existing bt_send_mail_filter variable in the config file. The emails are sent")
            pass

        if not bt_send_mail_filter:
            return super(mail_mail_ext, self).send(cr, uid, ids, auto_commit, recipient_ids, context)

        send_mail_db_names = []
        try:
            send_mail_db_names = openerp.tools.config['bt_send_mail_db_names']
            if send_mail_db_names:
                send_mail_db_names = send_mail_db_names.split(",")
        except:
            logger.debug("There is not defined bt_send_mail_db_names database => The emails are not sent")
            pass
        # Check, if the running DB is allowed to execute the function
        logger.debug("Current database {0} => Allowed databases".format(cr.dbname))
        if cr.dbname not in send_mail_db_names:
            logger.debug("The emails are not sent with this destination")
            self.write(cr, uid, ids, {'state': 'exception'})
            return True
        else:
            logger.debug("Emails sent with the correct destination")
            return super(mail_mail_ext, self).send(cr, uid, ids, auto_commit, recipient_ids, context)
