# b-*- encoding: utf-8 -*-
##############################################################################
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
##############################################################################
from openerp.osv import osv, fields
from openerp.tools.translate import _
import logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)



class res_partner_ext(osv.Model):
    _inherit = 'res.partner'

    def cron_main_tag_from_parent(self, cr, uid, context=None):
        ''' Copies the main tag from the parent or from the tags if it's empty.
            If silent is True the debug messages will not be shown.
            This functionality is in pc_connect_webshop since otherwise partners are always going to have a tag
            (it's mandatory in the user interface).
        '''
        if context is None:
            context = {}

        MSG_PARTNER_WITHOUT_MAIN_TAG = _("This partner doesn't have main tag.")

        is_mail_thread_no_duplicate_set = False
        if 'mail_thread_no_duplicate' in context:
            is_mail_thread_no_duplicate_set = True
        else:
            context['mail_thread_no_duplicate'] = True

        # Getting all partners ids without a main category assigned
        partner_without_main_category_ids = self.search(cr, uid, [('main_category_id', '=', None)], context=context)

        # Iteration over the partner objects without main category
        printed_err = False
        discrepancy_partner = None
        model_issue = self.pool.get('project.issue')

        # There are far more partners than different main tags, thus a way of speeding up
        # the process is making as many write() calls as tags we have, instead of calling
        # write() over every partner in the database with a missing tag.
        partner_ids_per_tag = {}

        # Partners with errors.
        partners_not_being_modified_ids = []

        num_partner = 0
        for partner in self.browse(cr, uid, partner_without_main_category_ids, context):
            num_partner += 1
            modified = False

            # Writing all of the main category field of a partner which has parent
            logger.debug('updating partner {0} (partner {1} out of {2})'.format(partner.id, num_partner, len(partner_without_main_category_ids)))

            if partner.parent_id and partner.parent_id.main_category_id:
                modified = True
                partner_ids_per_tag.setdefault(partner.parent_id.main_category_id.id, []).append(partner.id)

            # If the partner does't have a main tag we store it to log an issue later.
            if not modified:
                partners_not_being_modified_ids.append(partner.id)

        # Sets the main tag for those partners that can set one.
        for tag in partner_ids_per_tag:
            cr.execute("SAVEPOINT partner_main_tag_write;")
            try:
                self.write(cr, uid, partner_ids_per_tag[tag], {'main_category_id': tag}, context=context)
                cr.execute("RELEASE SAVEPOINT partner_main_tag_write;")
            except:
                partners_not_being_modified_ids.extend(partner_ids_per_tag[tag])
                cr.execute("ROLLBACK TO SAVEPOINT partner_main_tag_write;")

        # If some partner was not modified because of an error, we log issues.
        for partner_not_being_modified in self.browse(cr, uid, partners_not_being_modified_ids, context=context):
            # We save the first partner without main tag
            if not discrepancy_partner:
                discrepancy_partner = partner_not_being_modified.id
            logger.warning("Missed main category of a partner with ID: {0}".format(partner_not_being_modified.id))

            # An issue is created
            issue_ids = model_issue.find_resource_issues(cr, uid, 'res.partner', partner_not_being_modified.id, create=True, context=context, reopen=True, tags=['webshop'])
            for issue_id in issue_ids:
                model_issue.message_post(cr, uid, [issue_id], MSG_PARTNER_WITHOUT_MAIN_TAG, context=context)

        # Prints the first partner without main tag
        if discrepancy_partner:
            logger.warning("Missed main category of a partner with ID: {0}".format(discrepancy_partner))

        if not is_mail_thread_no_duplicate_set:
            del context['mail_thread_no_duplicate']

    def _check_partner_ref(self, cr, uid, ids, context=None):
        for partner in self.browse(cr, uid, ids, context=context):
            if not partner.ref and partner.webshop_account_id:
                partner.write({'ref': partner.webshop_account_id})
        return True

    _columns = {
        'webshop_account_id': fields.char('Webshop account', size=20),
        'webshop_address_id': fields.char('Webshop address', size=20),
    }

    _constraints = [(_check_partner_ref, 'In case this field is empty it would be set to the webshop_account_id', ['ref']),
                    ]

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
