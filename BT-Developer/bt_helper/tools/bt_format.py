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
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

import re

import sys
reload(sys)
sys.setdefaultencoding('utf-8')

'''
File with useful methods regarding value formatting.

In order to get access to these methods, you need to import this file. You can do it as follows:

from bt_helper.tools import bt_format
'''


def format_number(number, decimal_point='.', thousand_separator='\'', decimal_digits=2):
    '''Returns a string representation of the specified number after formatting it using the
    specified format information.

    Examples of number formatting using this method:
        - format_number(1234567) ==> 1'234'567.00
        - format_number(1234567.89, decimal_digits=1) ==> 1'234'567.9
        - format_number(1234567.89, ',', ' ', decimal_digits=3) ==> 1 234 567,890

    @param number: number to format
    @type number: int or float

    @param decimal_point: the decimal point symbol
    @type decimal_point: str

    @param thousand_separator: the thousand separator symbol
    @type thousand_separator: str

    @param decimal_digits: the number of digits after the decimal point
    @type decimal_digits: int'''

    format_str = '{0:.' + str(decimal_digits) + 'f}'
    number_str = format_str.format(number).replace('.', '#')
    return _intersperse(number_str, thousand_separator).replace('#', decimal_point)


#######################
# Auxiliary Functions #
#######################


def _split(l, counts):
    res = []
    saved_count = len(l)

    for count in counts:
        if not l:
            break

        if count == -1:
            break

        if count == 0:
            while l:
                res.append(l[:saved_count])
                l = l[saved_count:]

            break

        res.append(l[:count])
        l = l[count:]
        saved_count = count

    if l:
        res.append(l)

    return res


def _reverse(s):
    return s[::-1]


_regex_intersperse = re.compile('([^0-9]*)([^#]*)(.*)')


def _intersperse(string, separator=''):
    left, middle, right = _regex_intersperse.match(string).groups()
    splits = _split(_reverse(middle), [3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3])
    res = separator.join(map(_reverse, _reverse(splits)))
    return left + res + right

def check_if_zero(value):
    return abs(value) < 0.000001
