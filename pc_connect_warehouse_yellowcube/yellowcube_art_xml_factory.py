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

from xml_abstract_factory import xml_factory_decorator, xml_abstract_factory
from openerp.addons.pc_log_data.log_data import write_log
from openerp.addons.pc_connect_master.utilities.others import format_exception
from datetime import datetime
from openerp.osv import osv
from openerp.tools import DEFAULT_SERVER_DATETIME_FORMAT
from openerp.tools.translate import _
from lxml import etree
import logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


_element_to_check = {
    'ArticleDescription': lambda text, attrib: (text[:40], attrib),
}



@xml_factory_decorator("art")
class yellowcube_art_xml_factory(xml_abstract_factory):
    _table = "stock.location"

    post_issue_tags = ['art-file']
    post_issue_thread = True
    success = False
    base_priority = -1
    ignore_product_ids = False
    force_product_ids = False

    def __init__(self, *args, **kargs):
        logger.debug("ART factory created")

    def create_element(self, entity, text=None, attrib=None,
                       ns='https://service.swisspost.ch/apache/yellowcube/'
                          'YellowCube_ART_REQUEST_Artikelstamm.xsd'):
        element = self.xml_tools.create_element(entity, text, attrib, ns)
        if entity in _element_to_check:
            validation_errors = self.xml_tools.validate_xml('art', element,
                                                            print_error=False)
            if validation_errors:
                f = _element_to_check[entity]
                t, a = f(text, attrib)
                logger.debug(
                    "Changing element {0} values {1}, {2} into: {3}, {4}".format(
                        entity, text, attrib, t, a))
                element = self.xml_tools.create_element(entity, t, a, ns)
        return element

    def _check(self, obj, cond, msg):
        if not cond:
            self.post_issue(obj, msg)
            self.success = False
        return bool(cond)

    def get_main_file_name(self, _object):
        art_date_format = self.get_param('file_date_sufix', required=True)
        return '{1}'.format(_object.name,
                            datetime.now().strftime(art_date_format))

    def import_file(self, file_text):
        logger.debug("Unrequired functionality")
        return True

    def get_export_files(self, sale_order):
        return {}

    def generate_root_element(self, stock_location, domain=None):
        self.success = True
        self.processed_items = []

        # xml = '<?xml version="1.0" encoding="UTF-8"?>\n'
        # xml = '{0}<WAB xsi:noNamespaceSchemaLocation="YellowCube_WAB_Warenausgangsbestellung.xsd" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">\n'.format(xml)
        # xsi = 'http://www.host.org/2001/XMLSchema-instance'
        # art_loc = 'https://service.swisspost.ch/apache/yellowcube/YellowCube_ART_REQUEST_Artikelstamm.xsd'
        xml_root = self.xml_tools.create_root('{{{art}}}ART')

        # WAB > ControlReference
        now = datetime.now()
        xml_control_reference = self.create_element('ControlReference')
        xml_control_reference.append(self.create_element('Type', text='ART'))
        xml_control_reference.append(self.create_element(
            'Sender', text=self.get_param('sender', required=True)))
        xml_control_reference.append(self.create_element(
            'Receiver', text=self.get_param('receiver', required=True)))
        xml_control_reference.append(self.create_element(
            'Timestamp',
            text='{0:04d}{1:02d}{2:02d}{3:02d}{4:02d}{5:02d}'.format(now.year, now.month, now.day, now.hour, now.hour, now.minute)
        ))
        xml_control_reference.append(self.create_element(
            'OperatingMode',
            text=self.get_param('operating_mode', required=True)))
        xml_control_reference.append(self.create_element('Version', text='1.0'))
        xml_root.append(xml_control_reference)

        xml_article_list = self.create_element('ArticleList')
        xml_root.append(xml_article_list)
        product_pool = self.pool.get('product.product')
        self.cr.execute("SELECT code FROM res_lang WHERE active")
        languages = [x[0] for x in self.cr.fetchall()]

        basic_domain = [
            ('type', '!=', 'service')
        ]
        if self.force_product_ids:
            basic_domain.append(('id', 'in', self.force_product_ids))
        if self.ignore_product_ids:
            basic_domain.append(('id', 'not in', self.ignore_product_ids))
        
        if self.get_param('enable_product_lifecycle'):
            # Field 'product_state' is defined on the product's lifecycle.
            basic_domain.append(('product_state', '!=', 'draft'))
        else:
            # If we don't have the product's lifecycle, we just consider if
            # the product is active.
            basic_domain.append(('active', '=', True))

        if domain:
            # If a domain is passed by argument, we extend the basic one
            for x in domain:
                basic_domain.append(x)
        empty_file = True
        product_ids = product_pool.search(self.cr, self.uid, basic_domain, context=self.context)
        for product_id in product_ids:
            self.processed_items.append(('product.product', product_id))
            empty_file = False
            xml_article_list.append(self._generate_article_element(product_pool.browse(self.cr, self.uid, product_id, context=self.context), languages))
        if empty_file:
            return None

        xsd_error = self.xml_tools.validate_xml(
            "art", xml_root, print_error=self.print_errors)
        if xsd_error:
            write_log(self, self.cr, self.uid, self._table,
                      stock_location.name, stock_location.id,
                      'XSD validation error', correct=False,
                      extra_information=xsd_error)
            raise Warning(xsd_error)
        return xml_root

    def _generate_article_element(self, product, languages, raise_error=False):

        def mtq_to_cmq(number):
            ''' Receives a number which is in MTQ (cubic meters)
                and returns its equivalent in CMQ (cubic centimeters).
                1 m^3 == 1000000 cm^3.
            '''
            return 1000000.0 * number

        xml = self.create_element('Article')
        xml.append(etree.Comment("Model: product.product ID: {0}".format(product.id)))
        errors_list = []

        # The ChangeFlag tag is computed differently depending on if the 
        # product's lifecycle is enabled or not.
        change_flag = ''
        if self.get_param('enable_product_lifecycle'):
            if product.product_state == 'in_production':
                if product.yc_YCArticleNo:
                    change_flag = 'U'
                else:
                    change_flag = 'I'
            elif product.product_state == 'deactivated':
                change_flag = 'D'
            else:
                change_flag = 'U'
        else:
            def _product_under_sale():
                sol = self.env['sale.order.line'].search([('product_id', '=', product.id),
                                                          ('state', 'not in', ['cancel', 'done'])],
                                                         limit=1)
                return True if sol else False
            if (product.state != 'obsolete') or _product_under_sale():
                if product.yc_YCArticleNo:
                    change_flag = 'U'
                else:
                    change_flag = 'I'
            else:
                change_flag = 'D'

        dp_pool = self.pool.get('decimal.precision')
        weight_format = '{{0:.{0}f}}'.format(dp_pool.precision_get(self.cr, self.uid, 'Stock Weight'))
        length_format = '{{0:.{0}f}}'.format(dp_pool.precision_get(self.cr, self.uid, 'Stock Length'))
        width_format = '{{0:.{0}f}}'.format(dp_pool.precision_get(self.cr, self.uid, 'Stock Width'))
        height_format = '{{0:.{0}f}}'.format(dp_pool.precision_get(self.cr, self.uid, 'Stock Height'))
        volume_format = '{{0:.{0}f}}'.format(dp_pool.precision_get(self.cr, self.uid, 'Stock Volume'))

        xml.append(self.create_element('ChangeFlag', change_flag))
        xml.append(self.create_element(
            'DepositorNo', self.get_param('depositor_no', required=True)))
        xml.append(self.create_element(
            'PlantID', self.get_param('plant_id', required=True)))
        xml.append(self.create_element('ArticleNo', product.default_code))
        if not product.uom_id.uom_iso:
            logger.error(_("Undefined UOM ISO code: {0}"
                           ).format(product.uom_id.name))
        xml.append(self.create_element('BaseUOM', product.uom_id.uom_iso))
        xml.append(self.create_element(
            'NetWeight', weight_format.format(product.weight_net), {'ISO': 'KGM'}))
        xml.append(self.create_element(
            'BatchMngtReq', '1' if product.track_outgoing else '0'))

        min_rem_life = product.expiration_accept_time
        period_exp_date_type = product.expiration_accept_time_uom
        if period_exp_date_type:
            # If they UOM is not set, then we don't add this field
            xml.append(self.create_element('MinRemLife', int(min_rem_life)))
            # Each Unit of Measure has a different code according to the mapping table X01.00
            translations = {'days': '',
                            'weeks': '1',
                            'months': '2',
                            'years': '3'}
            error_message = _("Value for system's parameter 'default_expiration_accept_time_uom' is '{0}' while it must be one of {1}.").format(period_exp_date_type, ','.join(translations.keys()))
            partial_success = self._check(product, period_exp_date_type in translations, error_message)
            if partial_success:
                xml.append(self.create_element(
                    'PeriodExpDateType', translations[period_exp_date_type]))
            else:
                errors_list.append(error_message)

        # OPTIONAL xml.append(create_element('PeriodExpDateType', '???'))
        xml.append(self.create_element(
            'SerialNoFlag', '1' if product.yc_track_outgoing_scan else '0'))

        xml_uom = self.create_element('UnitsOfMeasure')
        xml.append(xml_uom)
        if product.ean13:
            xml_uom.append(self.create_element(
                'EAN', product.ean13, {'EANType': product.get_ean_type()}))
        xml_uom.append(self.create_element(
            'AlternateUnitISO', product.uom_id.uom_iso))
        if not product.uom_id.uom_iso:
            logger.error('Missing ISO code for UOM %s' % product.uom_id.name)
        xml_uom.append(self.create_element(
            'GrossWeight', weight_format.format(product.weight),
            {'ISO': 'KGM'}))
        xml_uom.append(self.create_element(
            'Length', length_format.format(product.length), {'ISO': 'CMT'}))
        xml_uom.append(self.create_element(
            'Width', width_format.format(product.width), {'ISO': 'CMT'}))
        xml_uom.append(self.create_element(
            'Height', height_format.format(product.height), {'ISO': 'CMT'}))
        xml_uom.append(self.create_element(
            'Volume', volume_format.format(mtq_to_cmq(product.volume)),
            {'ISO': 'CMQ'}))

        xml_desc = self.create_element('ArticleDescriptions')
        xml.append(xml_desc)
        product_pool = self.pool.get('product.product')
        names = {}
        for lang in languages:
            if lang[:2] not in ['de', 'fr', 'it', 'en']:
                continue
            _name = product_pool.read(self.cr, self.uid, [product.id], ['name'], {'lang': lang})[0]['name']
            if lang[:2] not in names:
                xml_desc.append(self.create_element(
                    'ArticleDescription', _name,
                    {'ArticleDescriptionLC': lang[:2]}))
                names[lang[:2]] = _name

        xsd_error = self.xml_tools.validate_xml(
            self._factory_name, xml, print_error=self.print_errors)
        if xsd_error:
            if raise_error:
                raise osv.except_osv('XSD validation error', xsd_error)
            else:
                write_log(self, self.cr, self.uid, 'product.product', product.name, product.id, 'XSD validation error', correct=False, extra_information=xsd_error)
        else:
            date_current_str = datetime.now().strftime(DEFAULT_SERVER_DATETIME_FORMAT)
            self.pool.get('product.product').write(self.cr,
                                                   self.uid,
                                                   [product.id],
                                                   {'yc_last_changeflag_submitted': change_flag,
                                                    'yc_last_changeflag_submitted_date': date_current_str})
        if self.success:
            return xml
        else:
            raise Warning(_('Errors appeared while generating the ART file:\n{0}'.format('\n'.join(errors_list))))

    def generate_files(self, domain=None, ignore_product_ids=None, force_product_ids=None, multifile=False):
        self.base_priority = -1
        if not multifile:
            # If call standard way, we delegate on typical creation
            self.ignore_product_ids = ignore_product_ids
            self.force_product_ids = force_product_ids
            return xml_abstract_factory.generate_files(self, domain=domain)
        else:
            self.ignore_product_ids = None
            self.force_product_ids = None

        product_domain = ['&',
                          ('id', 'not in', ignore_product_ids or []),
                          ('id', 'in', force_product_ids),
                          ]
        
        if not force_product_ids:
            product_domain = [product_domain[1]]
        else:
            self.base_priority = 1

        products_to_export = self.pool.get('product.product').search(self.cr, self.uid, product_domain, context=self.context)
        logger.debug("Exporting {0} files for {1} products".format(self._factory_name, len(products_to_export)))
        self.main_file_id = None
        sender = self.get_param('sender', required=True)
        table_model = self.pool[self._table]
        # search_domain = []#[('xml_export_state', '=', 'draft')]
        # For each object that matches the domain, we create its xml file
        object_ids = table_model.search(self.cr, self.uid, domain, context=self.context)
        for _object in table_model.browse(self.cr, self.uid, object_ids, context=self.context):
            main_file_name = self.get_main_file_name(_object)
            if not main_file_name:
                raise Warning(_('Missing filename for main object {0} {1}#{2}').format(_object.name, self._table, _object.id))
            for product_id in products_to_export:
                try:
                    object_id = _object.id
                    # We generated the final filename, according to task with ID=2922
                    object_filename = "{sender}_{factory_name}_{name}_sub{sub}.xml".format(
                        sender=sender,
                        factory_name=self._factory_name,
                        name=self.xml_tools.export_filename(main_file_name, self.context),
                        sub=product_id)

                    logger.debug("Exporting xml for {2} {0} into file {1}".format(object_id, object_filename, self._table))
                    # The name of the main xml, is appened to each related file
                    self.context['filename_prefix'] = "{0}_".format(object_filename[:-4])
                    # The XML root is generated
                    xml_node = self.generate_root_element(_object, domain=[('id', '=', product_id)])
                    if xml_node is None:
                        continue
                    xml_output = self.xml_tools.xml_to_string(xml_node, remove_ns=True)
                    # The associated files are copied
                    self.main_file_id = None
                    self.save_file(xml_output, object_filename, main=True, binary=False, record_id=product_id, model='product.product')
                    self.mark_as_exported(_object.id)
                    # Finally, the XML file is copied. This ensures that XML files have its dependencies copied to the folder
                    write_log(self, self.cr, self.uid, self._table, _object.name, object_id, 'XML export successful', correct=True, extra_information=object_filename, context=self.context)
                except Warning as e:
                    write_log(self, self.cr, self.uid, self._table, _object.name, object_id, 'XML export error', correct=False, extra_information=format_exception(e), context=self.context)
                    logger.error("Exception exporting into xml {0}: {1}".format(object_id, format_exception(e)))
                finally:
                    if 'filename_prefix' in self.context:
                        del self.context['filename_prefix']
        return True

    def get_base_priority(self):
        """
        ART files are not critic
        """
        return self.base_priority

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
