# b-*- encoding: utf-8 -*-
##############################################################################
#
#    Copyright (c) 2014 brain-tec AG (http://www.brain-tec.ch)
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


# Used for selections which require selecting a Unit of Measure without making use of a relation.
UOM_AGING_SELECTION_VALUES = [('hours', 'Hour(s)'),
                              ('days', 'Day(s)'),
                              ]


class product_uom_ext(osv.Model):
    _inherit = 'product.uom'

    _columns = {
        'uom_iso': fields.char("ISO code"),
    }

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:=======
