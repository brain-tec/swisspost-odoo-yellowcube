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
###############################################################################

from openerp.osv import fields, osv
from openerp.tools.translate import _
from openerp import tools


class wizard_inventory_report(osv.TransientModel):
    _name = 'pc_connect_master.wiz_inventory_report'

    _columns = {
        'name': fields.char('Name'),
        'min_date': fields.date('Date from'),
        'date': fields.date('Date to'),
        'period': fields.many2one('account.period', 'Period'),
        'product_id': fields.many2one('product.product', 'Product'),
        'default_code': fields.char('Default Code'),
        'alternative_code': fields.char('Alternative Code'),
        'parent_id': fields.many2one('pc_connect_master.wiz_inventory_report', 'Report'),
        'price': fields.float('Price'),
        'price_date': fields.date('Date last price change'),
        'location_id': fields.many2one('stock.location'),
    }

    def onchange_period(self, cr, uid, ids, period_id, context=None):
        period = self.pool['account.period'].browse(cr, uid, period_id,
                                                    context=context)
        return {
            'value': {
                'date': period.date_stop,
            }
        }

    def action_open(self, cr, uid, ids, context=None):
        if isinstance(ids, list):
            ids = ids[0]
        if context is None:
            context = {}
        else:
            context = context.copy()

        wiz = self.browse(cr, uid, ids, context=context)

        product_vals = {
            'parent_id': wiz.id,
            'date': wiz.date,
            'min_date': wiz.min_date,
            'location_id': wiz.location_id.id,
        }

        for product_id in self.pool['product.product'].search(cr, uid, [],
                                                              context=context):
            product = self.pool['product.product'].browse(cr, uid, product_id, context)
            product_date = None
            if product.standard_price_historical_ids:
                product_price = 0 if wiz.date else product.standard_price
                for line in product.standard_price_historical_ids:
                    if product_date is None or product_date < line.create_date:
                        if wiz.date:
                            if line.create_date[:10] <= wiz.date:
                                product_price = line.standard_price_value
                                product_date = line.create_date
                        else:
                            product_date = line.create_date
            else:
                product_price = product.standard_price
            product_vals2 = product_vals.copy()
            product_vals2.update({
                'product_id': product_id,
                'price': product_price,
                'price_date': product_date,
            })
            self.create(cr, uid, product_vals2, context)

        tree_id = self.pool['ir.model.data']\
            .get_object_reference(cr, uid,
                                  'pc_connect_master',
                                  'inventory_report_summary')[1]
        name = _('Inventory Analysis')
        if wiz.min_date:
            name = '%s (%s - %s)' % (name, wiz.min_date,
                                     wiz.date or wiz.create_date[:10])
        elif wiz.date:
            name = '%s (%s)' % (name, wiz.date)
        wiz.write({'name': name})
        ctx = context.copy()
        ctx.update({
            'search_default_group_location': True,
            'search_default_internal': True,
        })
        return {
            'name': name,
            'type': 'ir.actions.act_window',
            'res_model': 'pc_connect_master.inventory_report',
            'res_id': False,
            'target': 'current',
            'context': ctx,
            'view_mode': 'tree',
            'domain': [('parent_id', '=', ids)],
            'views': [(tree_id, 'tree')]
        }


class inventory_report(osv.osv):
    _name = 'pc_connect_master.inventory_report'
    _auto = False
    _columns = {
        'stock_value': fields.float('Value'),
        'price': fields.float('Price'),
        'product_id': fields.many2one('product.product', 'Product'),
        'default_code': fields.char('Default Code'),
        'alternative_code': fields.char('Alternative Code'),
        'qty': fields.float('Quantity'),
        'qty_12': fields.float('Quantity on last 12 months'),
        'qty_3': fields.float('Quantity on last 3 months'),
        'date_expected': fields.date('Date Last move'),
        'date_first': fields.date('Date First move'),
        'location_id': fields.many2one('stock.location', 'Location'),
        'location_usage': fields.char('Location type'),
        'parent_id': fields.many2one('pc_connect_master.wiz_inventory_report', 'Report'),
        'date': fields.date('Date last price change'),
    }

    def init(self, cr):
        tools.drop_view_if_exists(cr, 'pc_connect_master_inventory_report')
        cr.execute("""
CREATE OR REPLACE view pc_connect_master_inventory_report AS (

SELECT
	"row_number" () OVER () AS ID,
	report.product_id,
	report.default_code,
	report.alternative_code,
	report.location_id AS location_id,
	loc. USAGE AS location_usage,
	SUM (
		CASE
		WHEN report. DATE >= date_trunc(
			'month',
			wiz. DATE - INTERVAL '11 month'
		) THEN
			report.qty
		ELSE
			0
		END
	) AS qty_12,
	SUM (
		CASE
		WHEN report. DATE >= date_trunc(
			'month',
			wiz. DATE - INTERVAL '2 month'
		) THEN
			report.qty
		ELSE
			0
		END
	) AS qty_3,
	SUM (report.qty) AS qty,
	GREATEST (
		0,
		SUM (wiz.price * report.qty)
	) AS stock_value,
	MIN (wiz.price) AS price,
	MAX (wiz."price_date") AS DATE,
	MAX (report. DATE) AS date_expected,
	MIN (report. DATE) AS date_first,
	wiz.parent_id AS parent_id
FROM
	(
		SELECT
			DATE,
			product_id,
			default_code,
			alternative_code,
			location_id,
			- product_qty AS qty
		FROM
			stock_move AS sm,
			product_product AS pp
		WHERE
			sm."state" = 'done'
		AND sm.location_dest_id <> sm.location_id
		AND sm.product_id = pp.id
		UNION ALL
			SELECT
				DATE,
				product_id,
				default_code,
				alternative_code,
				location_dest_id AS location_id,
				product_qty AS qty
			FROM
				stock_move AS sm,
				product_product AS pp
			WHERE
				sm."state" = 'done'
			AND sm.location_dest_id <> sm.location_id
			AND sm.product_id = pp.id
	) AS report
INNER JOIN pc_connect_master_wiz_inventory_report wiz ON (
	wiz.product_id = report.product_id
)
INNER JOIN stock_location loc ON (loc. ID = report.location_id)
WHERE
	(
		wiz."date" IS NULL
		OR date_trunc('day', report."date") <= wiz."date"
	)
AND (
	wiz."min_date" IS NULL
	OR date_trunc('day', wiz."min_date") <= report."date"
)
AND (
	wiz.location_id IS NULL
	OR report.location_id = wiz.location_id
)
GROUP BY
	report.product_id,
	report.default_code,
	report.alternative_code,
	report.location_id,
	location_usage,
	parent_id
ORDER BY
	parent_id,
	report.location_id,
	product_id

)
        """)

inventory_report()
