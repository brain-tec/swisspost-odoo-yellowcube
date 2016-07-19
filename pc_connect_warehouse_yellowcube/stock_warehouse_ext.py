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
from openerp.osv import osv, fields
from openerp.tools.translate import _
import logging
#from yellowcube_bar_xml_factory import get_list_of_products_missing_in_bar_for_long_time
#from yellowcube_bar_xml_factory import get_num_days_product_not_in_bar
logger = logging.getLogger(__name__)
from xml_abstract_factory import deprecated


class stock_warehouse_ext(osv.osv):
    _inherit = "stock.warehouse"

    # This method is not yet ported into the new connector structure
    @deprecated
    def check_yellowcube_bar_missing(self, cr, uid, context=None):
        ''' Checks which products did not appeared in the BAR for a long time, and logs an issue on them.
            Sends an email with the list of products.
        '''
        if context is None:
            context = {}

        missing_ids = get_list_of_products_missing_in_bar_for_long_time(self, cr, uid, [], context=context)
        if missing_ids:
            issue_obj = self.pool.get('project.issue')
            for product_id in missing_ids:
                issue_ids = issue_obj.find_resource_issues(cr, uid, 'product.product', product_id,
                                                           tags=['missing-bar', 'lot', 'warehouse-error'],
                                                           create=True, reopen=True, context=context)
                for issue in issue_obj.browse(cr, uid, issue_ids, context=context):
                    issue.message_post(_('Out-of-sync with BAR file'))

            # Sends the email.
            mail_template_id = self.pool.get('ir.model.data').get_object_reference(cr, uid, 'pc_yellow_cube_export', 'email_template_bar_products_absent')[1]
            warehouse_id = self.pool.get('stock.warehouse').search(cr, uid, [], limit=1, context=context)[0]  # Just one warehouse's ID to fill in the template.
            self.pool.get('email.template').send_mail(cr, uid, mail_template_id, warehouse_id, context=context)

        return True

    # This method is not yet ported into the new connector structure
    @deprecated
    def get_support_bar_email(self, cr, uid, ids, context=None):
        ''' Gets the email address that is going to be used to send the list of products which
            did not appear in the BAR for a certain amount of days.
        '''
        if context is None:
            context = {}
        configuration_data = self.pool.get('configuration.data').get(cr, uid, [])
        return configuration_data.bar_checking_support_bar_email

    # This method is not yet ported into the new connector structure
    @deprecated
    def get_num_days_product_not_in_bar(self, cr, uid, ids, context=None):
        ''' This is used to fill in the email template.
        '''
        if context is None:
            context = {}
        return get_num_days_product_not_in_bar(self, cr, uid, ids, context)

    # This method is not yet ported into the new connector structure
    @deprecated
    def get_html_list_of_products_missing_in_bar_for_long_time(self, cr, uid, ids, context=None):
        ''' This is used to fill in the email template.
        '''
        if context is None:
            context = {}
        product_ids_to_inspect = get_list_of_products_missing_in_bar_for_long_time(self, cr, uid, ids, context)

        list_html_list = ['<ul>']
        product_obj = self.pool.get('product.product')
        for product_id in product_ids_to_inspect:
            product_name = product_obj.browse(cr, uid, product_id, context=context).name_template
            list_html_list.append('<li>{0}</li>'.format(product_name))
        list_html_list.append('</ul>')
        return '\n'.join(list_html_list)

    _columns = {
        'lot_blocked_id': fields.many2one('stock.location', 'Location Blocked', required=False, domain=[('usage', '=', 'internal')]),
        'lot_scrapping_id': fields.many2one('stock.location', 'Location Scrapping', required=False, domain=[('usage', '=', 'internal')]),
    }

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
