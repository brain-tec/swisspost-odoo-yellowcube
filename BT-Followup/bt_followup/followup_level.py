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


class followup_level(osv.osv):

    def _get_default_template(self, cr, uid, ids, context=None):
        try:
            return self.pool.get(
                'ir.model.data').get_object_reference(cr, uid, 'bt_followup',
                                                      'email_template_invoice_followup_default')[1]
        except ValueError:
            return False

    _name = 'followup.level'
    _description = 'Follow-up Criteria'
    _columns = {
        'name':
            fields.char(
                'Follow-up Action',
                size=64,
                required=True,
                translate=True),
        'sequence': fields.integer('Sequence', help="Gives the sequence order when \
        displaying a list of follow-up lines."),
        'delay': fields.integer('Delay', help="The number of days after the original due day after this level of follow-up is applied. The number can be negative if you want to send a polite alert beforehand.", required=True),
        'followup_config_id': fields.many2one('followup.config', 'Follow Up Configurations',
                                              required=True, ondelete="cascade"),
        'description': fields.text('Printed Message', translate=True),
        'send_email': fields.boolean('Send an Email', help="When processing,\
        it will send an email"),
        'send_letter': fields.boolean('Send a Letter',
                                      help="When processing, it will print a letter"),
        'manual_action': fields.boolean('Manual Action',
                                        help="When processing, it will set the manual action to be taken for that customer. "),
        'manual_action_note': fields.text('Action To Do', placeholder="e.g. Give a phone call,\
        check with others , ..."),
        'manual_action_responsible_id': fields.many2one('res.users', 'Assign a Responsible',
                                                        ondelete='set null'),
        'email_template_id': fields.many2one('email.template', 'Email Template',
                                             ondelete='set null'),

        'product_id': fields.many2one('product.product', _('Penalization')),

    }

    _order = 'delay'
    _sql_constraints = [(
                        'days_uniq',
                        'unique(followup_config_id, delay)',
                        _('Days of the follow-up levels must be different'))]
    _defaults = {
        'send_email': True,
        'send_letter': True,
        'manual_action': False,
        'description': """
        Dear {partner_name},

Exception made if there was a mistake of ours, it seems that the following invoice \
stays unpaid. Please, take appropriate measures in order to carry out this payment in the next 8 days.

Would your payment have been carried out after this mail was sent, please ignore this message. \
Do not hesitate to contact our accounting department.

Best Regards,
""",
        'email_template_id': _get_default_template,
    }

    def _check_description(self, cr, uid, ids, context=None):
        for line in self.browse(cr, uid, ids, context=context):
            if line.description:
                try:
                    line.description % {
                        'partner_name': '',
                        'date': '',
                        'user_signature': '',
                        'company_name': ''}
                except:
                    return False
        return True

    _constraints = [
        (_check_description, _('Your description is invalid, use the right legend or %% if you want to use the percent character.'),
         ['description']),
    ]

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
