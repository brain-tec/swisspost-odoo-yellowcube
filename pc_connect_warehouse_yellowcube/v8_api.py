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

def cr_uid_ids_context(f):
    """
    mock-up for the same function in v8
    
    assures ids is a list
    """
    def _wrap(self, cr, uid, ids, *args, **kargs):
        if not isinstance(ids, list):
            ids = [ids]
        return f(self, cr, uid, ids, *args, **kargs)
    return _wrap

def cr_uid_ids(f):
    return cr_uid_ids_context(f)
