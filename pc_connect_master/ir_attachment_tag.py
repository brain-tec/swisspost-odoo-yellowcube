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
from openerp.tools.translate import _


class ir_attachment_tag(osv.Model):
    """ Tags an attachment.
    """
    _name = 'ir.attachment.tag'

    def get_tag_id(self, cr, uid, ids, tag_name, context=None):
        """ Returns the ID of the tag having the provided name. Creates it
            if doesn't exist.
        """
        tag_ids = self.search(cr, uid, [
            ('name', '=', tag_name),
        ], limit=1, context=context)
        if not tag_ids:
            tag_id = self.create(cr, uid, {'name': tag_name}, context=context)
        else:
            tag_id = tag_ids[0]
        return tag_id

    _columns = {
        'name': fields.char('Name'),
    }

    _sql_constraints = [
        ('name_unique', 'unique(name)',
         'No duplicated tag names are allowed.'),
    ]

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
