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
from openerp.osv import osv, fields
from openerp.tools.translate import _
from openerp.osv import orm
from openerp.exceptions import Warning as OdooWarning
from openerp import api
from openerp.release import version_info
V8 = True if version_info[0] > 7 else False
import logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


_EXCEPTION_CONSTRAINT_YC = """
YellowCube connections must:
1) Only run over a unique warehouse.
2) Have a selected connection transport
3) Fill in 'YC Depositor No', 'YC PlantID', 'YC Sender', 'YC SupplierNo', 'YC PartnerNo', 'YC OperatingMode'
4) Have a positive value for the ART check over outdated products.
"""

_EXCEPTION_CONSTRAINT_YC_LIFECYCLE = """
In order to use the product's lifecycle, please install the module 'pc_product_lifecycle'.
"""

_EXCEPTION_CONSTRAINT_YC_PARTNERTYPE_ON_WAB = '''
If the invoice address is marked to be shown on the WAB, then its associated <PartnerType> must be indicated also.
'''

_YC_WAB_INVOICE_SEND_MODE_SELECTION = [
    ('pdf_wab', 'Send in WAB as PDF'),
    ('pdf_docout', 'Send only to Doc-out as PDF'),
]

FILE_TYPES = [('wab','WAB'),
              ('war','WAR'),
              ('wba','WBA'),
              ('wbl','WBL'),
              ('bar','BAR'),
              ('bur','BUR'),
              ('art','ART'),
              ('art_multifile', 'ART Multifile'),
              ('art_ondemand', 'ART On Demand'),
             ]

class stock_connect_ext(osv.Model):
    _inherit = 'stock.connect'

    def _constraint_lifecycle_can_be_activated_only_if_module_is_installed(self, cr, uid, ids):
        ''' If we have set that we want the product's life-cycle
            to be activated, then we check that the module
            which implements the product's life-cycle is installed,
            and if it's not, then we show a pop-up urging to
            install it.
        '''
        for connect in self.browse(cr, uid, ids):
            if connect.yc_enable_product_lifecycle is True:
                module_obj = self.pool.get('ir.module.module')
                if not module_obj.search(cr, uid, [('name', '=', 'pc_product_lifecycle'),
                                                   ('state', '=', 'installed'),
                                                   ]):
                    return False
        return True

    def _constraint_partner_type_tag_for_wab(self, cr, uid, ids):
        ''' Checks fhat if the WAB is going to show the invoicing address, the <PartnerType> content
            for that kind of addresses is provided.
        '''
        for this in self.browse(cr, uid, ids):
            if this.yc_wab_add_invoicing_address and (not this.yc_wab_partner_type_for_invoicing_address):
                return False
        return True

    @api.cr_uid_ids
    def _constraints_for_yellowcube(self, cr, uid, ids):
        error = False
        for this in self.browse(cr, uid, ids):
            if this.type == 'yellowcube':
                if len(this.warehouse_ids) > 1:
                    error = True
                    logger.debug('warehouse_ids > 1')
                if not this.connect_transport_id:
                    error = True
                    logger.debug('not connect_transport_id')
                if this.yc_hours_between_art_files <= 0:
                    error = True
                    logger.debug('yc_hours_between_art_files <= 0')
                if (not this.yc_depositor_no) or \
                   (not this.yc_plant_id) or \
                   (not this.yc_sender) or \
                   (not this.yc_supplier_no) or \
                   (not this.yc_partner_no) or \
                   (not this.yc_operating_mode):
                    logger.debug('missing values')
                    error = True
                if error:
                    logger.debug('Error on constraints stock.connect#{0}'.format(this.id))
        if V8 and error:
            raise Exception(_EXCEPTION_CONSTRAINT_YC)
        else:
            return not error

    def _get_default_lang(self, cr, uid, context):
        return 'de_DE'  # self.pool.get('res.users').browse(cr, uid, uid, context).lang

    def get_event_codes_to_ignore(self, cr, uid, ids, context=None):
        """ Returns the list of event_code to ignore AND mark as ignored.
        """
        if context is None:
            context = {}
        if type(ids) is not list:
            ids = [ids]

        this = self.browse(cr, uid, ids[0], context=context)
        if this.type in ['yellowcube', 'yellowcubesoap']:
            ret = [
                'new_picking_state_draft',
                'new_picking_state_auto',
                'new_picking_state_confirmed',
                'new_picking_state_done',
                'new_picking_state_cancel',
                'warehouse_connection_set',
            ]

        else:
            ret = super(stock_connect_ext, self).get_event_codes_to_ignore(
                cr, uid, ids, context=context)

        return ret

    _columns = {
        'yc_language_setting': fields.selection(
            [('fixed', 'Fixed per connection'),
             ('shipment', 'According to shipment address'),
             ], string='YC XML Language Setting'),
        'yc_language_default': fields.char('YC XML Language Default'),
        # TODO: mark as default=True whatever code ready for execution
        'yc_enable_art_file': fields.boolean("Enable ART file", default=True),
        'yc_enable_art_multifile': fields.boolean("Enable ART multifile", default=False),
        'yc_enable_art_ondemand': fields.boolean("Enable ART creation on demand", default=False),
        'yc_enable_bar_file': fields.boolean("Enable BAR file", default=False),
        'yc_enable_bur_file': fields.boolean("Enable BUR file", default=False),
        'yc_enable_wab_file': fields.boolean("Enable WAB file", default=False),
        'yc_enable_war_file': fields.boolean("Enable WAR file", default=False),
        'yc_enable_wbl_file': fields.boolean("Enable WBL file", default=False),
        'yc_enable_wba_file': fields.boolean("Enable WBA file", default=False),
        'yc_ignore_ean': fields.boolean(
            'Ignore EAN in ART/WAB/WAR/WBA/BAR/BUR',
            help="If it is activated, in ART we still transmit the "
                 "current EAN, in WAB we do NOT send the EAN "
                 "(it's an optional field), and when the WAR, WBA, BUR and "
                 "BAR are read, we do NOT check if it's the correct one from "
                 "the product, but we trust only in default_code and "
                 "yc_YCArticleNo"),

        'yc_wab_add_invoicing_address': fields.boolean('Include the Invoicing Address on WAB?', default=False),
        'yc_wab_partner_type_for_shipping_address': fields.char('Value of <PartnerType> for the shipping address on WAB', required=True, default="WE"),
        'yc_wab_partner_type_for_invoicing_address': fields.char('Value of <PartnerType> for the invoicing address on WAB'),

        'yc_wab_shortdescription_mapping': fields.selection([('name', 'Name'),
                                                             ('price', 'Price'),
                                                             ], string='Content of tag <ShortDescription> on WAB',
                                                            help='Allows to overload the content of the tag <ShortDescription> on a WAB. '
                                                                 'If Name is selected, then it prints the standard content for this tag. '
                                                                 'If Price is selected, then it prints the price of the order line instead'),
        'yc_wab_pickingmessage_mapping': fields.selection(
            [('not_used', 'Not Used'),
             ('carrier_tracking_ref', 'Carrier Tracking Ref'),
             ], string='Content of tag <PickingMessage>',
            help='Allows to overload the content of the tag <PickingMessage> '
                 'on a WAB.\n'
                 '- Not Used: It does not use this tag.\n'
                 '- Carrier Tracking Ref: Prints the reference by the carrier '
                 'used for the picking, truncated to 132 characters.\n'),
        'yc_wab_invoice_send_mode': fields.selection(_YC_WAB_INVOICE_SEND_MODE_SELECTION, string='How to Send the Invoices?',
                                                     help='Indicates how to send the invoices, either on the WAB (as PDF) '
                                                          'or as PDF to the doc-out folder.'),

        'yc_war12_dummy_lot_name': fields.char('WAR1 & WAR2 dummy lot name'),

        'yc_wba_invoice_on_import': fields.boolean('Create invoice for Incoming Shipment'),
        'yc_wba_confirm': fields.boolean('Allow WBA to confirm pickings?'),
        'yc_wba_confirm_time': fields.float(
            string='Time to wait to confirm picking in (in hours)',
            help='Safety time to wait for delayed WBA to confirm an incoming '
                 'picking after the last end of delivery has been received. '
                 'Only applies to incomplete pickings without over-fulfilled '
                 'lines.'),
        'yc_wba_auto_cancel_backorder': fields.boolean(
            string='Allow to cancel back orders?',
            help='If this option is set, back orders that did not get any '
                 'quantities during the configured time are automatically '
                 'cancelled. A cancelled back order will automatically '
                 'create the WBA-0 if a forwarding connection for '
                 'outgoing WBA is configured.'),
        'yc_wba_cancel_time': fields.float(
            'Time to wait to cancel back order (in hours)',
            help='Time to wait after a back-order is automatically '
                 'cancelled after it has been created. Only applies '
                 'to back orders where no quantity done has been '
                 'added by any WBA.'),
        'yc_wba_outgoing_redirect': fields.many2one(
            'stock.connect',
            'Connection for the redirection of the outgoing WBA',
            help='The outgoing WBAs: Summary WBA and WBA-0, will be generated '
                 'only if this field is set, and the generated WBA will be '
                 'copied to the connection indicated in this field.'),
        'yc_wba_respect_eod_flag': fields.boolean(
            "Respect EndOfDelivery Flag",
            help="Set this flag for YellowCube, clear it for LogoS. If this "
                 "flag is set, the EndOfDelivery flag in the WBA is expected "
                 "to be set on the last WBA:GoodsReceiptDetail for that "
                 "position (YellowCube), otherwise the flag is expected "
                 "not to be used deterministically "),

        'yc_hours_between_art_files': fields.integer('Hours to wait before creating a new ART file, if a pending ART exists.'),
        'yc_depositor_no': fields.char('YC DepositorNo'),
        'yc_plant_id': fields.char('YC PlantID'),
        'yc_sender': fields.char('YC Sender'),
        'yc_receiver': fields.char('YC Receiver', default='YELLOWCUBE'),
        'yc_supplier_no': fields.char('YC SupplierNo'),
        'yc_partner_no': fields.char('YC PartnerNo'),
        'yc_file_date_sufix': fields.char('Filename suffix', required=False),
        'yc_operating_mode': fields.selection([('P', 'Production'),
                                               ('D', 'Development'),
                                               ('T', 'Test')], string='YC OperatingMode', help='Value of the tag OperatingMode in YellowCube files.'),
        'yc_missing_bar_days_due': fields.integer('Days a product or lot may be outdated from a BAR file', help='Negative or zero, ignore check.', required=False),

        'yc_enable_product_lifecycle': fields.boolean("Enable Product's Life-cycle?",
                                                      help="If checked, then the module pc_product_lifecycle must be installed."),
    }

    _defaults = {
        'yc_file_date_sufix': '%Y%m%d_%H%M%S',
        'yc_hours_between_art_files': 24,
        'yc_operating_mode': 'T',
        'yc_missing_bar_days_due': 0,
        'yc_language_setting': 'fixed',
        'yc_language_default': _get_default_lang,
        'yc_enable_product_lifecycle': False,
        'yc_wab_add_invoicing_address': False,
        'yc_wab_partner_type_for_shipping_address': 'WE',
        'yc_wab_shortdescription_mapping': 'name',
        'yc_wab_pickingmessage_mapping': 'not_used',
        'yc_wab_invoice_send_mode': 'pdf_wab',
        'yc_wba_invoice_on_import': False,
        'yc_wba_confirm': True,
        'yc_wba_confirm_time': 4,
        'yc_wba_auto_cancel_backorder': False,
        'yc_ignore_ean': False,
        'yc_wba_respect_eod_flag': True
    }

    _constraints = [
        (_constraints_for_yellowcube, _EXCEPTION_CONSTRAINT_YC, ['warehouse_ids', 'connect_transport_id', 'type']),
        (_constraint_lifecycle_can_be_activated_only_if_module_is_installed, _EXCEPTION_CONSTRAINT_YC_LIFECYCLE, ['yc_enable_product_lifecycle']),
        (_constraint_partner_type_tag_for_wab, _EXCEPTION_CONSTRAINT_YC_PARTNERTYPE_ON_WAB, ['yc_wab_add_invoicing_address', 'yc_wab_partner_type_for_invoicing_address']),
    ]

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
