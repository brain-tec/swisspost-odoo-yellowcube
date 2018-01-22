##OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2009 Tiny SPRL (<http://tiny.be>).
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
import netsvc

class account_tax_code_extended(osv.osv):
    _inherit = 'account.tax.code'

    def _get_code(self, cr, uid, ids, name, args, context=None):
        res = {}
        for tax_code in self.browse(cr, uid, ids, context):
            res[tax_code.id] = tax_code.value_for_tax_report_column_tax_hidden or tax_code.code
        return res
    
    def _set_code(self, cr, uid, id, name, value, args, context=None):
        return self.write(cr, uid, [id], {'value_for_tax_report_column_tax_hidden': value}, context=context)

    _columns = {
        'is_sales_tax':fields.boolean("Sales Tax", help="Check this box if this tax is a sales tax"),
        'active': fields.boolean('Active'),
        'show_in_tax_journal':fields.boolean("Show in tax journal", help="Check this box if you want this Tax Code to appear on tax journal"),
        'value_for_tax_report_column_tax': fields.function(_get_code, type="char", size=128, store=True, string='Tax text for details in tax report', fnct_inv=_set_code),
        'value_for_tax_report_column_tax_hidden': fields.char('Case Code', size=64),
    }

    _defaults = {
        'is_sales_tax': lambda *a: False,
        'active': lambda *args: 1,
        'show_in_tax_journal': lambda *a: False,
    }
    
    def _sum(self, cr, uid, ids, name, args, context, where ='', where_params=()):
#        print 'ids: ', ids
        parent_ids = tuple(self.search(cr, uid, [('parent_id', 'child_of', ids)]))
#        print 'parent_ids: ', parent_ids
        if context.get('based_on', 'invoices') == 'payments':
            cr.execute('SELECT line.tax_code_id, sum(line.tax_amount) \
                    FROM account_move_line AS line, \
                        account_move AS move \
                        LEFT JOIN account_invoice invoice ON \
                            (invoice.move_id = move.id) \
                    WHERE line.tax_code_id IN %s '+where+' \
                        AND move.id = line.move_id \
                        AND ((invoice.state = \'paid\') \
                            OR (invoice.id IS NULL)) \
                            GROUP BY line.tax_code_id',
                                (parent_ids,) + where_params)
        else:
            if len(parent_ids) > 0:
            #cr.execute('SELECT line.tax_code_id, sum(line.tax_amount) \
                cr.execute('SELECT line.tax_code_id, sum(line.debit - line.credit) AS tax_amount \
                        FROM account_move_line AS line, \
                        account_move AS move, \
                        account_tax_code AS tax_code_table \
                        WHERE line.tax_code_id IN %s '+where+' \
                        AND tax_code_table.id = line.tax_code_id \
                        AND move.id = line.move_id \
                        GROUP BY line.tax_code_id',
                           (parent_ids,) + where_params)
        res=dict(cr.fetchall())
        obj_precision = self.pool.get('decimal.precision')
        for record in self.browse(cr, uid, ids, context=context):
            def _rec_get(record):
                amount = res.get(record.id, 0.0)
                for rec in record.child_ids:
                    amount += _rec_get(rec) * rec.sign
                return amount
            res[record.id] = round(_rec_get(record), obj_precision.precision_get(cr, uid, 'Account'))
        return res
        return super(account_tax_code_extended, self)._sum(self, cr, uid, ids, name=name, args=args, context=context, where =where, where_params=where_params)

account_tax_code_extended()

