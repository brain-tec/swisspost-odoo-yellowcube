# b-*- encoding: utf-8 -*-
##############################################################################
#
#    Copyright (c) 2016 brain-tec AG (http://www.braintec-group.com)
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


def get_free_memory_in_kb():
    """ Returns an integer with the free memory of the system, in kB.
        It simply parses the file /proc/meminfo and reads its field MemFree.
    """
    mem_free = 0
    lines_meminfo = open('/proc/meminfo').read().splitlines()
    for line in lines_meminfo:
        fields = line.split(' ')
        key = fields[0]
        if key in ('MemFree:', 'Buffers:', 'Cached:'):
            mem_free += int(fields[-2])
            if key == 'Cached:':
                break  # Since they are always sorted in MemFree, Buffers, Cached order, we can skip the rest.
    return mem_free


def get_free_memory_in_mb():
    return get_free_memory_in_kb() / 1024


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
