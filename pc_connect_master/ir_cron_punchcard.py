# b-*- encoding: utf-8 -*-
##############################################################################
#
#    Copyright (c) 2015 brain-tec AG (http://www.brain-tec.ch)
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
from openerp import fields, models, api
from datetime import datetime
from openerp.tools import DEFAULT_SERVER_DATETIME_FORMAT


class ir_cron_punchcard(models.Model):
    _name = 'ir.cron.punchcard'
    _rec_name = 'create_date'
    _order = 'create_date DESC'

    @api.one
    def unlink(self):
        self.active = False

    @api.multi
    def entry_exists_after_or_at(self, ir_cron_id, today_date, target_hour):
        ''' Checks if, for the given scheduler, exists an entry for today which has an
            hour which is greater or equal than the provided one (target_hour)
        '''

        # Sets the timezone to that indicated in the configuration.
        config = self.env['configuration.data'].get()
        context = self.env.context.copy()
        context['tz'] = config.support_timezone

        entries_today = self.with_context(context).search([('ir_cron', '=', ir_cron_id),
                                                           ('execution_day', '>=', today_date),
                                                           ], order='create_date DESC', context=context)

        for entry in entries_today:
            create_time_local = fields.datetime.context_timestamp(cr, uid, datetime.strptime(entry.create_date, DEFAULT_SERVER_DATETIME_FORMAT), context)
            if create_time_local.time() >= target_hour:
                return True

        return False

    ir_cron = fields.Integer('Scheduler', required=True, readonly=True)  # fields.many2one('ir.cron', 'Scheduler', required=True, readonly=True),
    create_date = fields.Datetime('Create date', required=True, readonly=True)
    create_uid = fields.Many2one(comodel_name='res.users', string='Executer', required=True, readonly=True)
    execution_day = fields.Date('Execution day', required=True, readonly=True, default=lambda *args: datetime.now())
    active = fields.Boolean('Active?', default=True)

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
