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

'''
File with useful methods to work with users.

In order to get access to these methods, you need to import this file. You can do it as follows:

from bt_helper.tools import bt_users
'''


def is_in_groups(delegate, cr, uid, group_list, context):
    
    # Bugfixing: If language is not "en_US" the group.full_name will 
    # be traduced to language in context and result will allways be False
    #TODO look for safer solution
    context={'lang': 'en_US'}
    
    
    '''Returns True if the current user belongs to any of the specified groups, False otherwise.

    @param group_list: list of group full names (e.g., ['Human Resources / Employee'])
    @type group_list: list of str elements'''

    user = delegate.pool.get('res.users').browse(cr, uid, uid, context)

    for group in user.groups_id:
        if group.full_name in group_list:
            return True

    return False
