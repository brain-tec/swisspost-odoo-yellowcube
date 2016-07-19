# b-*- encoding: utf-8 -*-
##############################################################################
#
#    Copyright (c) 2014 brain-tec AG (http://www.brain-tec.ch)
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

import traceback
import sys


def format_exception(exception):
    _traceback = traceback.format_exc(limit=10)
    if isinstance(exception, IOError):
        return "{0}\n{1}\n{2}\n{3}\n{4}".format(exception, exception.errno or '', exception.strerror or '', sys.exc_info()[0] or '', _traceback)
    else:
        return "{0}\n{1}\n{2}".format(exception, sys.exc_info()[0] or '', _traceback)

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
