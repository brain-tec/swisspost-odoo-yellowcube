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
from osv import osv, fields, orm
#import fields
#import openerp
from openerp.tools.translate import _
from openerp.tools.config import config
from bt_helper.log_rotate import get_log
#from jinja2.testsuite import here
#from numpy.ma.core import ids
from pytz import all_timezones_set
from docutils.nodes import row
logger = get_log("DEBUG")
import functools
from base_import.models import ir_import
import csv
import itertools
import openerp.tools as tools
from openerp import SUPERUSER_ID
import base64
import gzip

#from ORM.py; needed for export_data
def fix_import_export_id_paths(fieldname):
    """
    Fixes the id fields in import and exports, and splits field paths
    on '/'.

    :param str fieldname: name of the field to import/export
    :return: split field name
    :rtype: list of str
    """
    fixed_db_id = re.sub(r'([^/])\.id', r'\1/.id', fieldname)
    fixed_external_id = re.sub(r'([^/]):id', r'\1/id', fixed_db_id)
    return fixed_external_id.split('/')

class export_all(osv.osv):
    
    _name = 'export.all'
    
    """
    When this class is called a back daemon must start exporting all the data from the given model & fields.
    
    A message must appear on screen to advise that this is being done and that an email will be sent to the user with
    the desired data.
    
    At the same time an email must be sent to the actual user when the job is finished, with the data
    """
    
    def create_send_email(self, cr, uid, filename, context):
        
        ir_config_parameter_pool = self.pool.get('ir.config_parameter')
        param = 'export_all_path'
        directoryPath = ir_config_parameter_pool.get_param(cr, uid, param, False)
        
        context={}
        attachment_data = {}
        
        mail_message_obj = self.pool.get('mail.mail')
        ir_attachment_obj = self.pool.get('ir.attachment')
        
        #email address of the user
        usrs = self.pool.get('res.users')
        email_to = usrs.browse(cr, uid, uid, context).partner_id.email
        
        subject = 'Export all fields file'
        
        file = directoryPath+ filename
        
        logger.debug(file)
        csvfile = open(file, 'rb')

        attachment_data = {
                        'name': 'Inventory Failure data',
                        'datas_fname': filename,
                        'datas': base64.b64encode(csvfile.read()),
                        #'datas': f.read(),
                        #'datas': base64.b64encode(data_to_send),
                        'res_model': None,
                        'res_id': None,
                        }
        attachment_ids = [ir_attachment_obj.create(cr, uid, attachment_data, context=context)]
        
        csvfile.close()
        
        msg_id = mail_message_obj.create(cr, 
                                        uid, 
                                        {'subject': subject,
                                        'email_from': 'export_fields@leister.it',
                                        'email_to': email_to,
                                        'subject': subject,
                                        'body_html':"Attached you will find the file with the full export of desired fields",
                                        'model':'',
                                        'auto_delete': True,
                                        #'subtype':'html',
                                        },
                                        context=context)
        mail_message_obj.write(cr, uid, msg_id, {'attachment_ids': [(6, 0, attachment_ids)]}, context=context)
         
        mail_message_obj.send(cr, uid, [msg_id], context=context)
        logger.debug('send export all email')
        return True
    
    def gen_filename(self, cr, uid, model, context):
        filename=''
        id=self.pool.get('res.users').browse(cr, uid, uid, context).id
        id = str(id)
        filename='ExpAll_uid'+id+'_'+model+'.csv'
        return filename
    
    def ___export_row(self, cr, uid, row, fields, work_model, context=None):
        if context is None:
            context = {}
            
        print row
        print fields
        print work_model
        print '----'

        def check_type(field_type):
            if field_type == 'float':
                return 0.0
            elif field_type == 'integer':
                return 0
            elif field_type == 'boolean':
                return 'False'
            return ''

        def selection_field(in_field):
            col_obj = self.pool.get(in_field.keys()[0])
            if f[i] in col_obj._columns.keys():
                return  col_obj._columns[f[i]]
            elif f[i] in col_obj._inherits.keys():
                selection_field(col_obj._inherits)
            else:
                return False

        def _get_xml_id(self, cr, uid, r, work_model):
            model_data = self.pool.get('ir.model.data')
            data_ids = model_data.search(cr, uid, [('model', '=', r._table_name), ('res_id', '=', r['id'])])
            if len(data_ids):
                d = model_data.read(cr, uid, data_ids, ['name', 'module'])[0]
                #module = __export__
                if d['module']:
                    r = '%s.%s' % (d['module'], d['name'])
                else:
                    r = d['name']
            else:
                postfix = 0
                while True:
                    n = work_model._table+'_'+str(r['id']) + (postfix and ('_'+str(postfix)) or '' )
                    if not model_data.search(cr, uid, [('name', '=', n)]):
                        break
                    postfix += 1
                model_data.create(cr, SUPERUSER_ID, {
                    'name': n,
                    'model': work_model._name,
                    'res_id': r['id'],
                    'module': '__export__',
                })
                r = '__export__.'+n
            return r

        lines = []
        data = map(lambda x: '', range(len(fields)))
        done = []
        for fpos in range(len(fields)):
            f = fields[fpos]
            if f:
                #r = row
                i = 0
                while i < len(f):
                    r = row
                    cols = False
                    if f[i] == '.id':
                        r = r['id']
                    elif f[i] == 'id':
                        r = _get_xml_id(self, cr, uid, r, work_model)
                    else:
                        
                        #different to ID
                        
                        r = r[f[i]]
                        # To display external name of selection field when its exported
                        if f[i] in work_model._columns.keys():
                            cols = work_model._columns[f[i]]
                        elif f[i] in work_model._inherit_fields.keys():
                            cols = selection_field(work_model._inherits)
                        if cols and cols._type == 'selection':
                            sel_list = cols.selection
                            if r and type(sel_list) == type([]):
                                r = [x[1] for x in sel_list if r==x[0]]
                                r = r and r[0] or False
                    if not r:
                        if f[i] in work_model._columns:
                            r = check_type(work_model._columns[f[i]]._type)
                        elif f[i] in work_model._inherit_fields:
                            r = check_type(work_model._inherit_fields[f[i]][2]._type)
                        data[fpos] = r or False
                        break
                    if isinstance(r, (orm.browse_record_list, list)):
                        first = True
                        fields2 = map(lambda x: (x[:i+1]==f[:i+1] and x[i+1:]) \
                                or [], fields)
                        if fields2 in done:
                            if [x for x in fields2 if x]:
                                break
                        done.append(fields2)
                        if cols and cols._type=='many2many' and len(fields[fpos])>(i+1) and (fields[fpos][i+1]=='id'):
                            data[fpos] = ','.join([_get_xml_id(self, cr, uid, x) for x in r])
                            break

                        for row2 in r:
                            
                            #new call but from different model now                        
                            work_model = row2._model
                            
                            lines2 = self.___export_row(cr, uid, row2, fields2, work_model, context)
                            
                                    
                            if first:
                                for fpos2 in range(len(fields)):
                                    if lines2 and lines2[0][fpos2]:
                                        data[fpos2] = lines2[0][fpos2]
                                if not data[fpos]:
                                    dt = ''
                                    for rr in r:
                                        name_relation = self.pool.get(rr._table_name)._rec_name
                                        if isinstance(rr[name_relation], orm.browse_record):
                                            rr = rr[name_relation]
                                        rr_name = self.pool.get(rr._table_name).name_get(cr, uid, [rr.id], context=context)
                                        rr_name = rr_name and rr_name[0] and rr_name[0][1] or ''
                                        dt += tools.ustr(rr_name or '') + ','
                                    data[fpos] = dt[:-1]
                                    break
                                lines += lines2[1:]
                                first = False
                            else:
                                lines += lines2
                        break
                    i += 1
                if i == len(f):
                    if isinstance(r, orm.browse_record):
                        r = self.pool.get(r._table_name).name_get(cr, uid, [r.id], context=context)
                        r = r and r[0] and r[0][1] or ''
                    data[fpos] = tools.ustr(r or '')
        return [data] + lines
      
    
    def get_headers(self, import_compat, field_names):
        if import_compat:
            columns_headers = field_names
        else:
            columns_headers = [val['label'].strip() for val in fields]
        return columns_headers
    

    


    def export_and_write(self, cr, uid, ids, field_names, columns_headers, filename, model, context):
        #open file to write in
        if context is None:
            context = {}
            
        ir_config_parameter_pool = self.pool.get('ir.config_parameter')
        param = 'export_all_path'
        route = ir_config_parameter_pool.get_param(cr, uid, param, False)
        
        #route = '/home/gaca1/openerpsources/leister/export_all/'
        filename = route+filename
        
        fp2 = open(filename,'w')
        writer = csv.writer(fp2, quoting=csv.QUOTE_ALL)
        
        #write the columns headers into the file
        writer.writerow([name.encode('utf-8') for name in columns_headers])
        
        #get the data to import and write it
        #first get all the IDS (we are in Export all context)
        md=self.pool.get(model)
        all_ids = md.search(cr, uid,[])
        
        datas = []
        datas = self.pool.get(model).export_data(cr, uid, all_ids, field_names, context={})
        #print data['datas']
        
        data_to_write = datas['datas']
        for line in data_to_write:
            #===================================================================
            # line = line.replace('\n',' ').replace('\t',' ')
            # try:
            #     line = line.encode('utf-8')
            # except UnicodeError:
            #     pass
            #     d = d.encode('utf-8')
            #===================================================================
            writer.writerow(line)
            #print line
        

        #pass these
        
        #=======================================================================
        # cols = md._columns.copy()
        # for f in md._inherit_fields:
        #     cols.update({f: md._inherit_fields[f][2]})
        # fields_to_export = map(orm.fix_import_export_id_paths, field_names)
        # datas = []
        #=======================================================================
        
        #=======================================================================
        # for row in self.browse(cr, uid, ids, context):
        #     datas += self.__export_row(cr, uid, row, fields_to_export, context)
        # return {'datas': datas}
        #=======================================================================
        
        #=======================================================================
        # work_model = md
        # for index in all_ids:
        #     data=[]
        #     row = md.browse(cr, uid, index, context)
        #     #get the data to write
        #     
        #     #SELF = export.all
        #     
        #     data = self.___export_row(cr, uid, row, fields_to_export, work_model, context)
        #     #data = md.__export_row(cr, uid, row, fields_to_export, context)
        #     
        #     
        #     data=data[0]
        #     #write the data in the file
        #     row_write = []
        #     for d in data:
        #         if isinstance(d, basestring):
        #             d = d.replace('\n',' ').replace('\t',' ')
        #             try:
        #                 d = d.encode('utf-8')
        #             except UnicodeError:
        #                 pass
        #         if d is False: d = None
        #         row_write.append(d)
        #     writer.writerow(row_write)
        #=======================================================================
            

        #end file: close
        fp2.close()
        logger.debug("closed file")
        return True
    
    def compress_export_file(self, cr, uid, ids, filename, context):
        
        
        
        ir_config_parameter_pool = self.pool.get('ir.config_parameter')
        param = 'export_all_path'
        route = ir_config_parameter_pool.get_param(cr, uid, param, False)
        filename = route+filename
        new_filename = filename +'.gz'
        
        logger.debug('compressing the file')
        f_to_compress = open(filename,'rb')
        f_compressed = gzip.open(new_filename,'wb')
        f_compressed.writelines(f_to_compress)
        f_compressed.close()
        f_to_compress.close()
        
        return new_filename
    
    def delete_cron(self, cr, uid, context):
        ir_cr = self.pool.get('ir.cron')
        index = ir_cr.search(cr, uid, [('name','=','Create All Export File')] )


    def exp_all_cron(self, cr, uid, ids, model, field_names, import_compat, context=None):
        
        #logger.debug("Function inside of Cron Job")
        #model = model.encode('ascii','ignore')
        context.update({'model':model})
        md=self.pool.get(model)
        #ids = model.search(cr, uid, [], context=context)
        
        
        #get filename
        filename=self.gen_filename(cr, uid, model, context)
        #get headers
        columns_headers = self.get_headers(import_compat, field_names)
        #import and write data to file
        logger.debug('start reading and writting')
        
        
        self.export_and_write(cr, uid, ids, field_names, columns_headers, filename, model, context)
        logger.debug('finish reading and writting')
        
        self.compress_export_file(cr, uid, ids, filename, context)
        logger.debug('done compressing the file')
        
        #put the name of the file to the compressed file
        filename = filename + '.gz'
        
        #send email with data
        logger.debug("Send Email")
        self.create_send_email(cr, uid, filename, context)
        #inactivate the cron_job for further use
        #self.inactivate_cron_job(self, cr, uid, ids, context)
        logger.debug("Finish export all method")
        return True
    
    def create_cron_job(self, cr, uid, ids, model, field_names, import_compat, context):
        self.pool.get('ir.cron').create(cr, uid, {
            'name': 'Create All Export File',
            'user_id': uid,
            'model': 'export.all',
            'function': 'exp_all_cron',
            'args': repr([ids, model, field_names, import_compat, context]),
            'active': True
        })
    
    def unlink_cron_job(self, cr, uid, ids, index_cron, context):
        id = self.pool.get('ir.cron').unlink(cr, uid, index_cron, context)
        return id
    
    def export_all(self, cr, uid, ids, model, field_names, import_compat, context):
        #update the context
        context.update({'export_all':True})
        #
        #
        #look if there is a cron job already
        #ir_cr = self.pool.get('ir.cron')
        #index = self.pool.get('ir.cron').search(cr, uid, [('name','=','Create All Export File')])
        query = """  SELECT id FROM ir_cron WHERE "name" LIKE 'Create All Export File'; """
        cr.execute(query)
        index2 = [x[0] for x in cr.fetchall()]
        
        if not index2:
            self.create_cron_job(cr, uid, ids, model, field_names, import_compat, context)
        else:
            self.unlink_cron_job(cr, uid, ids, index2, context)
            self.create_cron_job(cr, uid, ids, model, field_names, import_compat, context)
            #print 'opcion 2'
        
        logger.debug("Cron job created")
        return True
            
    #use FROM_DATA (\in /web module) to write the data
    #view the inputs in it
    
    


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
