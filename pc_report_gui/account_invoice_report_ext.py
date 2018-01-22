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


class account_invoice_report_ext(osv.Model):
    _inherit = 'account.invoice.report'

    _columns = {
        'partner_main_category_id': fields.many2one('res.partner.category', "Partner's Main Category", readonly=True),
        'payment_date': fields.date('Payment Date', readonly=True),
        'product_name': fields.char('Name', readonly=True),
        'product_default_code': fields.char('Default Code', readonly=True),
        'price_total_with_taxes': fields.float('Total With Tax', readonly=True),
        'invoice_origin': fields.char('Origin', readonly=True),
        'invoice_name': fields.char('Name', readonly=True),

        # Functional fields used to allow a direct search from the search-box.
        'date_invoice_from': fields.function(lambda *a, **k: {}, method=True, type='date', string='Invoice Date from'),
        'date_invoice_to': fields.function(lambda *a, **k: {}, method=True, type='date', string='Invoice Date to'),
    }

    def _select(self):
        ''' Extends the original _select().
        '''
        old_select = super(account_invoice_report_ext, self)._select()
        new_select = '''{0},
                        sub.partner_main_category_id,
                        sub.payment_date,
                        sub.product_default_code,
                        sub.product_name,
                        sub.invoice_origin,
                        sub.invoice_name,
                        sub.price_total_with_taxes / cr.rate as price_total_with_taxes '''.format(old_select)
        return new_select

    def _sub_select(self):
        ''' Extends the sub-query.
        '''
        old_sub_select = super(account_invoice_report_ext, self)._sub_select()
        new_sub_select = '''{0},
                            (SELECT main_category_id
                             FROM res_partner rp
                             WHERE rp.id = ai.partner_id)
                             AS partner_main_category_id,

                             ai.payment_date AS payment_date,

                            (SELECT prod_templ.name
                             FROM product_product prod, product_template prod_templ
                             WHERE ail.product_id = prod.id
                             AND prod.product_tmpl_id = prod_templ.id)
                             AS product_name,

                            (SELECT prod.default_code
                             FROM product_product prod
                             WHERE ail.product_id = prod.id)
                             AS product_default_code,

                            SUM(CASE
                                  WHEN ai.type::text = ANY (ARRAY['out_refund'::character varying::text, 'in_invoice'::character varying::text])
                                    THEN - ail.price_total
                                    ELSE ail.price_total
                                END) AS price_total_with_taxes,
                                
                            ai.origin AS invoice_origin,
                            ai.number AS invoice_name
                        '''.format(old_sub_select)
        return new_sub_select

    def _group_by(self):
        ''' Extends the group by clause.
        '''
        old_group_by = super(account_invoice_report_ext, self)._group_by()
        new_group_by = '''{0},
                          partner_main_category_id,
                          payment_date,
                          product_name,
                          product_default_code '''.format(old_group_by)
        return new_group_by

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
