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

from tools.translate import _

# Fixes encoding problems
from tools import ustr

import pytz
from pytz import timezone
from datetime import datetime
from datetime import timedelta
from datetime import date
from dateutil.relativedelta import relativedelta
import math

# Regular expressions
import re

# Checks object types
import types
import openerp

# Sorts, groups and prints lists
import operator
import itertools

# Removes accents from especial characters
import unicodedata

# Accesses local services as reports or work-flows
import netsvc

"""
File with useful methods to work with dates

* in order to get access to these methods you need to import this file:
import bt_helper.tools.bt_dates as bt_dates
"""



#########################
# DATE RELATED FUNCTIONS
#########################

MONTHS = [
    (1, _('January')),
    (2, _('February')),
    (3, _('March')),
    (4, _('April')),
    (5, _('May')),
    (6, _('June')),
    (7, _('July')),
    (8, _('August')),
    (9, _('September')),
    (10, _('October')),
    (11, _('November')),
    (12, _('December')),
]

DEUTSCH_MONTHS = [
    (1, 'Januar'),
    (2, 'Februar'),
    (3, 'März'),
    (4, 'April'),
    (5, 'Mai'),
    (6, 'Juni'),
    (7, 'Juli'),
    (8, 'August'),
    (9, 'September'),
    (10, 'Oktober'),
    (11, 'November'),
    (12, 'Dezember'),
]

def get_string_months(state):
    """
    This function is used to return the key corresponding to a specific state.

    :param: string state
    :return: string key
    """
    for key, value in MONTHS:
        if key == state:
            return value

    return None

def get_string_deutsch_months(state):
    """
    This function is used to return the key corresponding to a specific state.

    :param: string state
    :return: string key
    """
    for key, value in DEUTSCH_MONTHS:
        if key == state:
            return value

    return None

def today():
    '''Returns a string date with no time information.'''
    return datetime.today().strftime('%Y-%m-%d')

def now():
    '''Returns a string date with time information.'''
    return datetime.now().strftime('%Y-%m-%d %H:%M:%S')

def first_month_day_from_date(str_date=False):
    '''Returns a string date with first day month information.'''
    try:
        if not str_date:
            # return current month first day
            date = datetime.today()
        else:
            date = get_date(str_date)

        return date.strftime('%Y-%m-01')
    except:
        return False

def last_month_day_from_date(str_date=False):
    '''Returns a string date with last day month information.'''
    try:
        if not str_date:
            # return current month first day
            date = datetime.today()
        else:
            date = get_date(str_date)

        return str(date + relativedelta(months= +1, day=1, days= -1))[:10]
    except:
        return False

def strftime(date_time, format='%Y-%m-%d', language=False):
    '''Returns the string representation of the specified datetime object using the specified format.
    This method is similar to "datetime.strftime(...)" except for the fact that this method
    localizes some strings (for now, it only localizes full months) using the current user's
    language instead of the current python's locale.'''

    try:
        if format.find('%B') != -1:
            # format = format.replace('%B', MONTHS[date_time.month - 1])
            # NOTE: The line above should be enough to translate the months, but as the translation doesn't work here
            # we have to use to different vars and the next 6 lines:
            #    - MONTHS and deutsch_MONTHS
            if language == 'de_DE':
                format = format.replace('%B', get_string_deutsch_months(date_time.month))
            else:
                # we return by default the english translation
                format = format.replace('%B', get_string_months(date_time.month))

        return ustr(date_time.strftime(format))
    except:
        return False

def strftime_str(str_date_time, format='%Y-%m-%d', language=False, tz=False):
    '''Returns the string representation of the specified string date or date time using the
    specified format. This method is similar to "datetime.strftime(...)" except for the fact that
    this method localizes some strings (for now, it only localizes full months) using the current
    user's language instead of the current python's locale.'''

    date_time = get_datetime(str_date_time)

    if date_time and tz:
        date_time = date_time.replace(tzinfo=pytz.utc)
        date_time = date_time.astimezone(timezone(tz))

    if not date_time:
        date_time = get_date(str_date_time)

    return strftime(date_time, format, language)

def get_date(str_date):
    '''Returns a datetime object with no time information.'''
    try:
        return datetime.strptime(str_date, '%Y-%m-%d')
    except:
        return False

def get_datetime(str_datetime):
    '''Returns a datetime object with time information.'''
    try:
        return datetime.strptime(str_datetime, '%Y-%m-%d %H:%M:%S')
    except:
        try:
            return datetime.strptime(str_datetime, '%Y-%m-%d')
        except:
            return False

def get_numeric_values_from_date(str_date):
    '''Returns the triplet (day, month, year).'''
    try:
        result_date = datetime.strptime(str_date, '%Y-%m-%d')
        return (result_date.day, result_date.month, result_date.year)
    except:
        return False

def update_days(str_date, days):
    '''Adds or substracts the specified days to the specified date.'''
    try:
        new_date = datetime.strptime(str_date, '%Y-%m-%d') + timedelta(days=days)
        return new_date.strftime('%Y-%m-%d')

    except Exception:
        import logging
        logging.getLogger('update_days').exception('Could not calculate the requested date')

        return False

def update_months(str_date, months):
    '''Adds or substracts the specified months to the specified date.'''
    try:
        new_date = datetime.strptime(str_date, '%Y-%m-%d') + relativedelta(months=months)
        return new_date.strftime('%Y-%m-%d')

    except Exception:
        import logging
        logging.getLogger('update_days').exception('Could not calculate the requested date')

        return False

def get_difference_in_months(str_date_from, str_date_to):
    '''Return the difference of two dates in months 01.01.2013-31.12.2013 -> 12 Months'''
    date_from = datetime.strptime(str_date_from, '%Y-%m-%d')
    date_to = datetime.strptime(str_date_to, '%Y-%m-%d')
    start_month=date_from.month
    end_months=(date_to.year-date_from.year)*12 + date_to.month+1
    dates=[datetime(year=yr, month=mn, day=1) for (yr, mn) in (((m - 1) / 12 + date_from.year, (m - 1) % 12 + 1) for m in range(start_month, end_months))]
    return len(dates)    

def get_difference_in_days(str_date_from, str_date_to):
    '''Returns the number of days between the two specified dates plus one. Therefore, if the two
    dates specified are equal, the difference is 1 (not 0). Note that the first date must be smaller
    than the second one.'''
    try:
        delta = (datetime.strptime(str_date_to, '%Y-%m-%d') -
                 datetime.strptime(str_date_from, '%Y-%m-%d'))

        return delta.days + 1
    except:
        return False

def get_overlapping_days(str_date_from_1, str_date_to_1, str_date_from_2, str_date_to_2):
    '''Returns the number of overlapping days between the two specified periods. Negative results
    are always changed to 0.'''
    try:
        latest_from = max(datetime.strptime(str_date_from_1, '%Y-%m-%d'),
                          datetime.strptime(str_date_from_2, '%Y-%m-%d'))
        earliest_to = min(datetime.strptime(str_date_to_1, '%Y-%m-%d'),
                          datetime.strptime(str_date_to_2, '%Y-%m-%d'))

        delta = earliest_to - latest_from

        return max(0, delta.days + 1)
    except:
        return False

def convert_float_time(float_val):
    '''Returns a float time as readable time (e.g. 07:20) '''
    negative = False
    if float_val < 0.0:
        negative = True
        
    hours = math.floor(abs(float_val))
    mins = round(abs(float_val)%1+0.01,2)
    if mins >= 1.0:
        hours = hours + 1
        mins = 0.0
    else:
        mins = mins * 60
    float_time = '%02d:%02d' % (hours,mins)
    
    if negative:
        float_time = '-' + float_time
    return float_time  
