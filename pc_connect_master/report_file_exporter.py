# b-*- encoding: utf-8 -*-
##############################################################################
#
#    Copyright (c) 2014 brain-tec AG (http://www.brain-tec.ch)
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
from openerp.addons.web.controllers.main import content_disposition
import base64
import csv
import StringIO
import xlsxwriter
import logging
logger = logging.getLogger(__name__)


def export_decorator(mode):
    def _export_decorator(f):
        def _decorated(*args, **kargs):
            logger.info("Exporting into {0}".format(mode))
            [data, n] = f(*args, **kargs)
            logger.info("Exported {0} items".format(n))
            return [data, n]
        return _decorated
    return _export_decorator


class report_file_exporter(osv.osv_memory):
    _name = "report.file.exporter"

    def export_report(self, cr, uid, ids, context=None):

        if context is None:
            context = {}

        if not isinstance(ids, list):
            ids = [ids]

        wizard = self.browse(cr, uid, ids, context=context)[0]

        var_model = context.get('active_model', False)
        var_format = wizard.file_ext or context.get('var_format', 'csv')
        var_fields = context.get('var_fields', ('id'))
        file_name = _("report_{var_model}.{var_format}").format(var_model=var_model.replace(".", "_"), var_format=var_format)
        logger.debug("Active model {0} ".format(var_model))
        logger.debug("Format {0} ".format(var_format))
        logger.debug("Field {0} ".format(str(var_fields)))
        if not var_model:
            # Raise exception
            return
        if var_format == 'csv':
            [result_csv, nitems] = self.export_model_to_csv(cr, uid, var_model, var_fields, context)
        elif var_format == 'xlsx':
            [result_csv, nitems] = self.export_model_to_xlsx(cr, uid, var_model, var_fields, context)
        else:
            return False
        new_vals = {
            'ready': True,
            'file': base64.b64encode(result_csv),
            'file_name': file_name,
            'message': _("{0} exported records").format(nitems)
        }
        self.write(cr, uid, ids, new_vals)
        return {
            'name': 'Result',
            'context': context,
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'report.file.exporter',
            'res_id': ids[0],
            'type': 'ir.actions.act_window',
            'target': 'new',
        }

    def get_datas(self, cr, uid, model, fields, context):
        context['import_comp'] = True
        active_ids = context.get('active_ids', [])
        logger.debug("Export {1} ids={0}".format(active_ids, model))
        if 'sql' in context:
            cr.execute(context['sql'].format(ids=','.join([str(x) for x in active_ids])))
            datas = []
            for line in cr.fetchall():
                line = list(line)
                for mod_pos in context['models']:
                    if line[mod_pos]:
                        line[mod_pos] = self.pool.get(context['models'][mod_pos]).name_get(cr, uid, [line[mod_pos]], context)[0][1]
                    else:
                        line[mod_pos] = ''
                datas.append(tuple(line))
            result_data = {'datas': datas}
            print result_data
        else:
            result_data = self.pool.get(model).export_data(cr, uid, active_ids, fields, context=context)
        if 'var_fields_label' in context:
            labels = context['var_fields_label']
            new_fields = []
            pos = 0
            for f in fields:
                if labels[pos]:
                    new_fields.append(labels[pos])
                else:
                    new_fields.append(f)
                pos += 1
            fields = new_fields

        return fields, result_data

    @export_decorator('xlsx')
    def export_model_to_xlsx(self, cr, uid, model, fields, context=None):
        if context is None:
            context = []
        fields, result_data = self.get_datas(cr, uid, model, fields, context)

        xlsx_stream = StringIO.StringIO()
        xlsx_writer = xlsxwriter.Workbook(xlsx_stream)
        xlsx_sheet = xlsx_writer.add_worksheet(model)
        col_number = 0
        for field in fields:
            xlsx_sheet.write_string(0, col_number, str(field))
            col_number += 1
        row_number = 0
        for row in result_data['datas']:
            # row = [str(x).replace('\n', '|') for x in row]
            col_number = 0
            row_number += 1
            for datum in row:
                xlsx_sheet.write_string(row_number, col_number, str(datum))
                col_number += 1
        xlsx_writer.close()
        result_csv = xlsx_stream.getvalue()
        xlsx_stream.close()
        return [result_csv, len(result_data['datas'])]

    @export_decorator('csv')
    def export_model_to_csv(self, cr, uid, model, fields, context=None):
        if context is None:
            context = []
        fields, result_data = self.get_datas(cr, uid, model, fields, context)

        csv_stream = StringIO.StringIO()
        csv_writer = csv.writer(csv_stream)
        csv_writer.writerow(fields)
        for row in result_data['datas']:
            row = [str(x).replace('\n', '|') for x in row]
            csv_writer.writerow(row)
        result_csv = csv_stream.getvalue()
        csv_stream.close()
        return [result_csv, len(result_data['datas'])]

    _columns = {
        'file': fields.binary("Download file"),
        'file_name': fields.text("File name"),
        'file_ext': fields.selection([('csv', 'csv'), ('xlsx', 'Excel (xlsx)')], "Extension"),
        'ready': fields.boolean("Ready for download"),
        'message': fields.text("Information")
    }

    _defaults = {
        'ready': "False",
        'file_name': 'report.csv',
        'message': 'Click to create report.',
        'file_ext': 'csv'
    }

report_file_exporter()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
