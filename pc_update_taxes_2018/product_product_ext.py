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
###############################################################################

from openerp.osv import osv, fields
from openerp.tools.translate import _
import logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


# Dictionary to map the taxes, from old to new (yes, new ones are lower!)
_TAX_MAPPING = {
    '8.0% achat': '7.7% achat',
    '8.0%': '7.7%',
    '8.0% invest.': '7.7% invest.',
    '8.0% C+C': '7.7% C+C',
    '3.8% achat': '3.7% achat',
    '3.8%': '3.7%',
    '3.8% invest': '3.7% invest.',
}


class product_product_ext(osv.Model):
    _inherit = 'product.product'

    def cron_update_taxes_in_products(self, cr, uid, context=None):
        """ Updates the taxes on all the products, according to the
            fixed mapping provided above.
        """
        if context is None:
            context = {}

        tax_obj = self.pool.get('account.tax')
        issue_obj = self.pool.get('project.issue')
        user_obj = self.pool.get('res.users')

        for old_tax_name, new_tax_name in _TAX_MAPPING.iteritems():
            old_tax_ids = tax_obj.search(cr, uid, [
                ('description', '=', old_tax_name),
            ], context=context)
            new_tax_ids = tax_obj.search(cr, uid, [
                ('description', '=', new_tax_name),
            ], context=context)

            # Checks that the given taxes exists, otherwise informs in the log.
            errors = []
            if len(old_tax_ids) == 0:
                errors.append("Old tax {0} was not found".format(
                    old_tax_name))
            elif len(old_tax_ids) > 1:
                errors.append("Old tax {0} was found several times".format(
                    old_tax_name))
            if len(new_tax_ids) == 0:
                errors.append("New tax {0} was not found".format(
                    new_tax_name))
            elif len(new_tax_ids) > 1:
                errors.append("New tax {0} was found several times".format(
                    new_tax_name))

            # The change of taxes is done only if there were no errors at all
            # for the tax being substituted, otherwise a log line & issue are
            # created to inform the user.
            if errors:
                errors_str = ';'.join(errors)
                logger.info("NEW YEAR 2018 Tax Errors: {0}".format(errors_str))

                user = user_obj.browse(cr, uid, uid, context=context)
                issue_obj.create_issue(
                    cr, uid, 'res.company', user.company_id.id, errors_str,
                    context=context)

            else:
                old_tax_id = old_tax_ids[0]
                new_tax_id = new_tax_ids[0]

                # Replaces this tax on the customer taxes for the products:
                # removes the old one, and adds the new one if is not set yet,
                # for both the customer and supplier taxes.
                for tax_field in ['taxes_id', 'supplier_taxes_id']:

                    # Removes the old taxes.
                    prod_having_old_customer_tax_ids = self.search(cr, uid, [
                        ('active', 'in', [True, False]),
                        (tax_field, 'in', old_tax_id),
                    ], context=context)
                    self.write(cr, uid, prod_having_old_customer_tax_ids, {
                        tax_field: [(3, old_tax_id)],
                    }, context=context)

                    # Sets the new taxes, only if it is not set yet.
                    prod_to_have_new_customer_tax_ids = self.search(cr, uid, [
                        ('id', 'in', prod_having_old_customer_tax_ids),
                        ('active', 'in', [True, False]),
                        (tax_field, 'not in', new_tax_id),
                    ], context=context)
                    self.write(cr, uid, prod_to_have_new_customer_tax_ids, {
                        tax_field: [(4, new_tax_id)],
                    }, context=context)

        return True

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
