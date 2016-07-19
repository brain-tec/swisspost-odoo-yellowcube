# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2011 OpenERP S.A (<http://www.openerp.com>).
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

import logging
from openerp.osv import fields, osv
from openerp.tools.translate import _
from openerp.tools import email_split
from xml.dom.minidom import parse
from openerp import SUPERUSER_ID
import base64
_logger = logging.getLogger(__name__)
HEADER = """<?xml version="1.0" encoding="utf-8"?><documents> \n"""
FOOTER = """</documents>"""


class wizard_knowledge_export(osv.TransientModel):

    _name = 'pc.wz.knowledge.export'
    _description = 'Wizard knowledge export'

    _columns = {
        'state': fields.selection([('draft', 'Draft'), ('done', 'Done')], 'State', required=True),
        'attachment_ids': fields.many2many('ir.attachment', rel='wiz_know_attach', string="Attachments"),
        'report_file': fields.binary('Generated Report', readonly=True),
        'report_name': fields.char('Report name'),
        'description': fields.text('Description'),
    }
    _defaults = {'state': 'draft'}

    def action_create_binary(self, cr, uid, ids, context):
        for wiz in self.browse(cr, uid, ids, context):
            xml_fname = HEADER
            for attachment in wiz.attachment_ids:
                xml_fname += attachment.export_to_xml()
            wiz.write({'report_file': base64.b64encode(xml_fname + FOOTER),
                       'report_name': 'export%s.xml' % fields.datetime.now(),
                       'state': 'done'})

        return True


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
