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

import date_utilities


def _replace_week_placeholders(self, cr, uid, args, context=None):
    ''' Generates the placeholders for the XML which defines the filter for the current week.
        The code of this filter had to be done partially in Python, thus the reason of this function.
    '''
    if context is None:
        context = {}
    if context.get('this_week', False):
        for arg in args:
            this_mon, this_sun = date_utilities.get_dates_of_current_week()
            if len(arg) > 2:
                if arg[2] == 'this_mon':
                    arg[2] = this_mon
                elif arg[2] == 'this_sun':
                    arg[2] = this_sun
    return args


def _replace_quarter_placeholders(self, cr, uid, args, context=None):
    ''' Generates the placeholders for the XML which defines the filter for the current quarter.
        The code of this filter had to be done partially in Python, thus the reason of this function.
    '''
    if context is None:
        context = {}
    if context.get('this_quarter', False):
        for arg in args:
            start_of_this_quarter, end_of_this_quarter = date_utilities.get_dates_of_current_quarter()
            if len(arg) > 2:
                if arg[2] == 'start_of_this_quarter':
                    arg[2] = start_of_this_quarter
                elif arg[2] == 'end_of_this_quarter':
                    arg[2] = end_of_this_quarter
    return args


def _replace_delivery_to_customer_placeholders(self, cr, uid, args, context=None):
    ''' Generates the placeholders for the XML which defines the filter for the
        destination location when it is equal to the location "Partner Locations / Customer"
        The code of this filter had to be done partially in Python, thus the reason of this function.
    '''
    if context is None:
        context = {}
    if context.get('delivery_to_customer', False):
        stock_location_obj = self.pool.get('stock.location')
        for arg in args:
            customer_location_ids = stock_location_obj.search(cr, uid,
                                                              [('complete_name', '=', 'Partner Locations / Customers')],
                                                              context=context, limit=1)
            if len(arg) > 2:
                if arg[2] == 'customer_location':
                    arg[2] = customer_location_ids[0]
    return args


def search(self, cr, uid, args, super_class, offset=0, limit=None, order=None, context=None, count=False):
    ''' Adds three new filters, added in addition to the ones defined in the XML.
        - Search for the instances done in this week.
        - Search for the instances done in this quarter.
        - Search for the instances delivered to customer
    '''
    if context is None:
        context = {}
    if ('this_week' in context):
        args = self._replace_week_placeholders(cr, uid, args, context=context)
    elif ('this_quarter' in context):
        args = self._replace_quarter_placeholders(cr, uid, args, context=context)
    elif ('delivery_to_customer' in context):
        args = self._replace_delivery_to_customer_placeholders(cr, uid, args, context=context)
    return super(super_class, self).search(cr, uid, args=args, offset=offset, limit=limit, order=order, context=context, count=count)


def read_group(self, cr, uid, domain, fields, groupby, super_class, offset=0, limit=None, context=None, orderby=False):
    ''' Adds the possibility to group when using the three new filters, added in addition to the ones defined in the XML.
        - Search for the instances done in this week.
        - Search for the instances done in this quarter.
        - Search for the instances delivered to customer
    '''
    if context is None:
        context = {}
    if ('this_week' in context):
        domain = self._replace_week_placeholders(cr, uid, domain, context=context)
    elif ('this_quarter' in context):
        domain = self._replace_quarter_placeholders(cr, uid, domain, context=context)
    elif ('delivery_to_customer' in context):
        domain = self._replace_delivery_to_customer_placeholders(cr, uid, domain, context=context)
    return super(super_class, self).read_group(cr, uid, domain, fields, groupby, offset, limit, context, orderby)

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
