# -*- coding: utf-8 -*-
##############################################################################
#
# Copyright (c) 2012 brain-tec AG
# All Right Reserved
#
# Author : Fux Philipp (brain-tec)
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

{
    "name": "Webkit Report Engine brain-tec",
    "description": """
This is the modification of the Webkit Report Engine - provided by brain-tec
=====================================================================================================================

New Features:
-----------------
Objects are printed as single pdf and combined at the end
Setup printers under Settings/Companies/Webkit Printers
Setup child reports under Customization/Low Level Objects/Actions/Reports => Webkit Reports
Setup direct printing option => This directly prints the file to the printer
Setup alternate printing option => This directly prints the child Report to the printer



Requirements and Installation for webkit
-----------------------------------------
This module requires the ``wkthtmltopdf`` library to render HTML documents as
PDF. Version 0.9.9 or later is necessary, and can be found at http://code.google.com/p/wkhtmltopdf/
for Linux, Mac OS X (i386) and Windows (32bits).

After installing the library on the OpenERP Server machine, you need to set the
path to the ``wkthtmltopdf`` executable file on each Company.

If you are experiencing missing header/footer problems on Linux, be sure to
install a "static" version of the library. The default ``wkhtmltopdf`` on
Ubuntu is known to have this issue.


Printer configuration
------------------------------
Install cups on the server: aptitude install cups
Then go to the url:631 to configure the printers

Ensure that the port 631 is accessible from the url
( Configure the cups file, because per default it only accepts localhost:631 )
Also add this part in the cups File:
<Location/>
Allow from all
<Location>

Requirements and Installation for direct printing
-----------------------------------------

1. Setup a new printer
    a) search for all printers with command: ``lpstat -p``
    b) select the printer and search the arguments: ``lpoptions -p hp -l`` (hp is my previously found printer name)
    c) create a ``lp`` statement with the options you want: ``lp -p hp -o InputSlot=Tray2``
    d) Put this statement in the Field ``Primary tray command`` and add the other statement in ``Alternative tray command`` ( Could be Tray3 )
    
2. Setup the reports under Customization/Low Level Objects/Actions/Report

3. Add this import in the Mako File
   ``from report_webkit import report_sxw_ext``
4. Launch the report_sxw_ext instead of report_sxw:
   ``report_sxw_ext.report_sxw_ext('report.webkitaccount.invoice',
                       'account.invoice', 
                       'addons/report_webkit_sample/report/report_webkit_html.mako',
                       parser=report_webkit_html)``


                    """,
    "version": "1.3",
    "depends": ["base"],
    "author": "brain-tec",
    "category": "Reporting", # i.e a technical module, not shown in Application install menu
    "url": "http://http://www.brain-tec.ch/",
    "data": [ "security/ir.model.access.csv",
              "printer_view.xml",
              "data.xml",
              "wizard/report_webkit_actions_view.xml",
              "company_view.xml",
              "header_view.xml",
              "ir_report_view.xml",
              "printer_view.xml",
    ],
    "installable": True,
    "auto_install": False,
    'images': ['images/companies_webkit.jpeg','images/header_html.jpeg','images/header_img.jpeg'],
}

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
