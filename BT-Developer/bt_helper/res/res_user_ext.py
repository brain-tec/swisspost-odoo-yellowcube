# b-*- encoding: utf-8 -*-
##############################################################################
#
#    Copyright (c) 2012 brain-tec AG (http://www.brain-tec.ch) 
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
from osv import fields,osv,orm
import logging
logger = logging.getLogger(__name__)
#logger.setLevel(logging.INFO) 
logger.setLevel(logging.DEBUG)
#logger.setLevel(logging.WARNING)
#logger.setLevel(logging.NOTSET)

class res_user_ext(osv.Model):
    _inherit = 'res.users'
    """
    Fix the bug ==>
       "Settings" : "Users" : "Add advanced filter": i.e, Administration is True
       "Einstellungen" :  "Benutzer" : "Erweiterte Filter" : i.e, Administration is True
    
    """

    
   
    def search_group_operation(self,cr,uid,groups_ids,operation,context={}):
        """
        Receives as input parameter a set of groups and a operation. 
        If the operation is != then 
            we will return the ids of those users that are not mapped at any groups_ids
        otherwise then 
            we will return the ids of those users that are mapped at least in one group of groups_ids.
        """
        logger.debug("Search group: {0}. Operation: {1}.".format(groups_ids,operation))
        if groups_ids == [] or groups_ids[0] == 'false' : return [-1]
        groups_ids = map(int,groups_ids)
        ALL_USERS = self.search(cr,uid,[])
        ALL_USERS_OBJS = self.browse(cr,uid,ALL_USERS)
        
        #
        # Check the operation
        #
        result = []
        for user in ALL_USERS_OBJS:
            user_group = [x.id for x in user.groups_id]
            if operation == '!=' :
                if common_elements(groups_ids,user_group) == []: result.append(user.id)
            else:
                if common_elements(groups_ids,user_group) != []: result.append(user.id)
        if result == [] : return [-1]
        return result
    
    
    
    def search_in_group(self,cr,uid,arg,context={}):
        """
        Receives a query in arg.
        In the case that it contains the attribute 'in_group_'
        Then we make this operation and return the res.user ids that hold this property.
        """
        
        if len(arg) != 3 : return[]
        if 'in_group_' not in arg[0] : return []
        logger.debug('Inside search in group')
        #
        # Get the group ids to search for and return the 
        #
        groups_ids = arg[0].replace('in_group_','').split('_')
        return self.search_group_operation(cr,uid,groups_ids,arg[1],context)

    
    def search_in_groups(self,cr,uid,arg,context={}):
        """
        Receives a query in arg.
        In the case that it contains the attribute 'in_groups_'
        Then we make this operation and return the res.user ids that hold this property.
        
        See that is is similar than in_group_ => Therefore we call the previous one.
        """
        
        value = list(arg)
        value[0] = value[0].replace('in_groups_','in_group_')
        return self.search_in_group(cr,uid,value,context)
        
                                
    
    def search_sel_group(self,cr,uid,arg,context={}):
        """
        Receives a query in arg.
        In the case that it contains the attribute 'sel_groups_'
        Then we make this operation and return the res.user ids that hold this property.
        """
        #
        # If it is not sel_groups => Continue
        #
        if len(arg) != 3 : return[]
        if 'sel_groups_' not in arg[0]: return []
        #
        #  There are different options in sel group :
        #    a) IS + VALUE
        #    b) IS NOT + VALUE
        #    c) IS SET
        #    d) IS NOT SET
        #  
        groups_ids = []
        op = arg[1]
        #
        # The type of argv[2] for options a) and b) is boolean.
        # 
        if type(arg[2]) == type(True):
            groups_ids = arg[0].replace('sel_groups_','').split('_')
            #
            # We need to change the operation signal (it is defined in negative not in positive).
            # 
            if op == '!=' : op = '='
            else : op = '!='
        else:
            #
            # Otherwise we are in options c) and d) => argv[2] contains the id of the group to look for. 
            groups_ids = [arg[2]]
            
        return self.search_group_operation(cr,uid,groups_ids,op,context)        
    
    def search(self, cr, uid, args, offset=0, limit=None, order=None,
                context={}, count=False):
        """
        There is a bug when we try to select some users by using sel_groups, in_groups_ and in_group attributes.
        What we do is transform these queries into ['id','in',list_of_ids]
        where list_of_ids are those res.users that hold the query. 
        """
        for i in range(0,len(args)):
            # We check all the input queries and just in case that 
            # we detect the strange query => we change this field
            results = []
            results.extend(self.search_in_group(cr,uid,args[i],context)) 
            results.extend(self.search_sel_group(cr,uid,args[i],context)) 
            results.extend(self.search_in_groups(cr,uid,args[i],context)) 
            if results != [] : args[i] = ['id', 'in', results]

        return super(res_user_ext, self).search(cr, uid, args=args, offset=offset, limit=limit, order=order,
                context=context, count=count)
             
def common_elements(list1, list2):
    """
    Function used to compare two lists.
    """
    return [element for element in list1 if element in list2]   
    
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
