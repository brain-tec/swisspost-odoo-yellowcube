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
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program. If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

from osv import osv, fields
import logging
import tools
from time import mktime
from datetime import datetime


class printer(osv.osv):
    _name = "printer"
    _description = "Printer Management"

    _columns = {
        'name': fields.char('Printer', size=64, required=True),
        'primary_tray': fields.text('Primary tray command'),
        'alternative_tray': fields.text('Alternative tray command'),
        'third_tray': fields.text('3rd tray command'),
        'fourth_tray': fields.text('4th tray command'),
    }

printer()

class res_users(osv.osv):
    _inherit = "res.users"
    _columns = {
                'printer_id':fields.many2one('printer', 'Printer', required=False),
    }
res_users()   