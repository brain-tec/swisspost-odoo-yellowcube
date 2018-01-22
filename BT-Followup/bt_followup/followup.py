# b-*- encoding: utf-8 -*-
#
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
#

from openerp.osv import fields, osv
from openerp.tools.translate import _


class followup(osv.osv):
    _name = 'followup'

    _columns = {
        'followup_create_date': fields.date('Follow-up Creation Date',
                                            help='The date in which the follow-up was created'),
        'followup_handled_date': fields.date('Follow-up Handled Date',
                                             help='The date in which the follow-up was handled'),
        'followup_level_id':
            fields.many2one('followup.level', 'Follow-up Level'),
        'invoice_followup_id':
            fields.many2one('account.invoice', 'Penalization Invoice'),
        'followup_parent_id':
            fields.many2one('account.invoice', 'Follow-up Invoice'),
        'email_id': fields.many2one('mail.mail', 'Mail', ondelete="restrict"),
        'email_subject': fields.related('email_id', 'mail_message_id', 'subject', type='text',
                                        string='Email Subject', store=False),
        'email_date': fields.related('email_id', 'mail_message_id', 'date',
                                     type='datetime', string='Email Date', store=False),
        # 'followup_partner_id': fields.related('followup_parent_id', 'partner_id',
        # type="many2one", relation="res.partner", string="Partner",
        # store=True),
        'followup_partner_id': fields.many2one('res.partner', 'Partner'),
    }
    _sql_constraints = [
        ('unique followup_level_per_invoice', 'UNIQUE(followup_parent_id, followup_level_id)',
         _('One invoice can only has a followup per different level.')),
    ]


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
