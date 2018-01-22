# b-*- encoding: utf-8 -*-
##############################################################################
#
#    Copyright (c) 2015 brain-tec AG (http://www.brain-tec.ch)
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
from osv import osv, fields
from bt_helper.log_rotate import get_log
logger = get_log('NOTSET')


class one2many_line_ext(fields.one2many):
    def get(self, cr, obj, ids, name, user=None, offset=0, context=None, values=None):
        super_ids = super(one2many_line_ext, self).get(cr, obj, ids, name, user, offset, context, values)
        module_class = obj.pool.get('ir.module.module')
        order_editor_id = module_class.search(cr, 1, [('name', '=', 'bt_order_editor'), ('state', '!=', 'uninstalled')])
        logger.debug("One 2 many filter {0}".format(super_ids))
        if order_editor_id:
            super_ids = self.get_sale_order_editor(cr, obj, ids, name, user, offset, context, values, super_ids)
        logger.debug("One 2 many filter After bt_order editor{0}".format(super_ids))
        stage_discount_id = module_class.search(cr, 1, [('name', '=', 'stage_discount'), ('state', '!=', 'uninstalled')])
        if stage_discount_id:
            super_ids = self.get_stage_discount(cr, obj, ids, name, user, offset, context, values, super_ids)
        logger.debug("One 2 many filter After stage_discount{0}".format(super_ids))
        return super_ids

    def get_sale_order_editor(self, cr, obj, ids, name, user=None, offset=0, context=None, values=None, super_ids=[]):
        logger.debug("Get one 2 many line ext")
        logger.debug("Context 1234 {0}".format(context))
        if context is None:
            context = {}
        if not values:
            values = {}
        res = {}
        logger.debug("Calling super")
        ids2 = super_ids
        print "IDS2 {0}".format(ids2)
        if not context.get('custom_search_line_editor', False):
            return ids2
        # do not remove
        order_line_ids = [0]
        for key in ids2:
            order_line_ids.extend(ids2[key])
        del context['custom_search_line_editor']
        logger.debug("Continue...")
        for var_id in ids:
            res[var_id] = []
        category_id = context.get('change_category_id', False)
        if not category_id and len(values) > 0:
            category_id = values[0].get('category_id', False)

        if not category_id and ids:
            try:
                cr.execute("""select category_id from sale_order where id = {0}""".format(ids[0]))
                result = [x[0] for x in cr.fetchall()]
                if result:
                    category_id = result[0]
            except:
                raise
            logger.debug("Given category id {0}".format(category_id))

        if category_id:
            logger.debug("Filtered by category_id {0}".format(category_id))
            ids2 = obj.pool.get(self._obj).search(cr, user, [(self._fields_id, 'in', ids), ('id', 'in', order_line_ids),
                                                             ('category_id', '=', category_id)],
                                                  limit=self._limit)
        else:
            logger.debug("No category_id => see all!!")
            ids2 = obj.pool.get(self._obj).search(cr, user, [(self._fields_id, 'in', ids), ('id', 'in', order_line_ids)],
                                                  limit=self._limit)
            logger.debug("Ids = {0}".format(",".join(map(str, ids2 + [0]))))

        for r in obj.pool.get(self._obj)._read_flat(cr, user, ids2, [self._fields_id], context=context, load='_classic_write'):
            res[r[self._fields_id]].append(r['id'])

        logger.debug("Result => {0}".format(res))
        return res

    def get_stage_discount(self, cr, obj, ids, name, user=None, offset=0, context=None, values=None, super_ids=[]):
        if context is None:
            context = {}
        if not values:
            values = {}
        logger.debug("Get one 2 many line ext... stage_discount")
        ids2 = super_ids
        if not context.get('custom_search_line_discount', False):
            if 'custom_remove_subtotal' not in context:
                logger.debug("ADDING THIS!!")
                return ids2
            else:
                logger.debug("ADDING THIS (1)!!")
                order_line_ids = [0]
                for key in ids2:
                    order_line_ids.extend(ids2[key])
                res = {}
                for var_id in ids:
                    res[var_id] = []
                ids2 = obj.pool.get(self._obj).search(cr, user, [(self._fields_id, 'in', ids), ('is_subtotal', '=', False), ('id', 'in', order_line_ids)], limit=self._limit)
                for r in obj.pool.get(self._obj)._read_flat(cr, user, ids2, [self._fields_id], context=context, load='_classic_write'):
                    res[r[self._fields_id]].append(r['id'])
                return res

        # do not remove
        del context['custom_search_line_discount']
        logger.debug("ADDING THIS (2)!!")
        order_line_ids = [0]
        for key in ids2:
            order_line_ids.extend(ids2[key])
        res = {}
        for var_id in ids:
            res[var_id] = []

        ids2 = obj.pool.get(self._obj).search(cr, user, [(self._fields_id, 'in', ids), ('is_discount', '=', False), ('id', 'in', order_line_ids)], limit=self._limit)
        for r in obj.pool.get(self._obj)._read_flat(cr, user, ids2, [self._fields_id], context=context, load='_classic_write'):
            res[r[self._fields_id]].append(r['id'])
        return res


def make_safe(context, ids):
    if context is None:
        context = {}
    if not isinstance(ids, list):
        ids = [ids]
    return (context, ids)

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
