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
import logging


def create_db_index(cr, index_name, table_name, criteria):
    cr.execute('SELECT tablename FROM pg_tables WHERE tablename = %s;', (table_name,))
    if not cr.fetchall():
        logging.getLogger(__name__).error('Table %s not found' % table_name)
        return
    cr.execute('SELECT indexname FROM pg_indexes WHERE indexname = %s;', (index_name,))
    if not cr.fetchall():
        cr.execute('CREATE INDEX {0} ON {1} ({2});'.format(index_name, table_name, criteria))

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
