# b-*- encoding: utf-8 -*-
##############################################################################
#
#    Copyright (c) 2017 brain-tec AG (http://www.braintec-group.com)
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

from openerp.osv import osv, fields, orm


class sale_order_ext(osv.Model):
    _inherit = 'sale.order'

    _columns = {
        'creation_wab_datetime': fields.datetime(
            'Date & Time for WAB creation',
            help='The date & time in which the creation of the WAB was done '
                 'for the last picking of this '),
    }

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
