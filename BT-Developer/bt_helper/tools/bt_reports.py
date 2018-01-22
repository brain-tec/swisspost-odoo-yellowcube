# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>).
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

import netsvc


'''
File with useful methods to work with reports.

In order to get access to these methods, you need to import this file. You can do it as follows:

from bt_helper.tools import bt_reports
'''


def generate_report(cr, uid, xml_report_name, object_ids, name_to_save, context={}):
    '''Generates a report on demand, returning a two-element tuple where the second element is the
    binary of such a report. You can use the binary, for example, to generate a mail attachment.

    ----------------
    Example of usage
    ----------------

    for ship_report in self.pool.get('ship_report').browse(cr, uid, ship_report_ids, context):
        if ship_report.name:
            # Generates and attaches ship reports
            attachment_name = ustr(ship_report.name) + _(' Ship Report_') + ustr(ship_report.id)

            (attach_name, attach_binary) = \
                bt_reports.generate_report(cr, uid, 'ship_report.report', [ship_report.id],
                                           attachment_name, context)

            if attach_binary:
                attachments[attach_name] = attach_binary

    -----------------

    :param: string xml_report_name The name of the report as specified in the XML report record.
    :param: list object_ids List of object ids that must be used to generate the report (the model
                            associated with these objects must be the model defined in the XML
                            report record).
    :param: string name_to_save The name of the report file to be generated.
    :return: tuple The following two-element tuple: (report_name_with_extension, report_binary)'''

    try:
        # The string provided to the LocalService class is composed of:
        # 'report': fixed string
        # 'xml_report_name': the name (not the id) of the XML report record
        service = netsvc.LocalService('report.' + xml_report_name)
        (report_binary, report_format) = service.create(cr, uid, object_ids, {}, context)

        return (name_to_save + '.' + report_format, report_binary)
    except:
        return (False, False)


def delete_report_from_db(NAMES):
    '''
    @param param NAMES: List of string with the report names OR
                         a single name 
    '''
    if type(NAMES) is not list:
        NAMES = [NAMES]
    for name in NAMES:
        if 'report.' + name in netsvc.Service._services:
            del netsvc.Service._services['report.' + name]
