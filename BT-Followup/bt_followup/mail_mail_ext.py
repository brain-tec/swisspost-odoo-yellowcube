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

from osv import fields, osv


class mail_mail(osv.osv):
    _inherit = "mail.mail"
    _columns = {
        'followup_invoice_ids': fields.many2many('account.invoice', 'followup_invoice_mail_rel', 'mail_id', 'invoice_id',
                                                 string="Invoices in Mail",),

        'followup_partner_id':
            fields.many2one('res.partner', 'Partner', readonly=True),
    }


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
