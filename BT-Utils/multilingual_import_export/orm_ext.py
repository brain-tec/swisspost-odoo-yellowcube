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
from openerp.osv import osv, fields, orm
from openerp.tools.translate import _
import functools
from openerp.addons.base_import.models import ir_import

__field_recursion = 0


def __new_fields_get_keys(f):
    """
    This function decorates the method ir_import.get_fields, so the field '.lang' is always
    included in the import web UI.
    """
    @functools.wraps(f)
    def __fields_get_keys_delegate(*args, **kargs):
        global __field_recursion
        __field_recursion += 1
        r = f(*args, **kargs)
        __field_recursion -= 1
        if __field_recursion == 0:
            # This method is recursive, and new fields must be attached after recursion
            r.append({'fields': [],
                      'required': False,
                      'id': '.lang',
                      'string': 'MultiLanguage field',
                      'name': '.lang'})
        return r
    return __fields_get_keys_delegate


def __new_load(f):
    """
    This function decorates the function orm.BaseModel.load, in order to import different languages

    if the csv is missing a '.lang' field it follows the standard behavior
    if the field '.lang' is not the last one, it will fail (import is faster if the last field is
     the only on to be removed.
    if the '.lang' field is the last one, it will import each row one by one changing the context
     'lang' variable to the value of the field '.lang'

    returns the same error messages as the original function, and uses rollbacks to avoid
     inconsinstencies
    """
    @functools.wraps(f)
    def __import_load(self, cr, uid, fields, data, context=None):
        # No .lang defined, act as always
        if not ('.lang' in fields):
            return f(self, cr, uid, fields, data, context=context)

        # .lang is not the last field, the import must be stopped (it is not optimal)
        if ('.lang' != fields[-1]):
            return {'ids': False,
                    'messages': [{'type': 'error',
                                  'message': '.lang must be the last field in the list'}]}

        if context is None:
            context = {}
        else:
            context = dict(context)
        # save previous value of context['lang'], restore at the exit
        old_lang = None
        if 'lang' in context:
            old_lang = context['lang']
        found_error = None
        # create a savepoint in the DB for consistency
        cr.execute("SAVEPOINT model_load_save_multilingual")
        # output message. If ids is false, it is and error (as described in messages
        result = {'ids': [], 'messages': []}
        data_lang = {}
        langs = []
        if old_lang != None:
            langs = [old_lang]
            
        for data_line in data:
            # First, we extract the info by language, in order to keep o2m relations
            _lang = data_line[-1]
            if _lang in data_lang:
                data_lang[_lang].append(data_line[:-1])
            else:
                if _lang not in langs:
                    langs.append(_lang)
                data_lang[_lang] = [data_line[:-1]]

        for _lang in langs:
            # for each data_line, we change the context language, and import every field,
            #  except for the last one '.lang'
            context['lang'] = _lang
            if _lang is None:
                del context['lang']
            to_import_data = data_lang[_lang]
            r = f(self, cr, uid, fields[:-1], to_import_data, context=context)
            if r['ids']:
                result['ids'].extend(r['ids'])
            else:
                # if ids is false, there is an error. It must be reported, and DB needs a rollback
                messages = [{'type': 'error',
                             'message': 'Error importing language {0}'.format(_lang)}]
                for item in r['messages']:
                    messages.append(item)
                found_error = {'ids': False, 'messages': messages}
                break

        if found_error:
            cr.execute("ROLLBACK TO SAVEPOINT model_load_save_multilingual")
        else:
            cr.execute("RELEASE SAVEPOINT model_load_save_multilingual")
        # context language is re-set
        context['lang'] = old_lang
        if old_lang is None:
            del context['lang']
        return found_error or result
    return __import_load


def __new_import_data(f):
    """
    This function decorates the function orm.BaseModel.load, in order to import different languages

    if the csv is missing a '.lang' field it follows the standard behavior
    if the field '.lang' is not the last one, it will fail (import is faster if the last field is
     the only on to be removed.
    if the '.lang' field is the last one, it will import each row one by one changing the context
     'lang' variable to the value of the field '.lang'

    returns the same error messages as the original function, and uses rollbacks to avoid
     inconsinstencies
    """
    @functools.wraps(f)
    def __import_data(self, cr, uid, fields, datas, mode='init', current_module='', noupdate=False, context=None, filename=None):
        # No .lang defined, act as always
        if '.lang' not in fields:
            return f(self, cr, uid, fields, datas, mode=mode, current_module=current_module, noupdate=noupdate, context=context, filename=filename)

        # .lang is not the last field, the import must be stopped (it is not optimal)
        if '.lang' != fields[-1]:
            return {'ids': False,
                    'messages': [{'type': 'error',
                                  'message': '.lang must be the last field in the list'}]}

        if context is None:
            context = {}
        else:
            context = dict(context)
        # save previous value of context['lang'], restore at the exit
        old_lang = None
        if 'lang' in context:
            old_lang = context['lang']
        found_error = None
        # create a savepoint in the DB for consistency
        cr.execute("SAVEPOINT model_load_save_multilingual")
        # output message. If ids is false, it is and error (as described in messages
        result = [0, 0, 0, 0]
        data_lang = {}
        langs = []
        if old_lang != None:
            langs = [old_lang]

        for data_line in datas:
            # First, we extract the info by language, in order to keep o2m relations
            _lang = data_line[-1]
            if _lang in langs:
                data_lang[_lang].append(data_line[:-1])
            else:
                langs.append(_lang)
                data_lang[_lang] = [data_line[:-1]]

        for _lang in langs:
            # for each data_line, we change the context language, and import every field,
            #  except for the last one '.lang'
            context['lang'] = _lang
            if _lang is None:
                del context['lang']
            if _lang not in data_lang:
                continue
            to_import_data = data_lang[_lang]
            r = f(self, cr, uid, fields[:-1], to_import_data, mode=mode, current_module=current_module, noupdate=noupdate, context=context, filename=filename)
            result[0] = r[0]
            if r[2]:
                result[1] = r[1]
                result[2] = r[2]
                result[3] = r[3]
                found_error = True
                break

        if found_error:
            cr.execute("ROLLBACK TO SAVEPOINT model_load_save_multilingual")
        else:
            cr.execute("RELEASE SAVEPOINT model_load_save_multilingual")
        # context language is re-set
        context['lang'] = old_lang
        if old_lang is None:
            del context['lang']
        return tuple(result)
    return __import_data


def __new_export(f):
    """
    This function decorates orm.BaseModel.export_data, so multiple language descriptions of a
     record are exported.
    """
    @functools.wraps(f)
    def __export_delegate(self, cr, uid, ids, fields_to_export, context=None):
        if not self.pool.get('res.users').read(cr,
                                               uid,
                                               uid,
                                               ['use_multilang'],
                                               context=context)['use_multilang']:
            return f(self, cr, uid, ids, fields_to_export, context=context)
        result = []
        if context is None:
            context = {}
        # save previous value of context['lang'], restore at the exit
        old_lang = None
        if 'lang' in context:
            old_lang = context['lang']
        # we select every language code available to the system, with translation support
        cr.execute('SELECT code FROM res_lang WHERE active AND translatable')
        # we append at the end, the new field, '.lang'
        fields_to_export.append('.lang')
        languages = [x[0] for x in cr.fetchall()]
        lang_offset = -1
        lang_len = len(languages)
        for lang in languages:
            # for each language we export all data for the selected elements
            lang_offset += 1
            context['lang'] = lang
            lang_result = f(self, cr, uid, ids, fields_to_export[:-1], context=context)
            if lang_offset == 0:
                # for the first language, we reserve the list required to keep all data
                result = range(len(lang_result['datas']) * lang_len)
            item_id = -1
            for item in lang_result['datas']:
                # for each item, we add the language field, and save it in its position in the list
                item_id += 1
                # this formula keeps same records together, with alternating languages.
                #  Easier to understand
                item_pos = item_id * lang_len + lang_offset
                item.append(lang)
                if lang_offset > 0 and False:  # if True, CSV redundant data will be removed
                    original_item = result[item_id * lang_len]
                    for i in range(len(item))[1:]:
                        if item[i] == original_item[i]:
                            item[i] = None
                result[item_pos] = item
        context['lang'] = old_lang
        if old_lang is None:
            del context['lang']
        return {'datas': result}
    return __export_delegate


orm.BaseModel.export_data = __new_export(orm.BaseModel.export_data)
orm.BaseModel.load = __new_load(orm.BaseModel.load)
orm.BaseModel.import_data = __new_import_data(orm.BaseModel.import_data)
ir_import.get_fields = __new_fields_get_keys(ir_import.get_fields)


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
