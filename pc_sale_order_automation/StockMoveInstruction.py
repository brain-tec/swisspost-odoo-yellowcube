# b-*- encoding: utf-8 -*-
##############################################################################
#
#    Copyright (c) 2016 brain-tec AG (http://www.braintec-group.com
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

from collections import namedtuple


# Defines a named tuple in order to encode an instruction to apply over a stock move
#
# Meaning of the fields:
# - command: can be any of the following options:
#   * copy: Indicates that the stock move has to be copied to result in a new one.
#   * update: Indicates that the stock move has to be updated.
#   * none: Indicates that nothing has to be done over the stock move.
# - move_option: can be any of the following options:
#   * wait: If the stock move has to be set in waiting for availability because some goods are missing.
#   * deliver: If the stock move can be set in ready to be delivered.
# - stock_move_id: The ID of the stock.move this instructions applies to.
# - values: A dictionary containing the values to apply when calling copy() of write() for the commands
#           copy and update, respectively.
StockMoveInstruction = namedtuple('StockMoveInstruction', 'command move_option stock_move_id values')


def goods_are_available(instructions_list):
    """ Returns if some goods are available, which happens if at least one instruction
        has 'deliver' as the move_option.
    """
    for instruction in instructions_list:
        if instruction.move_option == 'deliver':
            return True
    return False


def backorder_has_to_be_created(instructions_list):
    """ Returns if a back-order has to be created, which happens if at least one instruction
        has 'wait' as the move_option.
    """
    for instruction in instructions_list:
        if instruction.move_option == 'wait':
            return True
    return False


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
