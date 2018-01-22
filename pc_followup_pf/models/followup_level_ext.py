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

import os
from openerp.osv import fields, osv
from openerp.tools.translate import _


_FOLLOWUP_ROUTING = [
    ('same_as_invoice', 'Same as invoice'),
    ('force_email', 'Force email'),
    ('force_docout', 'Force doc-out'),
]


class followup_level_ext(osv.osv):
    _inherit = 'followup.level'

    def get_followup_level_number(self, cr, uid, ids, context=None):
        """ Returns an integer indicating the order of the follow-up, starting
            in one. The order is taken by ordering the delay.
        """
        if context is None:
            context = {}
        if not isinstance(ids, list):
            ids = [ids]
        assert len(ids) == 1, 'ids must be a 1-element list.'

        current_level = self.browse(cr, uid, ids[0], context=context)

        level_number = self.search(cr, uid, [
            ('followup_config_id', '=', current_level.followup_config_id.id),
            ('delay', '<=', current_level.delay),
        ], order='delay ASC', count=True, context=context)

        return level_number

    def _check_max_2_lines_letter_title(self, cr, uid, ids):
        """ The maximum number of lines for the title of the letter is 2,
            and this is fixed and super-hardcoded, because the template is
            like that...
        """
        for this in self.browse(cr, uid, ids):
            if this.letter_title and len(this.letter_title.strip(
                    os.linesep).split(os.linesep)) > 2:
                return False
        return True

    _columns = {
        'invoice_routing': fields.selection(
            _FOLLOWUP_ROUTING, string='Follow-up Routing',
            help='Indicates where to send the follow-up.'),

        'report_account_invoice': fields.many2one(
            'ir.actions.report.xml', 'Follow-up Report',
            domain=[('model', '=', 'account.invoice')],
            help='If set, this follow-up level uses this template instead '
                 'of the default one.'),

        'letter_title': fields.text(
            'Title of the letter',
            help='When the letter is generated, this text will appear as '
                 'the title, just below the name of the follow-up level.'),

        'carrier_id': fields.many2one(
            'delivery.carrier', 'Carrier',
            help='The carrier for the invoice generated because of the '
                 'follow-up, needed for the generation of the barcode label.'),

        'use_barcode_address': fields.boolean(
            'Use barcode label?',
            help='If checked, generates a barcode label that is placed on '
                 'the address window of the letter.'),

        'docout_email_template_id': fields.many2one(
            'email.template', 'Email Template for the Email Docout',
            domain=[('model', '=', 'account.invoice')],
            help='The email template for the email which sends '
                 'the invoice via doc-out.'),
    }

    _defaults = {
        'invoice_routing': 'same_as_invoice',
    }

    _constraints = [
        (_check_max_2_lines_letter_title,
         "The title of the letter can only have 2 lines maximum.",
         ['letter_title']),
    ]

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
