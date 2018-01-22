# b-*- encoding: utf-8 -*-
##############################################################################
#
#    Copyright (c) 2017 brain-tec AG (http://www.braintec-group.com)
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


class CommonTestFunctionalityFollowupPF(object):

    def get_delay_followup_level(self, delegate, followup_level_id):
        """ Returns the delay of the given follow-up level.
        """
        cr, uid, ctx = delegate.cr, delegate.uid, delegate.context
        followup_level_obj = self.registry('followup.level')
        followup_level = followup_level_obj.browse(
            cr, uid, followup_level_id, context=ctx)
        return followup_level.delay

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
