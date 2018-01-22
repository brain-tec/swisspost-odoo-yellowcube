Copyright (c) 2017 brain-tec AG (http://www.braintec-group.com)
All Right Reserved

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU Affero General Public License as
published by the Free Software Foundation, either version 3 of the
License, or (at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU Affero General Public License for more details.

You should have received a copy of the GNU Affero General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.


NOTES
===============================================================================

The following modules were taken from the version 7 of the so called
"BT modules":

* BT-Followup
    * bt_followup
* BT-Accounting
    * bt_account
    * bt_indicator
    * bt_oplist
    * bt_payment_difference
    * bt_tax
    * l10n_ch_base_bank 
    * l10n_ch_payment_slip
* BT-Developer
    * bt_helper
    * bt_export_all
* BT-Discount
    * stage_discount
* BT-Webkit
    * report_webkit
* BT-Utils
    * multilingual_import_export
    * one2many_filter
    * export_to_xml

Some comments:

* BT-Accounting/l10n_ch_base_bank and BT-Accounting/l10n_ch_payment_slip are 
copies of the modules in l10n-switzerland with some patches/extensions.

* BT-Accounting/bt_indicator and BT-Accounting/bt_oplist, are modules 
installed which are only used by bt_allocation, which is not installed in 
PCAP. Then, we don't have dependencies to them but we might need them as 
independent modules. 

* BT-Utils/bt_export_all is installed, but we don't have dependencies to
them although we might need them as independent modules.
