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


class sale_exception_ext(osv.Model):
    _inherit = "sale.order"

    def write(self, cr, uid, ids, values, context=None):
        ret = super(sale_exception_ext, self).write(cr, uid, ids, values, context=None)
        if 'exceptions_ids' in values:
            # If an exception is created in a sale.order
            excep_values = values['exceptions_ids'][0]
            if excep_values[0] == 6:
                # Of type add
                except_obj = self.pool.get('sale.exception')
                issue_obj = self.pool.get('project.issue')
                if type(ids) is not list:
                    ids = [ids]
                for _id in ids:
                    # For each sale.order
                    for except_ in except_obj.browse(cr, uid, excep_values[2], context=context):
                        # And for each exception
                        for issue_id in issue_obj.find_resource_issues(cr,
                                                                        uid,
                                                                        'sale.order',
                                                                        ids[0],
                                                                        tags=['sale', 'sale-exception'],
                                                                        create=True,
                                                                        reopen=True,
                                                                        context=context):
                            # A message is trigger in a new/open issue
                            issue_obj.message_post(cr, uid, issue_id, _('Sale exception found.<br/><b>{0}</b>: {1}').format(except_.name, except_.description), context=context)
        return ret

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: