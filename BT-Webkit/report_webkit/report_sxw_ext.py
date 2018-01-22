# -*- coding: utf-8 -*-
##############################################################################
#
#
##############################################################################

import subprocess
import os
import sys
import report
import tempfile
import time
import logging
import base64

from webkit_report import WebKitParser
import netsvc
import pooler
from report_helper import WebKitHelper
from report.report_sxw import *
import addons
import tools
from tools.translate import _
from osv import osv, fields
from string import Template
import cStringIO
from datetime import datetime

_logger = logging.getLogger(__name__)

class report_sxw_ext(WebKitParser):
    
    def _(self, src):
        return _(src)
    
    #save attachments
    def _save_attachments(self, cr, uid, ids, result, objs, report_xml, context=None):
        pool = pooler.get_pool(cr.dbname)
        if not context:
            context={}
        #attachments
        attach = report_xml.attachment
        if attach and result and len(result) >= 2:
            aname = eval(attach, {'object':objs[0], 'time':time})
            if aname:
                try:
                    aname = Template(aname).\
                                        substitute(set_date=datetime.now().strftime('%d%m%Y'))
                    name = aname+'.'+result[1]
                    res_id = objs[0].id if len(objs) == 1 else 0
                    # Remove the default_type entry from the context: this
                    # is for instance used on the account.account_invoices
                    # and is thus not intended for the ir.attachment type
                    # field.
                    ctx = dict(context)
                    ctx.pop('default_type', None)
                    #if attachment already exist just update with the new content
                    attachment_obj = self.pool.get('ir.attachment')
                    attachment_ids = attachment_obj.search(cr, uid, [('name', '=', aname),
                                                                     ('datas_fname', '=', name),
                                                                     ('res_model', '=', context.get('bt.res_model',self.table) ),
                                                                     ('res_id', '=', context.get('bt.res_id', res_id))])
                    if attachment_ids:
                        #just update with new context if attachment_use is not set
                        if report_xml.attachment_use and aname and context.get('attachment_use', True):
                            results_attachment = []
                            aids = pool.get('ir.attachment').search(cr, uid, [('datas_fname','=',aname+'.pdf'),('res_model','=',self.table),('res_id','=',objs[0])])
                            if aids:
                                brow_rec = pool.get('ir.attachment').browse(cr, uid, aids[0])
                                if brow_rec.datas:
                                    d = base64.decodestring(brow_rec.datas)
                                    results_attachment.append((d,'pdf'))
                            return results_attachment
                        else:
                            for attachment in attachment_obj.browse(cr, uid, attachment_ids, context):
                                attachment.write({'datas': base64.encodestring(result[0])})
                    else:
                        attachment_obj.create(cr, uid, {
                                                        'name': aname,
                                                        'datas': base64.encodestring(result[0]),
                                                        'datas_fname': name,
                                                        'res_model': context.get('bt.res_model',self.table),
                                                        'res_id': context.get('bt.res_id', res_id),
                                                        }, context=ctx
                                              )
                except Exception:
                    #TODO: should probably raise a proper osv_except instead, shouldn't we? see LP bug #325632
                    # by ropa1 (15.04.2014): At least this will pass the exception.
                    raise
    
    #rewrite create_source_pdf
    def create_source_pdf(self, cr, uid, ids, data, report_xml, context=None):
        pol = pooler.get_pool(cr.dbname)
        if not context:
            context={}
        #Fernuni - 1 for UID Administrator - Maybe a Security Risk
        objs = self.getObjects(cr, 1, ids, context)  
        printer =  pol.get('res.users').browse(cr, uid, uid, context).printer_id
        if report_xml.direct_print and printer:
            selected=pol.get('printer').browse(cr,uid,printer.id,context)
            direct=selected.primary_tray
            if report_xml.alternative_print:
                child=selected.alternative_tray
            else:
                child=False  
        else:
            direct=False
            child=False
            
        results=[] 
        results_child=[]
        
        if report_xml.one_document:
            # To print every record in one document
            temp_result = self.create_single_pdf(cr, 1, ids, data,report_xml,context,direct)
            if temp_result:
                results.append(temp_result)
            #save attachments (if results_attachment is not [], then set this as return)
            results_attachment = self._save_attachments(cr, uid, ids, temp_result, objs, report_xml, context)
            if results_attachment:
                results = results_attachment
            else:
                for obj in objs:
                    #update context with current active_id
                    context.update({'active_id':obj.id})
                    #Need to set the latest Statement to True -> Then it prints directly to the printer
                    #Fernuni - 1 for UID Administrator - Maybe a Security Risk
                    #Create the Child PDF's if there are some of them -> ensure that they are printed directly
                    if report_xml.child_report:
                        #Fernuni - 1 for UID Administrator - Maybe a Security Risk
                        temp_result = self.create_single_pdf(cr, 1, [obj.id], data,report_xml.child_report,context,direct,child)
                        if temp_result:
                            results.append(temp_result)
        else:
            for obj in objs:
                #update context with current active_id
                context.update({'active_id':obj.id})
                #Need to set the latest Statement to True -> Then it prints directly to the printer
                #Fernuni - 1 for UID Administrator - Maybe a Security Risk
                temp_result = self.create_single_pdf(cr, 1, [obj.id], data,report_xml,context,direct)
                if temp_result:
                    results.append(temp_result)
                #save attachments (if results_attachment is not [], then set this as return)
                results_attachment = self._save_attachments(cr, uid, ids, temp_result, [obj], report_xml, context)
                if results_attachment:
                    results = results_attachment
                else:
                    #Create the Child PDF's if there are some of them -> ensure that they are printed directly
                    if report_xml.child_report:
                        #Fernuni - 1 for UID Administrator - Maybe a Security Risk
                        temp_result = self.create_single_pdf(cr, 1, [obj.id], data,report_xml.child_report,context,direct,child)
                        if temp_result:
                            results.append(temp_result)       
        #Return combined PDF
        if results:
            from report.pyPdf import PdfFileWriter, PdfFileReader
            output = PdfFileWriter()
            for r in results:
                reader = PdfFileReader(cStringIO.StringIO(r[0]))
                for page in range(reader.getNumPages()):
                    output.addPage(reader.getPage(page))
            s = cStringIO.StringIO()
            output.write(s)
            return s.getvalue(), results[0][1]
        else:
            return False


    
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
