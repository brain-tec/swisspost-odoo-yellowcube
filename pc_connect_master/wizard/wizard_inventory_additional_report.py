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


class wizard_inventory_additional_report(osv.TransientModel):
    _name = 'pc_connect_master.wiz_inventory_additional_report'

    _columns = {
        'name': fields.char('Name'),
        'date': fields.date('Date to', required=True),
        'wiz_loc_id': fields.many2one('pc_connect_master.wiz_inventory_report'),
        'wiz_dest_id': fields.many2one('pc_connect_master.wiz_inventory_report'),
        'period': fields.many2one('account.period', 'Period'),
        'location_id': fields.many2one('stock.location', 'Stock Location', required=True),
        'location_dest_id': fields.many2one('stock.location', 'Customer Location', required=True),
    }

    def default_get(self, cr, uid, fields_list, context=None):
        ret = super(wizard_inventory_additional_report, self).default_get(cr, uid, fields_list, context)
        company = self.pool['res.users'].browse(cr, uid, uid, context).company_id
        shop_ids = self.pool['sale.shop'].search(cr, uid, [('company_id', '=', company.id)], context=context)
        if shop_ids:
            shop = self.pool['sale.shop'].browse(cr, uid, shop_ids[0], context)
            ret['location_id'] = shop.warehouse_id.lot_stock_id.id
            ret['location_dest_id'] = shop.warehouse_id.lot_output_id.id
        if 'period' not in ret:
            period_obj = self.pool['account.period']
            ret['period'] = period_obj.find(cr, uid, context=context)[0]
            ret['date'] = period_obj.browse(cr, uid, ret['period'],
                                            context=context).date_stop
        return ret

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

        report_obj = self.pool['pc_connect_master.wiz_inventory_report']
        wiz_loc_id = report_obj.create(cr, uid, {'date': wiz.date, 'location_id': wiz.location_id.id}, context)
        wiz_dest_id = report_obj.create(cr, uid, {'date': wiz.date, 'location_id': wiz.location_dest_id.id}, context)

        report_obj.action_open(cr, uid, wiz_loc_id, context)
        report_obj.action_open(cr, uid, wiz_dest_id, context)

        tree_id = self.pool['ir.model.data']\
            .get_object_reference(cr, uid,
                                  'pc_connect_master',
                                  'inventory_additional_report_summary')[1]
        name = _('Inventory Additional Analysis')
        if wiz.date:
            name = '%s (%s)' % (name, wiz.date)
        wiz.write({
            'name': name,
            'wiz_loc_id': wiz_loc_id,
            'wiz_dest_id': wiz_dest_id,
        })
        ctx = context.copy()
        ctx.update({
        })
        return {
            'name': name,
            'type': 'ir.actions.act_window',
            'res_model': 'pc_connect_master.inventory_additional_report',
            'res_id': False,
            'target': 'current',
            'context': ctx,
            'view_mode': 'tree',
            'domain': [('parent_id', '=', ids)],
            'views': [(tree_id, 'tree')]
        }


class inventory_additional_report(osv.osv):
    _name = 'pc_connect_master.inventory_additional_report'
    _auto = False
    _columns = {
        'product_id': fields.many2one('product.product', 'Product'),
        'qty': fields.float('Quantity In'),
        'qty_12': fields.float('Quantity Out on last 12 months'),
        'qty_3': fields.float('Quantity Out on last 3 months'),
        'qty_diff': fields.float('Quantity Different (In - Out 12 months)'),
        'parent_id': fields.many2one('pc_connect_master.wiz_inventory_additional_report', 'Report'),
        'date_first': fields.date('Date First move'),
        'stock_value': fields.float('Value'),
        'price': fields.float('Price'),
    }

    def init(self, cr):
        tools.drop_view_if_exists(cr, 'pc_connect_master_inventory_additional_report')
        cr.execute("""
CREATE OR REPLACE view pc_connect_master_inventory_additional_report AS (

SELECT
	"row_number" () OVER () AS ID,
	MIN (date_first) AS date_first,
	parent_id,
	report.product_id AS product_id,
	SUM (
		CASE
		WHEN report.internal THEN
			report.qty
		ELSE
			0
		END
	) AS qty,
	SUM (
		CASE
		WHEN report.internal THEN
			0
		ELSE
			report.qty_12
		END
	) AS qty_12,
	SUM (
		CASE
		WHEN report.internal THEN
			0
		ELSE
			report.qty_3
		END
	) AS qty_3,
	SUM (
		CASE
		WHEN report.internal THEN
			report.qty
		ELSE
			- report.qty_12
		END
	) AS qty_diff,
	SUM (report.stock_value) AS stock_value,
	MAX (report.price) AS price
FROM
	(
		SELECT
			qty,
			product_id,
			qty_12,
			qty_3,
			wiz. ID AS parent_id,
			date_first,
			stock_value,
			price,
			TRUE AS internal
		FROM
			pc_connect_master_inventory_report AS rep
		INNER JOIN pc_connect_master_wiz_inventory_additional_report AS wiz ON (parent_id = wiz.wiz_loc_id)
		UNION ALL
			SELECT
				qty,
				product_id,
				qty_12,
				qty_3,
				wiz. ID AS parent_id,
				date_first,
				0 AS stock_value,
				0 AS price,
				FALSE AS internal
			FROM
				pc_connect_master_inventory_report AS rep
			INNER JOIN pc_connect_master_wiz_inventory_additional_report AS wiz ON (parent_id = wiz.wiz_dest_id)
	) AS report
GROUP BY
	parent_id,
	product_id

)
        """)

inventory_additional_report()
