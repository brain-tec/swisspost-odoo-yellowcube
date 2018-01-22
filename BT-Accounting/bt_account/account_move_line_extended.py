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
from tools.translate import _
from operator import itemgetter
import decimal_precision as dp

class account_move_line_extended(osv.osv):
    _inherit = 'account.move.line'
    
    #ok
    def _balance_ext(self, cr, uid, ids, name, args, context=None):
        result = {}
        for line in self.browse(cr, uid, ids, context=context):
            result[line.id] = 0.0
            result[line.id] += line.debit - line.credit
        return result
    #no change, just because balance was overwritten 
    def _balance_search_ext(self, cursor, user, obj, name, args, domain=None, context=None):
        if context is None:
            context = {}
        if not args:
            return []
        where = ' AND '.join(map(lambda x: '(abs(sum(debit-credit))'+x[1]+str(x[2])+')',args))
        cursor.execute('SELECT id, SUM(debit-credit) FROM account_move_line \
                     GROUP BY id, debit, credit having '+where)
        res = cursor.fetchall()
        if not res:
            return [('id', '=', '0')]
        return [('id', 'in', [x[0] for x in res])]
    
    #should be not needed for version 7
#     def onchange_account_id_new(self, cr, uid, ids, account_id=False, journal_id=False, period_id=False, date=False, partner_id=False):
#         print 'onchange_account_id_new'
# #        print 'account_id: ', account_id
# #        print 'journal_id: ', journal_id
# #        print 'period_id: ', period_id 
#         account_obj = self.pool.get('account.account')
#         partner_obj = self.pool.get('res.partner')
#         fiscal_pos_obj = self.pool.get('account.fiscal.position')
#         val = {}
#         #hack jool: 6.1 - added these 3 values to vals
#         val['journal_id'] = journal_id
#         val['period_id'] = period_id
#         val['date'] = date
#         if account_id:
#             res = account_obj.browse(cr, uid, account_id)
#             print 'res: ', res
#             tax_ids = res.tax_ids
#             print 'tax_ids: ', tax_ids
#             if tax_ids and partner_id:
#                 part = partner_obj.browse(cr, uid, partner_id)
#                 tax_id = fiscal_pos_obj.map_tax(cr, uid, part and part.property_account_position or False, tax_ids)[0]
#             else:
#                 tax_id = tax_ids and tax_ids[0].id or False
#             val['account_tax_id'] = tax_id
#             #hack jool: get tax_code_id of tax_id
#             if tax_id:
#                 tax = self.pool.get('account.tax').browse(cr,uid,tax_id)
#                 val['tax_code_id'] = tax.tax_code_id.id
#             else:
#                 val['tax_code_id'] = False
#         return {'value': val}


#gibt es so in version 7 nicht mehr!!    
#     def fields_view_get(self, cr, uid, view_id=None, view_type='form', context=None, toolbar=False, submenu=False):
#         print 'account_move_line_extended fields_view_get'
#         journal_pool = self.pool.get('account.journal')
#         if context is None:
#             context = {}
#         result = super(account_move_line_extended, self).fields_view_get(cr, uid, view_id, view_type, context=context, toolbar=toolbar, submenu=submenu)
#         if view_type != 'tree':
#             #Remove the toolbar from the form view
#             if view_type == 'form':
#                 if result.get('toolbar', False):
#                     result['toolbar']['action'] = []
#             #Restrict the list of journal view in search view
#             if view_type == 'search' and result['fields'].get('journal_id', False):
#                 result['fields']['journal_id']['selection'] = journal_pool.name_search(cr, uid, '', [], context=context)
#                 ctx = context.copy()
#                 #we add the refunds journal in the selection field of journal
#                 if context.get('journal_type', False) == 'sale':
#                     ctx.update({'journal_type': 'sale_refund'})
#                     result['fields']['journal_id']['selection'] += journal_pool.name_search(cr, uid, '', [], context=ctx)
#                 elif context.get('journal_type', False) == 'purchase':
#                     ctx.update({'journal_type': 'purchase_refund'})
#                     result['fields']['journal_id']['selection'] += journal_pool.name_search(cr, uid, '', [], context=ctx)
#             return result
#         if context.get('view_mode', False):
#             return result
#         fld = []
#         fields = {}
#         flds = []
#         title = _("Accounting Entries") #self.view_header_get(cr, uid, view_id, view_type, context)
#         
#         # hack by gafr1
#         # This hack is made for fsch_accounting to show the account.move.line tree view not editable
#         # To show the account.move.line tree view not editable, you can set 'editable' to False in the context.
#         if context.get('editable', True):
#             xml = '''<?xml version="1.0"?>\n<tree string="%s" editable="top" refresh="5" on_write="on_create_write" colors="red:state==\'draft\';black:state==\'valid\'">\n\t''' % (title)
#         else:
#             xml = '''<?xml version="1.0"?>\n<tree string="%s" refresh="5" on_write="on_create_write" colors="red:state==\'draft\';black:state==\'valid\'">\n\t''' % (title)
# 
#         ids = journal_pool.search(cr, uid, [])
#         journals = journal_pool.browse(cr, uid, ids, context=context)
#         all_journal = [None]
#         common_fields = {}
#         total = len(journals)
#         for journal in journals:
#             all_journal.append(journal.id)
#             for field in journal.view_id.columns_id:
#                 if not field.field in fields:
#                     fields[field.field] = [journal.id]
#                     fld.append((field.field, field.sequence, field.name))
#                     flds.append(field.field)
#                     common_fields[field.field] = 1
#                 else:
#                     fields.get(field.field).append(journal.id)
#                     common_fields[field.field] = common_fields[field.field] + 1
#         fld.append(('period_id', 3, _('Period')))
#         fld.append(('journal_id', 10, _('Journal')))
#         flds.append('period_id')
#         flds.append('journal_id')
#         fields['period_id'] = all_journal
#         fields['journal_id'] = all_journal
#         fld = sorted(fld, key=itemgetter(1))
#         widths = {
#             'statement_id': 50,
#             'state': 60,
#             'tax_code_id': 50,
#             'move_id': 40,
#         }
#         for field_it in fld:
#             field = field_it[0]
#             if common_fields.get(field) == total:
#                 fields.get(field).append(None)
# #            if field=='state':
# #                state = 'colors="red:state==\'draft\'"'
#             attrs = []
#             if field == 'debit':
#                 attrs.append('sum = "%s"' % _("Total debit"))
# 
#             elif field == 'credit':
#                 attrs.append('sum = "%s"' % _("Total credit"))
# 
#             #hack jool: added balance
#             elif field == 'balance':
#                 attrs.append('sum = "%s"' % _("Saldo"))
# 
#             elif field == 'move_id':
#                 attrs.append('required = "False"')
# 
#             elif field == 'account_tax_id':
#                 attrs.append('domain="[(\'parent_id\', \'=\' ,False)]"')
#                 attrs.append("context=\"{'journal_id': journal_id}\"")
# 
#             elif field == 'account_id' and journal.id:
#                 attrs.append('domain="[(\'journal_id\', \'=\', '+str(journal.id)+'),(\'type\',\'&lt;&gt;\',\'view\'), (\'type\',\'&lt;&gt;\',\'closed\')]" on_change="onchange_account_id(account_id, partner_id)"')
# 
#             elif field == 'partner_id':
#                 attrs.append('on_change="onchange_partner_id(move_id, partner_id, account_id, debit, credit, date, journal_id)"')
# 
#             elif field == 'journal_id':
#                 attrs.append("context=\"{'journal_id': journal_id}\"")
# 
#             elif field == 'statement_id':
#                 attrs.append("domain=\"[('state', '!=', 'confirm'),('journal_id.type', '=', 'bank')]\"")
# 
#             elif field == 'date':
#                 attrs.append('on_change="onchange_date(date)"')
# 
#             elif field == 'analytic_account_id':
#                 attrs.append('''groups="analytic.group_analytic_accounting"''') # Currently it is not working due to framework problem may be ..
# 
#             if field in ('amount_currency', 'currency_id'):
#                 attrs.append('on_change="onchange_currency(account_id, amount_currency, currency_id, date, journal_id)"')
#                 attrs.append('''attrs="{'readonly': [('state', '=', 'valid')]}"''')
# 
#             if field in widths:
#                 attrs.append('width="'+str(widths[field])+'"')
# 
#             if field in ('journal_id',):
#                 attrs.append("invisible=\"context.get('journal_id', False)\"")
#             elif field in ('period_id',):
#                 attrs.append("invisible=\"context.get('period_id', False)\"")
#             else:
#                 attrs.append("invisible=\"context.get('visible_id') not in %s\"" % (fields.get(field)))
#             xml += '''<field name="%s" %s/>\n''' % (field,' '.join(attrs))
# 
#         xml += '''</tree>'''
#         result['arch'] = xml
#         result['fields'] = self.fields_get(cr, uid, flds, context)
#         return result
        
    _columns = {
        'date_maturity_start': fields.date('Maturity start date', select=True ,help="This field is used only for the wizard to get the move lines which have to be payed."),
        #'balance': fields.function(_balance, method=True, string="Balance"),
        'balance': fields.function(_balance_ext, fnct_search=_balance_search_ext, string='Balance'),
        'tax_amount_base': fields.float('Tax/Base Amount Base', digits_compute=dp.get_precision('Account'), select=True, help="Base of field tax_amount"),
    }
    
account_move_line_extended()

