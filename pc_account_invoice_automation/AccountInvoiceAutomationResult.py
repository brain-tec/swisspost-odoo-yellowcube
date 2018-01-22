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

import os


class AccountInvoiceAutomationResult:
    def __init__(self):
        self.message = ''
        self.next_state = False
        self.error = False

    def __iadd__(self, other):
        """ Overloads the += operator.
        """
        if other.message:
            # Messages are appended.
            self.message = '{0}{1}{2}'.format(
                self.message, os.linesep, other.message)
        self.next_state = other.next_state  # Overridden.
        self.error = self.error or other.error  # Propagated.
        return self

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
