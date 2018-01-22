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
import test_yc_input_wbl
import test_yc_wab_war
import test_yc_wba_delivery
import test_yc_wba_summary_and_wba0
import test_yc_wbl_wba
import test_yc_art
import test_yc_bar
import test_yc_bur
import test_xmltools
import test_fds
import test_ean
import test_picking_in_split_lots


checks = [
    test_yc_wab_war,
    test_yc_wba_delivery,
    test_yc_wbl_wba,
    test_yc_art,
    test_yc_bar,
    test_yc_bur,
    test_xmltools,
    test_fds,
    test_ean,
    test_picking_in_split_lots,
]

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
