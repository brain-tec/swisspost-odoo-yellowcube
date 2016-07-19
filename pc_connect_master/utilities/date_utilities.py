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

from datetime import datetime, timedelta
from openerp.osv import fields
from openerp.tools import DEFAULT_SERVER_DATETIME_FORMAT
from pytz import timezone
import pytz


def get_number_of_natural_hours(start_date, num_working_hours, weekday_start_hour, weekday_end_hour, weekdays, mode='forward'):
    ''' Returns the number of natural hours to reach the number of working hours that are received as argument,
        and taking into account the opening/ending hour of each working day. The working days are received as a dictionary,
        with the key being the zero-based day of the week, e.g. weekdays[2] indicates whether Wednesday is opened.
    '''
    num_natural_hours = 0
    current_date = start_date
    num_current_working_hours = 0

    while num_current_working_hours < num_working_hours:
        num_natural_hours += 1

        if mode.lower() in ('forward', 'forwards'):
            current_date += timedelta(hours=1)
        if mode.lower() in ('backward', 'backwards'):
            current_date -= timedelta(hours=1)

        if 0 <= current_date.isoweekday() <= 4:
            # We are on a working day, so now we check if this particular day we are opened,
            # and also if we're opened over this period of time.
            if weekdays[current_date.isoweekday()] and (weekday_start_hour <= current_date.hour < weekday_end_hour):
                num_current_working_hours += 1

    return num_natural_hours


def get_number_of_natural_days(start_date, num_weekdays, mode, actual_weekdays=None):
    ''' Returns the number of natural days to reach the number of weekdays that are received
        as an argument, starting on the given date. This is useful if you want to use a timedelta()
        which only takes into account natural days: so instead of doing:
           timedelta(days=num_weekdays), do
           timedelta(days=get_number_of_natural_days(num_weekdays)), since timedelta() has not an
        option to consider only weekdays, but only natural ones.

        start_date must be a datetime.datetime object.

        Parameter mode must be 'backward' or 'forward'.

        Parameter actual_weekdays is a dictionary with 7 values, from 0 to 6, indicating the number
        of the day (Monday being number 0) and if that day is a weekday or a non-working day.
        By default it considers weekdays from Monday to Friday, also if it receives that there are not
        actual weekdays (i.e. if all of them are set to False).
    '''
    if (actual_weekdays is None) or (sum(map(int, actual_weekdays.values())) == 0):
        actual_weekdays = {
            0: True,  # Monday.
            1: True,  # Tuesday.
            2: True,  # Wednesday.
            3: True,  # Thursday.
            4: True,  # Friday.
            5: False,  # Saturday.
            6: False,  # Sunday.
        }

    num_natural_days = 0
    current_date = start_date
    num_current_weekdays = 0

    while num_current_weekdays < num_weekdays:
        num_natural_days += 1

        if mode.lower() == 'forward':
            current_date += timedelta(days=1)
        if mode.lower() == 'backward':
            current_date -= timedelta(days=1)

        if actual_weekdays[current_date.weekday()]:
            num_current_weekdays += 1

    return num_natural_days


def get_dates_of_current_quarter():
    ''' Returns a tuple of strings, each one encoding a date in the format yyyy-mm-dd.
        The two dates encode the starting and ending date for the current quarter.
    '''
    now = datetime.now()
    month_number = now.month
    year_number = now.year

    if 1 <= month_number <= 3:
        starting_date = '{0:04d}-01-01'.format(year_number)
        ending_date = '{0:04d}-03-31'.format(year_number)
    elif 4 <= month_number <= 6:
        starting_date = '{0:04d}-04-01'.format(year_number)
        ending_date = '{0:04d}-06-30'.format(year_number)
    elif 7 <= month_number <= 9:
        starting_date = '{0:04d}-07-01'.format(year_number)
        ending_date = '{0:04d}-09-30'.format(year_number)
    else:  # if 10 <= month_number <= 12:
        starting_date = '{0:04d}-10-01'.format(year_number)
        ending_date = '{0:04d}-12-31'.format(year_number)

    return (starting_date, ending_date)


def get_dates_of_current_week():
    ''' Returns a tuple of strings, each one encoding a date in the format yyyy-mm-dd.
        The two dates encode the starting and ending date for the current week.
    '''
    now = datetime.now()
    current_day_of_week = now.weekday()  # Starts at 0 (Monday) and ends at 6 (Sunday).
    starting_date = now - timedelta(days=current_day_of_week)
    ending_date = now + timedelta(days=6 - current_day_of_week)
    starting_date = '{0:04d}-{1:02d}-{2:02d}'.format(starting_date.year, starting_date.month, starting_date.day)
    ending_date = '{0:04d}-{1:02d}-{2:02d}'.format(ending_date.year, ending_date.month, ending_date.day)

    return (starting_date, ending_date)


def get_next_day_datetime(cr, uid, hour, minutes, timezone_str, actual_weekdays=None):
    ''' Returns the datetime of the next day, at the hour indicated following the timezone provided
        as a datetime object with UTC-0.

        Parameter actual_weekdays is a dictionary with 7 values, from 0 to 6, indicating the number
        of the day (Monday being number 0) and if that day is a weekday or a non-working day.
        By default it considers weekdays from Monday to Friday, also if it receives that there are not
        actual weekdays (i.e. if all of them are set to False).
    '''
    if (actual_weekdays is None) or (sum(map(int, actual_weekdays.values())) == 0):
        actual_weekdays = {
            0: True,  # Monday.
            1: True,  # Tuesday.
            2: True,  # Wednesday.
            3: True,  # Thursday.
            4: True,  # Friday.
            5: False,  # Saturday.
            6: False,  # Sunday.
        }

    now_str = fields.datetime.now()
    now = datetime.strptime(now_str, DEFAULT_SERVER_DATETIME_FORMAT)
    now += timedelta(days=get_number_of_natural_days(now, 1, 'forward', actual_weekdays))
    next_date_datetime = now.replace(hour=hour, minute=minutes, second=0, microsecond=0)

    timezone_to_use = timezone(timezone_str)
    localised_time = timezone_to_use.localize(next_date_datetime)  # Sets it on the timezone indicated.
    next_date_datetime = localised_time.astimezone(timezone('Etc/UTC'))  # Odoo expects it on UTC-0
    return next_date_datetime


def get_hours_minutes_from_float(float_time):
    ''' Given a floating point number encoding a time, it returns a tuple with the hours and minutes.
        For example, if 15.00 is received, it returns hours=15, minutes=0,
                     if 15.50 is received, it returns hours=15, minutes=30,
                     if 15.75 is received, it returns hours=15, minutes=45.
    '''
    hours = int(float_time)
    minutes = int((float_time - hours) * 60.0)
    return hours, minutes

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
