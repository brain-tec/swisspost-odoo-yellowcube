# -*- coding: utf-8 -*-
##############################################################################
#
# Copyright (c) 2010 Camptocamp SA (http://www.camptocamp.com)
# All Right Reserved
#
# Author : Nicolas Bessi (Camptocamp)
# Contributor(s) : Florent Xicluna (Wingo SA)
#
# WARNING: This program as such is intended to be used by professional
# programmers who take the whole responsability of assessing all potential
# consequences resulting from its eventual inadequacies and bugs
# End users who are looking for a ready-to-use solution with commercial
# garantees and support are strongly adviced to contract a Free Software
# Service Company
#
# This program is Free Software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA  02111-1307, USA.
#
##############################################################################

import subprocess
import os
import sys
import report
import tempfile
import time
import logging

from mako.template import Template
from mako.lookup import TemplateLookup
from mako import exceptions


import netsvc
import pooler
from report_helper import WebKitHelper
from report.report_sxw import *
import addons
import tools
from tools.translate import _
from osv.osv import except_osv
from functools import partial

logger = logging.getLogger(__name__)

def mako_template(text):
    """Build a Mako template.

    This template uses UTF-8 encoding
    """
    tmp_lookup  = TemplateLookup(directories=['openerp']) #we need it in order to allow inclusion and inheritance
    return Template(text, input_encoding='utf-8', output_encoding='utf-8', lookup=tmp_lookup)

class WebKitParser(report_sxw):
    """Custom class that use webkit to render HTML reports
       Code partially taken from report openoffice. Thanks guys :)
    """
    def __init__(self, name, table, rml=False, parser=False,
        header=True, store=False):
        self.localcontext = {}
        report_sxw.__init__(self, name, table, rml, parser,
            header, store)

    def get_lib(self, cursor, uid):
        """Return the lib wkhtml path"""
        proxy = self.pool.get('ir.config_parameter')
        # HACK: 06.10.2015 15:50:34: jool1: set use_wkhtmltopdf from webkit_path 
        if self.localcontext.get('use_default_webkit_path', True):
            webkit_path = proxy.get_param(cursor, uid, 'webkit_path')
        else:
            webkit_path = proxy.get_param(cursor, uid, 'webkit_path_financial_reports')

        if not webkit_path:
            try:
                defpath = os.environ.get('PATH', os.defpath).split(os.pathsep)
                if hasattr(sys, 'frozen'):
                    defpath.append(os.getcwd())
                    if tools.config['root_path']:
                        defpath.append(os.path.dirname(tools.config['root_path']))
                webkit_path = tools.which('wkhtmltopdf', path=os.pathsep.join(defpath))
            except IOError:
                webkit_path = None

        if webkit_path:
            return webkit_path

        raise except_osv(
                         _('Wkhtmltopdf library path is not set'),
                         _('Please install executable on your system' \
                         ' (sudo apt-get install wkhtmltopdf) or download it from here:' \
                         ' http://code.google.com/p/wkhtmltopdf/downloads/list and set the' \
                         ' path in the ir.config_parameter with the webkit_path key.' \
                         'Minimal version is 0.9.9')
                        )
    
    def generate_pdf(self, comm_path, report_xml, header, footer, html_list, webkit_header=False, printer=False, child=False, context={}):
        """Call webkit in order to generate pdf"""
    
        if not webkit_header:
            webkit_header = report_xml.webkit_header

        #_ , out_filename = tempfile.mkstemp(suffix=".pdf", prefix="webkit.tmp.")
        #out_filename = tempfile.mktemp(suffix=".pdf", prefix="webkit.tmp.")
        out_filename = tempfile.mktemp(suffix=".pdf", prefix="webkit.tmp.")

        files = []
        file_to_del = []

        # This structure will keep the file paths for the header, the footer,
        # and the different bodies (since apparently can be several ones)
        # just in case we want to retrieve them --- thing that only will happen
        # if the context contains the flag 'get_mako_html_files' as active.
        mako_html_files = {}

        if comm_path:
            command = [comm_path.strip()]
        else:
            command = ['wkhtmltopdf']

        command.append('--quiet')
        # default to UTF-8 encoding.  Use <meta charset="latin-1"> to override.
        command.extend(['--encoding', 'utf-8'])

        if header :
            head_file = file(tempfile.mktemp(suffix='.head.html', prefix=''), 'w')
            head_file.write(header)
            head_file.close()
            file_to_del.append(head_file.name)
            command.extend(['--header-html', head_file.name])
            mako_html_files.update({'header': head_file.name})

        if footer :
            foot_file = file(tempfile.mktemp(suffix='.foot.html', prefix=''), 'w')
            foot_file.write(footer)
            foot_file.close()
            file_to_del.append(foot_file.name)
            command.extend(['--footer-html', foot_file.name])
            mako_html_files.update({'footer': foot_file.name})

        if webkit_header.margin_top :
            command.extend(['--margin-top', str(webkit_header.margin_top).replace(',', '.')])
        if webkit_header.margin_bottom :
            command.extend(['--margin-bottom', str(webkit_header.margin_bottom).replace(',', '.')])
        if webkit_header.margin_left :
            command.extend(['--margin-left', str(webkit_header.margin_left).replace(',', '.')])
        if webkit_header.margin_right :
            command.extend(['--margin-right', str(webkit_header.margin_right).replace(',', '.')])
        if webkit_header.orientation :
            command.extend(['--orientation', str(webkit_header.orientation).replace(',', '.')])
        if webkit_header.format != "Customize":
            command.extend(['--page-size', str(webkit_header.format).replace(',', '.')])
        else:
            # Take page_width and page_hegith information
            #
            command.extend(['--page-width', str(webkit_header.page_width).replace(',', '.')])
            if 'page-height' in context:
                command.extend(['--page-height', str(context['page-height']).replace(',', '.')])
            else:
                command.extend(['--page-height', str(webkit_header.page_height).replace(',', '.')])

        for html in html_list :
            html_file = file(tempfile.mktemp(suffix='.body.html', prefix=''), 'w')
            html_file.write(html)
            html_file.close()
            file_to_del.append(html_file.name)
            command.append(html_file.name)
            mako_html_files.setdefault('bodies', []).append(html_file.name)

        command.append(out_filename)
        try:
            
            status = subprocess.call(command, stderr=subprocess.PIPE) # ignore stderr
            if status :
                raise except_osv(
                                _('Webkit raise an error' ),
                                status
                            )
        except Exception as e:
            for f_to_del in file_to_del :
                os.unlink(f_to_del)
            raise e

                
        #This setups the direct printing options from brain-tec
        if printer:
            if child:
                s=out_filename
                print 'Filename: ',s 
                a=child+" '"+s+"'"
                os.system(a)
            else:
                s=out_filename
                print 'Filename: ',s 
                a=printer+" '"+s+"'"
                os.system(a)
            
        
        pdf = file(out_filename, 'rb').read()

        # If we want to get the MAKO HTML files, we store their paths;
        # otherwise we remove them.
        if context.get('get_mako_html_files'):
            context.update({'mako_html_files': mako_html_files})
        else:
            pass
            # for f_to_del in file_to_del :
            #     if os.path.exists(f_to_del):
            #         os.unlink(f_to_del)

        os.unlink(out_filename)
        return pdf

    # HACK: 06.10.2015 15:50:34: jool1: copied method generate_pdf from account_financial_report_webkit
    def generate_pdf_account_financial_report_webkit(self, comm_path, report_xml, header, footer, html_list,
                     webkit_header=False, parser_instance=False):
        """Call webkit in order to generate pdf"""
        if not webkit_header:
            webkit_header = report_xml.webkit_header
        fd, out_filename = tempfile.mkstemp(suffix=".pdf",
                                            prefix="webkit.tmp.")
        file_to_del = [out_filename]
        if comm_path:
            command = [comm_path]
        else:
            command = ['wkhtmltopdf']

        command.append('--quiet')
        # default to UTF-8 encoding.  Use <meta charset="latin-1"> to override.
        command.extend(['--encoding', 'utf-8'])

        if webkit_header.margin_top:
            command.extend(
                ['--margin-top',
                 str(webkit_header.margin_top).replace(',', '.')])
        if webkit_header.margin_bottom:
            command.extend(
                ['--margin-bottom',
                 str(webkit_header.margin_bottom).replace(',', '.')])
        if webkit_header.margin_left:
            command.extend(
                ['--margin-left',
                 str(webkit_header.margin_left).replace(',', '.')])
        if webkit_header.margin_right:
            command.extend(
                ['--margin-right',
                 str(webkit_header.margin_right).replace(',', '.')])
        if webkit_header.orientation:
            command.extend(
                ['--orientation',
                 str(webkit_header.orientation).replace(',', '.')])
        if webkit_header.format:
            command.extend(
                ['--page-size',
                 str(webkit_header.format).replace(',', '.')])

        if parser_instance.localcontext.get('additional_args', False):
            for arg in parser_instance.localcontext['additional_args']:
                command.extend(arg)

        count = 0
        for html in html_list:
            with tempfile.NamedTemporaryFile(suffix="%d.body.html" % count,
                                             delete=False) as html_file:
                count += 1
                html_file.write(self._sanitize_html(html))
            file_to_del.append(html_file.name)
            command.append(html_file.name)
        command.append(out_filename)
        stderr_fd, stderr_path = tempfile.mkstemp(text=True)
        file_to_del.append(stderr_path)
        try:
            status = subprocess.call(command, stderr=stderr_fd)
            os.close(stderr_fd)  # ensure flush before reading
            stderr_fd = None  # avoid closing again in finally block
            fobj = open(stderr_path, 'r')
            error_message = fobj.read()
            fobj.close()
            if not error_message:
                error_message = _('No diagnosis message was provided')
            else:
                error_message = _(
                    'The following diagnosis message was provided:\n') + \
                    error_message
            if status:
                raise except_osv(_('Webkit error'),
                                 _("The command 'wkhtmltopdf' failed with \
                                 error code = %s. Message: %s") %
                                 (status, error_message))
            with open(out_filename, 'rb') as pdf_file:
                pdf = pdf_file.read()
            os.close(fd)
        finally:
            if stderr_fd is not None:
                os.close(stderr_fd)
            for f_to_del in file_to_del:
                try:
                    os.unlink(f_to_del)
                except (OSError, IOError), exc:
                    _logger.error('cannot remove file %s: %s', f_to_del, exc)
        return pdf

    def translate_call(self, parser_instance, src):
        """Translate String."""
        ir_translation = self.pool.get('ir.translation')
        # HACK: 14.05.2014 09:08:47: olivier: added self.tmpl instead of None to get source
        name = None
        if self.tmpl:
            name = self.tmpl
            if not name.startswith('addons/'):
                name = 'addons/' + name
        res = ir_translation._get_source(parser_instance.cr, parser_instance.uid,
                                         name, 'report', parser_instance.localcontext.get('lang', 'en_US'), src)
        if res == src:
            # no translation defined, fallback on None (backward compatibility)
            res = ir_translation._get_source(parser_instance.cr, parser_instance.uid,
                                             None, 'report', parser_instance.localcontext.get('lang', 'en_US'), src)
        if not res :
            return src
        return res

    # override needed to keep the attachments storing procedure
    def create_single_pdf(self, cursor, uid, ids, data,report_xml,context=None,printer=False,child=False):
        """generate the PDF"""


        if context is None:
            context={}
        htmls = []
        if report_xml.report_type != 'webkit':
            return super(WebKitParser,self).create_single_pdf(cursor, uid, ids, data, report_xml, context=context)
        
        parser_instance = self.parser(cursor,
                                      uid,
                                      self.name2,
                                      context=context)

        self.pool = pooler.get_pool(cursor.dbname)
        objs = self.getObjects(cursor, uid, ids, context)
        parser_instance.set_context(objs, data, ids, report_xml.report_type)

        template =  False

        if report_xml.report_file :
            # HACK: 28.06.2013 14:54:18: olivier: mako - change for openerp7 (works also for version 6)
#             path = addons.get_module_resource(report_xml.report_file)
            from os.path import join as opj
            mod_path = addons.get_module_path(report_xml.report_file)
            if not mod_path: return False
            resource_path = opj(mod_path)
            if os.path.exists(resource_path):
                path = resource_path
                
            if os.path.exists(path) :
                template = file(path).read()
        if not template and report_xml.report_webkit_data :
            template =  report_xml.report_webkit_data
        if not template :
            raise except_osv(_('Error!'), _('Webkit Report template not found !'))
        header = report_xml.webkit_header.html
        footer = report_xml.webkit_header.footer_html
        if not header and report_xml.header:
            raise except_osv(
                  _('No header defined for this Webkit report!'),
                  _('Please set a header in company settings')
              )
        if not report_xml.header :
            header = ''
            default_head = addons.get_module_resource('report_webkit', 'default_header.html')
            with open(default_head,'r') as f:
                header = f.read()
        css = report_xml.webkit_header.css
        if not css :
            css = ''
        user = self.pool.get('res.users').browse(cursor, uid, uid)
        company= user.company_id

        translate_call = partial(self.translate_call, parser_instance)
        #default_filters=['unicode', 'entity'] can be used to set global filter
        body_mako_tpl = mako_template(template)
        helper = WebKitHelper(cursor, uid, report_xml.id, context)
        if report_xml.precise_mode:
            for obj in objs:
                parser_instance.localcontext['objects'] = [obj]
                try :
                    html = body_mako_tpl.render(helper=helper,
                                                css=css,
                                                _=translate_call,
                                                **parser_instance.localcontext)
                    htmls.append(html)
                except Exception, e:
                    msg = exceptions.text_error_template().render()
                    logger.error(msg)
                    raise except_osv(_('Webkit render'), msg)
        else:
            try :
                html = body_mako_tpl.render(helper=helper,
                                            css=css,
                                            _=translate_call,
                                            **parser_instance.localcontext)
                htmls.append(html)
            except Exception, e:
                msg = exceptions.text_error_template().render()
                logger.error(msg)
                raise except_osv(_('Webkit render'), msg)
        
        # HACK: 06.10.2015 15:50:34: jool1: set use_default_webkit_path for get_lib methode to call the correct webkit_path
        self.localcontext['use_default_webkit_path'] = report_xml.webkit_header.use_default_webkit_path
        # HACK: 06.10.2015 15:50:34: jool1: use code from "def create_single_pdf" in account_financial_report_webkit if module is installed, otherwise use our code
        module_class = self.pool.get('ir.module.module')
        account_financial_report_webkit_id = module_class.search(cursor, 1, [('name', '=', 'account_financial_report_webkit'), ('state', '!=', 'uninstalled')], context=context)
        if not report_xml.webkit_header.use_default_webkit_path and account_financial_report_webkit_id:
            # NO html footer and header because we write them as text with
            # wkhtmltopdf
            head = foot = False
    
            if report_xml.webkit_debug :
                try :
                    deb = body_mako_tpl.render(helper=helper,
                                               css=css,
                                               _debug=tools.ustr("\n".join(htmls)),
                                               _=translate_call,
                                               **parser_instance.localcontext)
                except Exception, e:
                    msg = exceptions.text_error_template().render()
                    logger.error(msg)
                    raise except_osv(_('Webkit render'), msg)
                return (deb, 'html')
        else:
            head_mako_tpl = mako_template(header)
            try :
                head = head_mako_tpl.render(helper=helper,
                                            css=css,
                                            _=translate_call,
                                            _debug=False,
                                            **parser_instance.localcontext)
            except Exception, e:
                raise except_osv(_('Webkit render'),
                    exceptions.text_error_template().render())
            foot = False
            if footer :
                foot_mako_tpl = mako_template(footer)
                try :
                    foot = foot_mako_tpl.render(helper=helper,
                                                css=css,
                                                _=translate_call,
                                                **parser_instance.localcontext)
                except:
                    msg = exceptions.text_error_template().render()
                    logger.error(msg)
                    raise except_osv(_('Webkit render'), msg)
            if report_xml.webkit_debug :
                try :
                    deb = head_mako_tpl.render(helper=helper,
                                               css=css,
                                               _debug=tools.ustr("\n".join(htmls)),
                                               _=translate_call,
                                               **parser_instance.localcontext)
                except Exception, e:
                    msg = exceptions.text_error_template().render()
                    logger.error(msg)
                    raise except_osv(_('Webkit render'), msg)
                return (deb, 'html')
        
        bin = self.get_lib(cursor, uid)
        # HACK: 06.10.2015 15:50:34: jool1: call generate_pdf from account_financial_report_webkit if module is installed
        if not report_xml.webkit_header.use_default_webkit_path and account_financial_report_webkit_id:
            pdf = self.generate_pdf_account_financial_report_webkit(bin, report_xml, head, foot, htmls, parser_instance=parser_instance)
        else:
            pdf = self.generate_pdf(bin, report_xml, head, foot, htmls, printer=printer, child=child, context=context)
        return (pdf, 'pdf')


    def create(self, cursor, uid, ids, data, context=None):
        """We override the create function in order to handle generator
           Code taken from report openoffice. Thanks guys :) """
        pool = pooler.get_pool(cursor.dbname)
        ir_obj = pool.get('ir.actions.report.xml')
        report_xml_ids = ir_obj.search(cursor, uid,
                [('report_name', '=', self.name[7:])], context=context)
        if report_xml_ids:

            report_xml = ir_obj.browse(cursor,
                                       uid,
                                       report_xml_ids[0],
                                       context=context)
            report_xml.report_rml = None
            report_xml.report_rml_content = None
            report_xml.report_sxw_content_data = None
            report_rml.report_sxw_content = None
            report_rml.report_sxw = None
        else:
            return super(WebKitParser, self).create(cursor, uid, ids, data, context)
        if report_xml.report_type != 'webkit' :
            return super(WebKitParser, self).create(cursor, uid, ids, data, context)

        result = self.create_source_pdf(cursor, uid, ids, data, report_xml, context)
        if not result:
            return (False,False)
        return result
    
    def _sanitize_html(self, html):
        """wkhtmltopdf expects the html page to declare a doctype.
        """
        if html and html[:9].upper() != "<!DOCTYPE":
            html = "<!DOCTYPE html>\n" + html
        return html
