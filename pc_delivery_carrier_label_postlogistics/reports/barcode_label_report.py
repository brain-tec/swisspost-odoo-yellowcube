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

from openerp.addons.report_webkit import report_sxw_ext
import os
from openerp.addons.pc_generics import generics
from tools.translate import _
import math
from openerp.osv import osv, fields


class barcode_label_report(generics.report_ext):

    def __init__(self, cr, uid, name, context):
        super(barcode_label_report, self).__init__(cr, uid, name, context=context)
        self.localcontext.update({'get_top_of_css_class': self.get_top_of_css_class,
                                  })

    def get_top_of_css_class(self, configuration_data, class_name, context=None):
        HEIGHT_DINA4 = 297  # Millimetres.
        return str(self._page_num * HEIGHT_DINA4 + configuration_data[class_name]).replace(',', '.')


mako_path = os.path.abspath(os.path.join(os.path.dirname(__file__), 'barcode_label.mako'))
report_sxw_ext.report_sxw_ext('report.barcode_label_report',
                              'stock.picking.out',
                              mako_path,
                              parser=barcode_label_report)

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
