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

from openerp.addons.product.product import check_ean as check_ean13


def check_ean(ean):
    """ Overrides the default check on the module product.

        An EAN can have length 8, 12, 13 or 14.
        If length is 8, 12 or 14 we do not check the value.
        If length is 13, we keep the default current EAN validation.
    """
    if not ean:
        success = True
    elif len(ean) not in (8, 12, 13, 14):
        success = False
    elif len(ean) == 13:
        success = check_ean13(ean)
    else:  # if len(ean) in (8, 12, 14):
        try:
            int(ean)
        except:
            success = False
        else:
            success = True
    return success

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
