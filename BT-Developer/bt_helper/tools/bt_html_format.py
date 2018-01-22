# b-*- encoding: utf-8 -*-
##############################################################################
#
#    Copyright (c) 2015 brain-tec AG (http://www.braintec-group.com)
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
import re
from lxml import html
from lxml.html.clean import Cleaner


def get_cleaned_html(html_string, plain=False):
        """
            Replaces all the span tags with "style='font-weight: bold;' for
            strong tags before removing all the style tags, attributes and CSS classes.
        """
        res_string = ""
        if plain:
            html_parser = html.fromstring(html_string)
            for element in html_parser.xpath('//*[@style]'):
                    if element.tag == 'span':
                        style = element.attrib.get('style')
                        if style:
                            if 'bold' in style:
                                element.tag = 'strong'
    
            html_without_style = html.tostring(html_parser)
            safe_attrs = ['abbr', 'accept', 'accept-charset', 'accesskey', 'align',
                          'alt', 'axis', 'border', 'cellpadding', 'cellspacing', 'char', 'charoff',
                          'charset', 'checked', 'cite', 'clear', 'cols', 'colspan',
                          'color', 'compact', 'coords', 'datetime', 'dir', 'disabled', 'enctype',
                          'for', 'frame', 'headers', 'height', 'hreflang', 'hspace', 'id',
                          'ismap', 'label', 'lang', 'longdesc', 'maxlength', 'media', 'method',
                          'multiple', 'name', 'nohref', 'noshade', 'nowrap', 'prompt', 'readonly',
                          'rel', 'rev', 'rows', 'rowspan', 'rules', 'scope', 'selected', 'shape',
                          'size', 'span', 'src', 'start', 'summary', 'tabindex', 'target', 'title',
                          'type', 'usemap', 'valign', 'value', 'vspace', 'width']
    
            html.clean.defs.safe_attrs = safe_attrs
            Cleaner.safe_attrs = html.clean.defs.safe_attrs
            cleaner = Cleaner(style=True, page_structure=False, remove_unknown_tags=True,
                              safe_attrs_only=True)
            res_string = cleaner.clean_html(html_without_style)
        else:
            """
                Cleans the html saving the style attribute,
                but removing all the style tags, style fonts attributes and css classes .
            """

            html_parser = html.fromstring(html_string)
            for element in html_parser.xpath('//*[@style]'):
                    if element.tag == 'span':
                        style = element.attrib.get('style')
                        if style:
                            if 'font-family' in style:
                                p = re.compile('font-family:\s*[\w ,]+\s*;')
                                element.attrib['style'] = p.sub("", style)
                            if 'font-size' in style:
                                p = re.compile('font-size:\s*[\w ,]+\s*;')
                                element.attrib['style'] = p.sub("", style)
    
            html_without_font_family = html.tostring(html_parser)
    
            safe_attrs = ['abbr', 'accept', 'accept-charset', 'accesskey', 'align',
                          'alt', 'axis', 'border', 'cellpadding', 'cellspacing', 'char', 'charoff',
                          'charset', 'checked', 'cite', 'clear', 'cols', 'colspan',
                          'color', 'compact', 'coords', 'datetime', 'dir', 'disabled', 'enctype',
                          'for', 'frame', 'headers', 'height', 'href', 'hreflang', 'hspace', 'id',
                          'ismap', 'label', 'lang', 'longdesc', 'maxlength', 'media', 'method',
                          'multiple', 'name', 'nohref', 'noshade', 'nowrap', 'prompt', 'readonly',
                          'rel', 'rev', 'rows', 'rowspan', 'rules', 'scope', 'selected', 'shape',
                          'size', 'span', 'src', 'start', 'style','summary', 'tabindex', 'target', 'title',
                          'type', 'usemap', 'valign', 'value', 'vspace', 'width']
    
            html.clean.defs.safe_attrs = safe_attrs
            Cleaner.safe_attrs = html.clean.defs.safe_attrs
            cleaner = Cleaner(style=False, page_structure=False, kill_tags=['style'], remove_unknown_tags=True,
                              safe_attrs_only=True)
            res_string = cleaner.clean_html(html_without_font_family)
        return res_string




# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: