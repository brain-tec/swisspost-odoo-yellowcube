# b-*- encoding: utf-8 -*-
##############################################################################
#
#    Copyright (c) 2010 brain-tec AG (http://www.brain-tec.ch) 
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

from osv import fields, osv

class ir_cron_ext(osv.osv):
    _inherit = "ir.cron"

    def button_execute_job(self, cr, uid, ids, context=None):
        if ids:
            this = self.browse(cr, uid, ids, context=context)[0]
            self._callback(cr, uid, this.model, this.function, this.args, ids[0] if ids else [])
        return True

ir_cron_ext()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
