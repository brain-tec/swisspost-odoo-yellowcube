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



class fetchmail_server_ext(osv.osv):
    _inherit = 'fetchmail.server'
    """
    Two new input parameters in the config file:
        -- bt_fetch_mail_filter = True | False
        -- bt_fetch_mail_db_names = comma-separated list of db names

    if bt_fetch_mail_filter is not defined:
        Fetch mails
    else:
        if bt_fetch_mail_filter is False:
            Fetch mails.
        else:
            if bt_fetch_mail_db_names is not defined:
                Do not fetch mails
            else:
                Fetch mails if current db name is in bt_fetch_mail_db_names

    """
    def fetch_mail(self, cr, uid, ids, context=None):
        logger.debug("FETCH MAIL!!")
        bt_fetch_mail_filter = False

        try:
            bt_fetch_mail_filter = openerp.tools.config['bt_fetch_mail_filter']
            logger.debug('bt_fetch_mail_filter defined in config file as '
                         '"{0}"'.format(openerp.tools.config['bt_fetch_mail_filter']))
        except:
            logger.debug('bt_fetch_mail_filter not defined in config file: emails are fetched')

        if not bt_fetch_mail_filter:
            return super(fetchmail_server_ext, self).fetch_mail(cr, uid, ids, context)

        fetch_mail_db_names = []

        try:
            fetch_mail_db_names = openerp.tools.config['bt_fetch_mail_db_names']
            if fetch_mail_db_names:
                fetch_mail_db_names = fetch_mail_db_names.split(",")
        except:
            logger.debug('bt_fetch_mail_db_names not defined in config file: emails NOT fetched')
            return True

        logger.debug('Allowed databases: {0}'.format(cr.dbname))

        if cr.dbname in fetch_mail_db_names:
            logger.debug('Emails fetched')
            return super(fetchmail_server_ext, self).fetch_mail(cr, uid, ids, context)

        logger.debug('Emails NOT fetched')

        return True

fetchmail_server_ext()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
