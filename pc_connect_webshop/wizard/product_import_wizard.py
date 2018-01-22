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
from osv import osv, fields
from openerp.tools.translate import _
from openerp.addons.pc_connect_master.utilities.others import format_exception
import base64
import csv
import StringIO
from product_import_alternative import product_import_alternative
from product_import_related import product_import_related
from product_import_manuals import product_import_manuals
from product_import_media import product_import_media
import logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


class product_import_wizard(osv.TransientModel):
    _name = 'product.import_wizard'

    def do_import(self, cr, uid, ids, context=None):
        if context is None:
            context = {}

        wiz = self.browse(cr, uid, ids, context=context)[0]
        text = base64.decodestring(wiz.file)
        text = StringIO.StringIO(text)
        csv_file = csv.DictReader(text,
                                  dialect='excel')

        func = lambda pool, cr, uid, csv_file, context: (False, 'Undefined importer')
        if wiz.type == 'alternative':
            func = product_import_alternative
        elif wiz.type == 'link':
            func = product_import_related
        elif wiz.type == 'media':
            func = product_import_media
        elif wiz.type == 'manual':
            func = product_import_manuals
        elif wiz.type == 'related':
            func = product_import_related

        success, message = False, "Error on import execution.\n{0}"
        cr.execute("SAVEPOINT product_import_wizard;")
        try:
            success, message = func(self.pool, cr, uid, csv_file, context)
        except Exception as e:
            logger.info(e)
            message = message.format(format_exception(e))
        if success:
            cr.execute("RELEASE SAVEPOINT product_import_wizard;")
        else:
            cr.execute("ROLLBACK TO product_import_wizard;")
        context['error'] = not success
        context['info'] = message or False
        if message:
            self.write(cr, uid, ids, {'message': message}, context=context)

        return {
            'name': 'Result',
            'context': context,
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'product.import_wizard',
            'res_id': ids[0],
            'type': 'ir.actions.act_window',
            'target': 'new',
        }

    _columns = {
        'file': fields.binary("File to import", required=True),
        'type': fields.selection([('alternative', 'Alternative'),
                                  ('link', 'Related (link)'),
                                  ('media', 'Media pictures'),
                                  ('manual', 'Manual'),
                                  ],
                                 string="File type",
                                 required=True),
        'message': fields.text("Message", readonly=True)
    }
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: