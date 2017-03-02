# -*- coding: utf-8 -*-
##############################################################################
#
#    Copyright (c) 2016 brain-tec AG (http://www.braintec-group.com)
#    All Right Reserved
#
#    See LICENSE file for full licensing details.
##############################################################################
from openerp.tools.translate import _
from openerp.addons.stock_connector import BackendProcessor
from openerp.addons.connector import backend
from openerp.addons.stock_connector import stock_backend_alpha
from openerp.addons.stock_connector.models.backend_processor\
    import CheckBackends as oldCheckBackends
from .art_processor import ArtProcessor
from .bar_processor import BarProcessor
from .bur_processor import BurProcessor
from .wab_processor import WabProcessor
from .war_processor import WarProcessor
from .wba_processor import WbaProcessor
from .wbl_processor import WblProcessor
from lxml import etree
import logging
logger = logging.getLogger(__name__)


# Here we define the backend and the current version
wh_yc_backend = backend.Backend(parent=stock_backend_alpha,
                                version='0.1-yellowcube-1.0')

PROCESSORS_FOR_IMPORT = {
    'WBA': lambda s, f: WbaProcessor(s).yc_read_wba_file(f),
    'WAR': lambda s, f: WarProcessor(s).yc_read_war_file(f),
    'BAR': lambda s, f: BarProcessor(s).yc_read_bar_file(f),
    'BUR': lambda s, f: BurProcessor(s).yc_read_bur_file(f),
}


def CheckBackends():
    oldCheckBackends()
    if wh_yc_backend not in backend.BACKENDS.backends:
        backend.BACKENDS.register_backend(wh_yc_backend)


@wh_yc_backend
class BackendProcessorExt(BackendProcessor):
    """
    This class delegates the creation of all the files needed by YellowCube
    """

    def __init__(self, environment):
        super(BackendProcessorExt, self).__init__(environment)
        self.processors = PROCESSORS_FOR_IMPORT.copy()

    def file_type_is_enable(self, _type):
        _type = _type.lower()
        if _type == 'art':
            return self.backend_record.yc_parameter_sync_products
        if _type == 'wab' or _type == 'war':
            return self.backend_record.yc_parameter_sync_picking_out
        if _type == 'wbl' or _type == 'wba':
            return self.backend_record.yc_parameter_sync_picking_in
        if _type == 'bur':
            return self.backend_record.yc_parameter_sync_inventory_moves
        if _type == 'bar':
            return self.backend_record.yc_parameter_sync_inventory_updates
        return False

    def synchronize(self):
        """
        This method generates ART files, and checks local inconsistencies

        """

        self.backend_record.output_for_debug += 'Looking for input files\n'
        files_to_detect = self.env['stock_connector.file'].search([
            ('type', '=', False),
            ('backend_id', '=', self.backend_record.id),
            ('transmit', '=', 'in'),
            ('state', '=', 'ready'),
            ('name', 'ilike', '%.xml'),
        ])
        for file_to_detect in files_to_detect:
            root = etree.XML(str(file_to_detect.content))
            type_node = root.xpath("//*[local-name() = 'ControlReference']"
                                   "/*[local-name() = 'Type']")
            if type_node:
                file_to_detect.type = type_node[0].text.upper()
            else:
                file_to_detect.state = 'error'
                file_to_detect.info = _('Missing ControlReference with Type')
        files_to_import = self.env['stock_connector.file'].search([
            ('type', '!=', False),
            ('backend_id', '=', self.backend_record.id),
            ('transmit', '=', 'in'),
            ('state', '=', 'ready'),
        ])
        for file_to_import in files_to_import:
            if self.file_type_is_enable(file_to_import.type):
                proc = self.processors.get(file_to_import.type)
                if proc:
                    proc(self, file_to_import)

        self.backend_record.output_for_debug += 'Ready for some exports\n'
        # Generating ART files
        products_to_export = self.yc_find_product_for_art()
        if products_to_export and self.file_type_is_enable('art'):
            self.yc_create_art(products_to_export)

    def yc_create_art(self, products_to_export):
        """
        This method can be overriden by specific implementations

        @param products_to_export: Record set of products to export
        """
        ArtProcessor(self).yc_create_art_file(products_to_export)

    def yc_create_control_reference(self, xml_tools, _type, version):
        """
        Creates the basic ControlReference node used among YC

        @param xml_tools: instance with current file data
        @type xml_tools: XmlTools

        @param _type: YC file type
        @type _type: string

        @param version: Version of the current file XSD
        @type version: string

        @return: ControlReference XML element
        @rtype: etree.Element

        """
        create = xml_tools.create_element
        root = create('ControlReference')
        root.append(create('Type', text=_type.upper()))
        root.append(create('Sender', self.yc_get_parameter('sender')))
        root.append(create('Receiver', self.yc_get_parameter('receiver')))
        root.append(create('Timestamp', text=xml_tools.timestamp))
        root.append(create('OperatingMode',
                           self.yc_get_parameter('operating_mode')))
        root.append(create('Version', version))
        return root

    def yc_find_product_for_art(self):
        """
        Searches for products to export

        @return: List of products that can be exported
        @rtype: RecordList of product.product

        """
        return self.env['product.product'].search([('type', '!=', 'service')])

    def yc_get_parameter(self, name):
        """
        Return the value of the related field on the backend record

        @param name: name of the YC parameter
        @type name: string

        @return: value of the field yc_parameter_<name> in the backend record
        @rtype: <field type>

        """
        name = 'yc_parameter_{0}'.format(name)
        return getattr(self.backend_record, name)

    def yc_save_file(self, root, related_ids, tools, _type, transmit='out',
                     suffix=None, cancel_duplicates=False):
        """
        Saves the XML file into Odoo

        @param root: root XML node
        @type root: etree.Element

        @param related_ids: related elements with this file
        @type related_ids: [(model:string, res_id:integer)*]

        @param tools: xml tools used for this file
        @type tools: XmlTools

        @param _type: type of file
        @type _type: string

        @param transmit: is the file to be sent, or just received?
        @type transmit: string

        @param suffix: file suffix

        @param cancel_duplicates: if true, files that match the filename
            (except) timestamp, are cancelled if not send.
        """
        output = tools.xml_to_string(root)
        format_args = {
            'sender': self.yc_get_parameter('sender'),
            'type': tools._type,
            'ts': tools.timestamp,
            'suffix': '',
        }
        if suffix is not None:
            format_args['suffix'] = '_%s' % (suffix or related_ids[0][1])
        elif len(related_ids) == 1 and not cancel_duplicates:
            format_args['suffix'] = '_%s' % related_ids[0][1]
        filename_template = '{sender}_{type}_{ts}{suffix}.xml'
        filename = filename_template.format(**format_args)
        vals = {
            'name': filename,
            'type': _type,
            'child_ids': [(0, 0, {'res_model': x[0], 'res_id': x[1]})
                          for x in related_ids],
            'content': output,
            'backend_id': self.backend_record.id,
            'transmit': transmit,
        }
        if cancel_duplicates:
            format_args['ts'] = '%'
            # fns is the template we try to avoid duplicating
            fns = filename_template.format(**format_args)
            old_files = self.env['stock_connector.file'].search([
                ('name', 'ilike', fns[:1+fns.index('%')]),
                ('name', 'ilike', fns[fns.index('%'):]),
                ('state', '=', 'ready'),
            ])
            if len(old_files) > 0:
                logger.info('%s file overrides old files not send: %s'
                            % (filename, ' '.join(old_files.mapped('name'))))
                old_files.write({'state': 'cancel'})
                vals['child_ids'].extend([
                    (0, 0, {'res_model': 'stock_connector.file',
                            'res_id': x.id})
                    for x in old_files
                ])
        return self.env['stock_connector.file'].create(vals)

    def yc_check_valid_location(self, event):
        if event.res_model != 'stock.picking':
            # No picking, no problem
            return True
        valid_location = self.yc_get_parameter('limit_to_storage_location_id')
        record = event.get_record()

        if valid_location:
            # This location is accepted if appears in one side
            if valid_location == record.location_id:
                return True
            elif valid_location == record.location_dest_id:
                return True
            else:
                return False

        if self.yc_get_parameter('limit_to_binding_locations'):
            # This locations must appear on both sides
            limit_locations = self.backend_record.yc_storage_location_ids \
                .mapped('res_id')
            if record.location_dest_id.id not in limit_locations:
                return False
            elif record.location_id.id not in limit_locations:
                return False
            else:
                return True
        else:
            # Else, everything is OK
            return True

    def yc_create_wab_file(self, event):
        if self.yc_check_valid_location(event):
            return WabProcessor(self).yc_create_wab_file(event)
        else:
            logger.debug('Invalid location')
            return False

    def yc_create_wbl_file(self, event):
        if self.yc_check_valid_location(event):
            return WblProcessor(self).yc_create_wbl_file(event)
        else:
            logger.debug('Invalid location')
            return False

    def notify_new_event(self, new_event):
        super(BackendProcessorExt, self).notify_new_event(new_event)
        if (
            new_event.state == 'ready' and
            new_event.res_model == 'stock.picking' and
            self.yc_get_parameter('autoprocess_picking_events')
        ):
            logger.debug('Processing new_event picking')
            self.yc_create_wab_file(new_event)
