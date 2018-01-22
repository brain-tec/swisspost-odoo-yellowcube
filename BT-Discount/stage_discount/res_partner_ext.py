# b-*- encoding: utf-8 -*-
##############################################################################
#
#    Copyright (c) 2015 brain-tec AG (http://www.brain-tec.ch) 
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

from osv import fields,osv,orm
from tools.translate import _
from one2many_filter.generic import make_safe


class res_partner_ext(osv.osv):
    '''
    This class implements a default discount defined on the partner.
    We add a many2one on res.partner to a bt_stage_discount template.
    We also make an onchange on partner in account.invoice so it selected the
    stage_discount according to what was chosen in the respective partner.
    '''
    _inherit = "res.partner"
    _columns = {
        'use_parent_discount': fields.boolean('Use company discount', help="To use parent configuration."),
        'discount_template_id': fields.many2one('stage_discount.discount', 'Default discount',
                                                help="To define a default discount in an invoice using this partner."),
    }

    def get_discount_template(self, cr, uid, ids, context=None):
        '''
        Returns an integer with the id of the discount template.
        If the output is -1 then this partner does not have a default discount template.
        '''
        (context, ids) = make_safe(context, ids)
        partner = self.browse(cr, uid, ids, context)[0]
        if partner.use_parent_discount:
            if partner.parent_id:
                return self.get_discount_template(cr, uid, partner.parent_id.id, context)
            else:
                # use_parent_discount flag is set but no parent is defined
                return -1
        else:
            if partner.discount_template_id:
                return partner.discount_template_id.id
            else:
                return -1
