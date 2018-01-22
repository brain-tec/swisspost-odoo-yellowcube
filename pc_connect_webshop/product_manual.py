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

from openerp.osv import osv, fields
from openerp.tools.translate import _


class product_manual(osv.osv):
    ''' Links the product's manuals to its corresponding product.
    '''

    _name = 'product.manual'

    _columns = {
        'product_id': fields.many2one('product.product', 'Product', required=True, help='The product this manual relates to.'),
        'description': fields.char('Description of the type of manual', required=True, size=128, translate=True, help='Type of the manual (e.g. user manual, safety-use manual, etc.).'),
        'language_id': fields.many2one('res.lang', 'Language', required=True, ondelete='restrict', domain="[('active', '=', 'TRUE')]", help='The language of the manual.'),
        'attachment_id': fields.many2one('ir.attachment', 'URL Attachment', required=True, ondelete='restrict', help='The URL to the file of the manual, as an attachment.'),
    }

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
