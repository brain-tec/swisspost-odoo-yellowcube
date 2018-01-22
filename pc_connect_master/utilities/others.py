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


import sys
import traceback


def compact_csv_string(content, sep=','):
    """ Receives a string the fields of which are separated using the
        optionally provided separator, and returns it ensuring that
        no whitespaces are between the contents and the separator,
        e.g. if received 'a ; b; c; d ;   e' it would return 'a;b;c;d;e'
        assuming the separator is ';'
    """
    if isinstance(content, basestring):
        return sep.join(content.split(sep))
    else:
        raise TypeError("Parameter 'content' must be of type string.")


def format_exception(exception):
    """ Formats an exception depending on its type.

        Copied from bt_helper of repository BT-Developer by brain-tec AG.
    """
    _traceback = traceback.format_exc(limit=10)
    if isinstance(exception, IOError):
        return "{0}\n{1}\n{2}\n{3}\n{4}".format(exception,
                                                exception.errno or '',
                                                exception.strerror or '',
                                                sys.exc_info()[0] or '',
                                                _traceback)
    else:
        return "{0}\n{1}\n{2}".format(exception, sys.exc_info()[0] or '',
                                      _traceback)


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
