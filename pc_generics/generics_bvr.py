# b-*- encoding: utf-8 -*-
##############################################################################
#
#    Copyright (c) 2014 brain-tec AG (http://www.braintec-group.com)
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
import re
import os
from openerp import addons

# The following parameters are used to position correctly the BVR in all the pages.
GAP_BETWEEN_PAGES = 297

# Substract the variable margin_top defined in report_header_footer.xml
bvr_css_top_measures = {'bvr_background': 191.5,
#                         'slip_bank_add_acc': 190,
                        'slip_comp': 200,
                        'slip_bank_acc': 235,
                        'slip_amount': 243.5,
                        'slip_address_b': 252,
#                         'slip2_bank_add_acc': 190,
                        'slip2_comp': 200,
                        'slip2_bank_acc': 235,
                        'slip2_amount': 243.5,
                        'slip2_ref': 226,
                        'slip2_address_b': 238,
                        'ocrbb': 276,
                        }


def _space(nbr, nbrspc=5):
    """Spaces * 5.
    Example:
        >>> self._space('123456789012345')
        '12 34567 89012 345'
    """
    ret = ''
    if nbr:
        ret = ''.join([' '[(i - 2) % nbrspc:] + c for i, c in enumerate(nbr)])
    return ret


_compile_get_ref = re.compile('[^0-9]')



def _get_ref(inv, context=None):
    return inv.get_bvr_ref(context=context)

