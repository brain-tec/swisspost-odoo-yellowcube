Setup instructions 
===

If you have financial report webkit then you must change the following things:


Configuration:
==
            Webkit Headers/Footers
            Select your report:
           (For instance)           
           - Financial Landscape Header
           - Financial Portrait Header

The flag "Use webkit_path from params to generate the report" must be checked.

Check that you have the following system.parameters, 
and the following executables are on the system.

System Parameter:

* webkit_path

            /home/openerp/wkhtmltopdf/wkhtmltopdf-amd64
            -> wkhtmltopdf 0.11.0 rc1

* webkit_path_financial_reports

            /home/openerp/wkhtmltopdf/wkhtmltopdf 
            -> wkhtmltopdf 0.12.1 (with patched qt)
