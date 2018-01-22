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
from openerp import api
from openerp.addons.pc_connect_master.utilities.pdf import concatenate_pdfs
from tempfile import mkstemp
import os
import base64
import logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


RETURN_REASON_CODES = [
    ('R01', 'Order posted wrongly'),
    ('R02', 'Better price found'),
    ('R03', 'No reason'),
    ('R04', 'Delivery not in due time'),
    ('R05', 'Delivery packaging and article damaged'),
    ('R06', 'Company shipped wrong product'),
    ('R07', 'Faulty / not working properly'),
    ('R08', 'Company shipped more articles than ordered'),
    ('R09', 'Product did not meet customer\'s expectations'),
    ('R10', 'Wrong size delivered (too small)'),
    ('R11', 'Wrong size delivered (too big)'),
    ('R12', 'Product did not match description'),
    ('R13', 'Wrong order: style/size/colour'),
    ('R14', 'Product did not match description on website'),
]

CUSTOMER_ORDER_NUMBER_XSD_LIMIT = 35


class stock_picking_ext(osv.Model):
    _inherit = 'stock.picking'

    def create(self, cr, uid, values, context=None):
        picking_id = super(stock_picking_ext, self).create(
            cr, uid, values, context=context)

        if 'sale_id' in values or 'carrier_id' in values:
            self.set_mandatory_additional_shipping_codes(cr, uid, picking_id,
                                                         context=context)

        return picking_id

    def write(self, cr, uid, ids, values, context=None):
        ret = super(stock_picking_ext, self).write(
            cr, uid, ids, values, context=None)

        if 'sale_id' in values or 'carrier_id' in values:
            self.set_mandatory_additional_shipping_codes(cr, uid, ids,
                                                         context=context)

        return ret

    def set_mandatory_additional_shipping_codes(self, cr, uid, ids,
                                                context=None):
        """ Sets the mandatory additional shipping codes on the picking
            depending on its carrier. The code which updates the services
            depending on the products of the stock.moves are in that model.
        """
        if not isinstance(ids, list):
            ids = [ids]
        if context is None:
            context = {}

        sep = ';'

        for picking in self.browse(cr, uid, ids, context=context):
            mandatory_additional_options = set()

            # Stores the already existing mandatory additional services,
            # just in case the user had modified them manually.
            if picking.yc_mandatory_additional_shipping:
                original_mandatory_options = set(
                    picking.yc_mandatory_additional_shipping.split(sep))
                mandatory_additional_options.update(original_mandatory_options)
            else:
                original_mandatory_options = set()

            # Adds the mandatory additional services by the picking's carrier.
            carrier = picking.carrier_id
            if carrier and carrier.yc_additional_shipping:
                mandatory_additional_options.update(
                    set(carrier.yc_additional_shipping.split(sep)))

            # We update the list of mandatory additional shipping options
            # but only if it changed.
            if mandatory_additional_options and \
                    original_mandatory_options != mandatory_additional_options:
                self.write(cr, uid, picking.id, {
                    'yc_mandatory_additional_shipping': sep.join(
                        mandatory_additional_options),
                }, context=context)

        return True

    def store_tracking_link(self, cr, uid, ids, context=None):
        """ Stores the tracking link into the picking, formed by
            taking the tracking url pattern defined in the carrier, and
            the carrier's tracking reference stored in the picking.
        """
        if context is None:
            context = {}
        if type(ids) is not list:
            ids = [ids]

        for picking in self.browse(cr, uid, ids, context=context):
            tracking_url_pattern = picking.carrier_id.tracking_url_pattern
            tracking_ref = picking.carrier_tracking_ref
            if tracking_url_pattern and tracking_ref:
                tracking_url = tracking_url_pattern % tracking_ref
                picking.write({'carrier_tracking_url': tracking_url})

        return True

    def send_tracking_email_to_client(self, cr, uid, ids, context=None):
        """ Creates and equeues a confirmation email to the client
            after receiving the WAR, only if the picking has set the
            tracking link to be sent.
        """
        if context is None:
            context = {}
        if type(ids) is not list:
            ids = [ids]

        email_template_obj = self.pool.get('email.template')
        mail_obj = self.pool.get('mail.mail')
        project_issue_obj = self.pool.get('project.issue')

        conf_data = self.pool.get('configuration.data').\
            get(cr, uid, [], context=context)

        errors = []
        if conf_data.tracking_email_active:
            tracking_email_template = conf_data.tracking_email_template_id
            if tracking_email_template:
                picking_ids = self.search(cr, uid, [
                    ('id', 'in', ids),
                    ('carrier_tracking_url', '!=', None),
                ], context=context)

                for picking in self.browse(cr, uid, picking_ids,
                                           context=context):
                    try:
                        cr.execute('SAVEPOINT send_tracking_email')

                        # Prepares the email for the sending.
                        values = email_template_obj.\
                            generate_email(cr, uid, tracking_email_template.id,
                                           picking.id, context=context)
                        mail_obj.create(cr, uid, values, context=context)

                        # Copies the email's body to the chatter.
                        self.message_post(
                            cr, uid, [picking.id],
                            body='Tracking email was sent to the partner' +
                                 values['body_html'],
                            context=context)

                    except Exception as e:
                        cr.execute('ROLLBACK TO SAVEPOINT send_tracking_email')

                        errors.append(
                            ([picking.id],
                             _("The following errors happened while sending "
                               "the tracking email for the picking with "
                               "ID={0}: {1}").format(picking.id, str(e))))

                    else:
                        cr.execute('RELEASE SAVEPOINT send_tracking_email')

            else:
                errors.append((ids,_("There was no email template defined "
                                     "for the tracking email.")))

        if errors:
            for picking_ids, error_message in errors:
                for picking_id in picking_ids:
                    issue_subject = \
                        _('Errors when sending the tracking email.')
                    issue_msg = \
                        _('The tracking email for the picking with IDs={0} '
                          'could not be sent because of the following '
                          'error: {1}').format(picking_id, error_message)

                    project_issue_obj.create_issue(
                        cr, uid, 'stock.picking.out', picking_id, issue_msg,
                        issue_subject=issue_subject,
                        tags=['stock.picking.out', 'wab'],
                        create=True, reopen=True, context=context)

                    logger.warning(issue_msg)

        return True

    def get_filename_for_wab(self, cr, uid, ids, context=None):
        ''' Gets the filename for the picking file that is attached in the WAB,
            in the format the WAB expects.
        '''
        if context is None:
            raise Warning('context is missing when calling method get_filename_for_wab over stock.picking, and is required in this case.')
        if type(ids) is not list:
            ids = [ids]

        picking = self.browse(cr, uid, ids[0], context=context)
        if picking.type == 'in':
            raise Warning('get_filename_for_wab can only be called over stock.picking.out.')

        order_name = context['yc_customer_order_no']
        depositor_id = context['yc_sender']

        doc_type = 'LS'

        order_date = picking.sale_id.date_order
        order_date = order_date.split(' ')[0]  # Just in case date has attached the hh:mm:ss
        yyyy, mm, dd = order_date.split('-')
        yymmdd = '{yy}{mm}{dd}'.format(yy=yyyy[-2:], mm=mm, dd=dd)

        order_number = order_name

        file_name = '{depositor_id}_{doc_type}{order_number}_{yymmdd}.pdf'.format(depositor_id=depositor_id,
                                                                                  doc_type=doc_type,
                                                                                  order_number=order_number,
                                                                                  yymmdd=yymmdd)
        return file_name

    def get_attachment_wab(self, cr, uid, ids, context=None):
        ''' Returns a dictionary of the type
            <KEY=output_filename, VALUE=original_path_of_attachment>
            with as many keys as invoice-related attachments need to
            be exported on the WAB.

            The attachment for the WAB may be the picking OR a concatenation of
            the picking and the barcode report (if existing). Since we want both
            modules (this one and the one which generates the barcode) to be
            completely independent, we need to check if the module which generates
            the barcode is installed, and if that is the case then we consider
            adding the barcodes also to the attachment.

            IDs must be an integer, or a list of just one ID (otherwise
            just the first element is taken into account).
        '''
        if context is None:
            context = {}
        if type(ids) is not list:
            ids = [ids]

        result = {}

        ir_attachment_obj = self.pool.get('ir.attachment')
        ir_config_parameter_obj = self.pool.get('ir.config_parameter')
        ir_module_obj = self.pool.get('ir.module.module')

        attachments_location = ir_config_parameter_obj.get_param(cr, uid, 'ir_attachment.location')

        stock_picking_out = self.browse(cr, uid, ids[0], context=context)

        # Caches the attachments for the picking.
        att_ids = ir_attachment_obj.search(cr, uid, [('res_id', '=', stock_picking_out.id),
                                                     ('res_model', '=', 'stock.picking.out'),
                                                     ], context=context)

        # Gets the attachment for the delivery slip, since we must attach it for sure.
        att_picking_ids = ir_attachment_obj.search(cr, uid, [('id', 'in', att_ids),
                                                             ('document_type', '=', 'picking_out_report'),
                                                             ], context=context)
        if len(att_picking_ids) != 1:
            if context.get('yc_min_number_attachments') != 0:
                raise Warning(_('A bad number of picking reports was found ({0}) '
                                'on picking with ID={1}, while just one was expected').format(len(att_picking_ids),
                                                                                              stock_picking_out.id))
            return result

        # Determines if we have to attach also the picking report.
        att_barcode_ids = []
        if ir_module_obj.search(cr, uid, [('name', '=', 'pc_delivery_carrier_label_postlogistics'),
                                          ('state', '=', 'installed'),
                                          ], limit=1, count=True, context=context) \
           and (not stock_picking_out.uses_bulkfreight):
            att_barcode_ids = ir_attachment_obj.search(cr, uid, [('id', 'in', att_ids),
                                                                 ('document_type', '=', 'barcode_out_report'),
                                                                 ], context=context)
            if len(att_barcode_ids) > 1:
                raise Warning(_('A bad number of barcode reports was found ({0}) '
                                'for picking with ID={1}, while one or none was expected').format(len(att_picking_ids),
                                                                                                  stock_picking_out.id))

        # We compute the name of the output filename to be indicated on the WAB.
        output_filename = stock_picking_out.get_filename_for_wab()

        # Determines the ID of the attachment to send with the WAB. It will be only the ID of the picking
        # if no barcode needs to be attached, BUT it will be *a new* attachment, created ad-hoc, with is the
        # concatenation of the picking and the barcode.
        if not att_barcode_ids:
            attachment_to_send_id = att_picking_ids[0]  # Just the (only) delivery slip found.
        else:
            attachment_to_send_id = stock_picking_out._get_attachment_id_for_picking_and_barcode_concatenated(att_picking_ids[0], att_barcode_ids[0], extension)

        att = ir_attachment_obj.browse(cr, uid, attachment_to_send_id, context=context)
        result[output_filename] = ir_attachment_obj._full_path(cr, uid, attachments_location, att.store_fname)

        return result

    def _get_attachment_id_for_picking_and_barcode_concatenated(self, cr, uid, ids, att_picking_id, att_barcode_id, context=None):
        ''' Returns the ID of the attachment which consist of the concatenation of the picking and barcode attachments
            the ID of which is received as arguments. If the attachment doesn't exist, it creates it; otherwise just
            returns it.
        '''
        if context is None:
            context = {}
        if type(ids) is not list:
            ids = [ids]

        ir_attachment_obj = self.pool.get('ir.attachment')
        ir_config_parameter_obj = self.pool.get('ir.config_parameter')

        stock_picking_out = self.browse(cr, uid, ids[0], context=context)

        if 'output_filename' not in context:
            output_filename = stock_picking_out.get_filename_for_wab()
        else:
            output_filename = context['output_filename']
        attachments_location = ir_config_parameter_obj.get_param(cr, uid, 'ir_attachment.location')

        # First we check if we already have the attachment. If we don't have it, we create it.
        att_ids = ir_attachment_obj.search(cr, uid, [('res_id', '=', stock_picking_out.id),
                                                     ('res_model', '=', 'stock.picking.out'),
                                                     ('name', '=', output_filename),
                                                     ], limit=1, context=context)
        if att_ids:
            attachment_id = att_ids[0]
        else:
            try:
                # First, we create a temporary PDF file having the content of the concatenation.
                fd, tmp_path = mkstemp(prefix='delivery_slip_and_barcode_', dir="/tmp")
                paths_of_files_to_concatenate = []
                for att_to_concatenate in ir_attachment_obj.browse(cr, uid, [att_picking_id, att_barcode_id], context=context):
                    att_to_concatenate_full_path = ir_attachment_obj._full_path(cr, uid, attachments_location, att_to_concatenate.store_fname)
                    paths_of_files_to_concatenate.append(att_to_concatenate_full_path)
                concatenate_pdfs(tmp_path, paths_of_files_to_concatenate)

                # Then we create an attachment with the content of that file.
                with open(tmp_path, "rb") as f:
                    attachment_content_base64 = base64.b64encode(f.read())
                values_create_att = {'name': output_filename,
                                     'datas': attachment_content_base64,
                                     'datas_fname': output_filename,
                                     'res_model': 'stock.picking.out',
                                     'res_id': stock_picking_out.id,
                                     'type': 'binary',
                                     'description': _('Attachment for picking with ID={0}. It is the concatenation of '
                                                      'the attachments of the picking (attach. id={1}) '
                                                      'and the barcode report (attach. ID={2}'.format(stock_picking_out.id,
                                                                                                      att_picking_id,
                                                                                                      att_barcode_id)),
                                     }
                attachment_id = ir_attachment_obj.create(cr, uid, values_create_att, context=context)

            finally:
                if fd:
                    os.close(fd)
                if tmp_path:
                    os.remove(tmp_path)

        return attachment_id

    @api.cr_uid_ids_context
    def check_is_valid_return(self, cr, uid, ids, context=None):
        """
        If:
            type is stock.picking.in
            state different from draft or cancel
            return_origin_order XOR return_reason
                (one set, the other unset)
        Then:
            Fail
        """
        for pick in self.browse(cr, uid, ids, context):
            if pick.state in ['draft', 'cancel']:
                continue
            if pick.type in ['in', 'incoming'] and pick.sale_id and not pick.yellowcube_return_reason:
                return False
        return True

    def copy(self, cr, uid, id_, default=None, context=None):
        if default is None:
            default = {}
        if context is None:
            context = {}
        for k in ['yellowcube_return_reason', 'yellowcube_return_origin_order', 'yellowcube_return_automate']:
            if k in context:
                default[k] = context[k]

        return super(stock_picking_ext, self).copy(cr, uid, id_, default=default, context=context)

    @api.cr_uid_ids_context
    def get_customer_order_no(self, cr, uid, ids, field=None, arg=None, context=None):
        if context is None:
            context = {}

        config = self.pool.get('configuration.data').get(cr, uid, [], context=context)

        ret = {}
        for delivery in self.browse(cr, uid, ids, context=context):
            # make sure we have a default in any case
            ret[delivery.id] = delivery.id

            if config.yc_customer_order_no_mode == 'id':
                ret[delivery.id] = delivery.id
                
            elif config.yc_customer_order_no_mode == 'extref':
                if delivery.type == 'out':
                    ret[delivery.id] = '{0}-{1}'.format(delivery.sale_id.name.split('-')[-1], 
                                                       delivery.name[-5:]).replace('/', '')
                elif delivery.type == 'in':
                    # do not append picking name for incoming pickings, as we
                    # never send incoming backorders & the WBL SupplierOrderNo
                    # is limited to max-lenght 20 characters in the WBL XSD
                    ret[delivery.id] = '{0}'.format(delivery.purchase_id.name.split('-')[-1])   

            elif config.yc_customer_order_no_mode == 'name':
                if delivery.type == 'out':
                    ret[delivery.id] = '{0}-{1}'.format(delivery.sale_id.name or 
                                                       delivery.purchase_id.name, 
                                                       delivery.name).replace('/', '')
                elif delivery.type == 'in':
                    # do not append picking name for incoming pickings, as we
                    # never send incoming backorders & the WBL SupplierOrderNo
                    # is limited to max-lenght 20 characters in the WBL XSD
                    ret[delivery.id] = '{0}'.format(delivery.purchase_id.name or delivery.sale_id.name)

            elif config.yc_customer_order_no_mode == 'order':
                if delivery.sale_id:
                    ret[delivery.id] = delivery.sale_id.name
                elif delivery.purchase_id:
                    ret[delivery.id] = delivery.purchase_id.name
                else:
                    # default to id
                    ret[delivery.id] = delivery.id

            else:
                # default to id
                ret[delivery.id] = delivery.id

            if (config.yc_customer_order_no_mode != 'id') and \
               ret[delivery.id] and \
               len(ret[delivery.id]) > CUSTOMER_ORDER_NUMBER_XSD_LIMIT:
                ret[delivery.id] = '{0}.id{1}'.format(delivery.type, delivery.id)
        return ret

    @api.cr_uid_ids_context
    def get_yc_filename_postfix(self, cr, uid, ids, context=None):
        """
        What to append to the YC file when refering to this object
        """
        delivery = self.browse(cr, uid, ids[0], context=context)
        _type = delivery.type
        ret = None
        if _type in ['out', 'outgoing']:
            ret = '{0}{1}'.format(delivery.sale_id and delivery.sale_id.name or delivery.purchase_id.name, delivery.name).replace('/', '').replace('-', '')
        elif _type in ['in', 'incoming']:
            ret = '{0}{1}'.format(delivery.purchase_id and delivery.purchase_id.name or delivery.sale_id.name, delivery.name).replace('/', '').replace('-', '')
        return ret.replace('\\', '').replace(' ', '')

    @api.cr_uid_ids_context
    def equal_addresses_ship_invoice(self, cr, uid, ids, context=None):
        ''' Returns whether the shipping and invoicing addresses are the same for a given sale order.
        '''
        this = self.browse(cr, uid, ids[0], context)
        equal_addresses = True
        sale_order = this.sale_id
        if sale_order:
            equal_addresses = (sale_order.partner_invoice_id.id == sale_order.partner_shipping_id.id)

        return bool(equal_addresses)

    @api.cr_uid_ids_context
    def payment_method_has_epayment(self, cr, uid, ids, context=None):
        ''' Returns whether the payment method has epayment.
        '''
        this = self.browse(cr, uid, ids[0], context)
        has_epayment = False
        sale_order = this.sale_id
        if sale_order:
            has_epayment = sale_order.payment_method_id.epayment

        return bool(has_epayment)

    @api.cr_uid_ids_context
    def wrapper_do_partial(self, cr, uid, ids, partial_datas, context=None):
        ''' This is just a wrapper around the method do_partial, which allows for an easy
            way of determining when a backorder was created for a given picking, depending
            on its return type.

            It returns a tuple of two elements (backorder_id, new_picking_id), containing
            the IDs of the pickings created for the backorder (which in V7 has the same ID
            than the original picking) and the ID for the newly created picking (the one with
            the products that could be actually delivered).
                If no backorder is created, both IDs will be the same.

            This is called over just one ID. If ids is a list, then it only takes its first element.
        '''
        if context is None:
            context = {}
        if type(ids) is not list:
            ids = [ids]

        picking_id = ids[0]
        res = super(stock_picking_ext, self).do_partial(cr, uid, [picking_id], partial_datas, context=context)
        backorder_id = res.keys()[0]
        new_picking_id = res[backorder_id]['delivered_picking']

        # If both IDs are the same, that means we haven't created a back-order.
        if backorder_id == new_picking_id:
            backorder_id = False

        return (backorder_id, new_picking_id)

    _columns = {
        'yellowcube_delivery_no': fields.char('YCDeliveryNo', size=10, help='Tag <YCDeliveryNo> of the WAR file.'),
        'yellowcube_delivery_date': fields.date('YCDeliveryDate', help='Tag <YCDeliveryDate> of the WAR file.'),
        'yellowcube_customer_order_no': fields.function(get_customer_order_no,
                                                        string="YC CustomerOrderNo",
                                                        type='text',
                                                        store={
                                                            'stock.picking': (lambda self, cr, uid, ids, context=None: ids, ['sale_id', 'purchase_id'], 10),
                                                            'stock.picking.in': (lambda self, cr, uid, ids, context=None: ids, ['sale_id', 'purchase_id'], 10),
                                                            'stock.picking.out': (lambda self, cr, uid, ids, context=None: ids, ['sale_id', 'purchase_id'], 10),
                                                        },
                                                        readonly=True),
        'yellowcube_return_origin_order': fields.many2one('sale.order', 'Original order'),
        'yellowcube_return_automate': fields.boolean('Automate return-claim on confirm'),
        'yellowcube_return_reason': fields.selection(RETURN_REASON_CODES, 'Return reason (if and only if return)', help='Return reason in accordance with the Return-Reason Code List'),
        'yellowcube_exported_wab': fields.boolean('Has been exported into a wab file?'),
        'carrier_tracking_url': fields.char(
            'Carrier Tracking URL',
            help='URL for the tracking webpage provided '
                 'by the delivery carrier.'),
        'yellowcube_last_confirmation_timestamp': fields.datetime(
            string='Last confirmation file from YC',
            help='Last time a confirmation file (WBA/WAR) was processed for '
                 'this picking.'),
    }

    _default = {
        'yellowcube_return_automate': False,
        'yellowcube_exported_wab': False,
    }

    _constraints = [
        (check_is_valid_return, 'If associated to a sale order, it must have a return reason and a sale.order', ['yellowcube_return_reason', 'state'])
    ]


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
