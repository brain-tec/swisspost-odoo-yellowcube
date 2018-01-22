# b-*- encoding: utf-8 -*-
##############################################################################
#
#    Copyright (c) 2015 brain-tec AG (http://www.braintec-group.com)
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

from datetime import datetime


def get_difference_time(date_1, date_2):
    ''' Gets the difference between two dates (as Python objects), in seconds.
    '''
    return abs(date_1 - date_2).total_seconds()


def get_difference_time_str(date_str_1, date_str_2):
    ''' Gets the difference between two dates (as strings), in seconds.
    '''
    date_1 = datetime.strptime(date_str_1, '%Y-%m-%d %H:%M:%S')
    date_2 = datetime.strptime(date_str_2, '%Y-%m-%d %H:%M:%S')
    return get_difference_time(date_1, date_2)

