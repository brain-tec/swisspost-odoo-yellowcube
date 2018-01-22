# b-*- encoding: utf-8 -*-
##############################################################################
#
#    Copyright (c) 2014 brain-tec AG (http://www.braintec-group.com)
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

import os
from datetime import timedelta, datetime
from openerp.addons.report_webkit import report_sxw_ext
from openerp.tools.translate import _
from openerp.tools import mod10r
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT
from openerp.addons.pc_generics import generics_bvr
from openerp.addons.pc_generics import generics
from openerp.addons.pc_log_data.log_data import write_log
from openerp.addons.pc_connect_master.utilities.reports import \
    delete_report_from_db



class invoice_followup_report_ext(generics.report_ext):

    def __init__(self, cr, uid, name, context):
        super(invoice_followup_report_ext, self).__init__(cr, uid, name, context=context)
        self.localcontext.update({
            'mod10r': mod10r,
            'get_top_of_css_class': self.get_top_of_css_class,
            'get_followup_title': self.get_followup_title,
            '_space': self._space,
            '_get_ref': self._get_ref,
            # 'get_followup_level_text': self._get_followup_level_text,
        })

    def get_top_of_css_class(self, class_name, context=None):
        return str(generics_bvr.bvr_css_top_measures[class_name]).replace(',', '.')

    def get_followup_title(self, invoice_obj, context=None):
        followup_title = _('Mahnung')
        if invoice_obj.followup_level_id:
            followup_title = invoice_obj.followup_level_id.name
        return followup_title

    def _space(self, nbr, nbrspc=5, context=None):
        return generics_bvr._space(nbr, nbrspc)

    def _get_ref(self, inv, context=None):
        return generics_bvr._get_ref(inv)

mako_path = os.path.abspath(os.path.join(os.path.dirname(__file__), 'invoice_followup_report.mako'))
delete_report_from_db('invoice_followup_report')
report_sxw_ext.report_sxw_ext('report.invoice_followup_report',
                              'account.invoice',
                              mako_path,
                              parser=invoice_followup_report_ext)

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
