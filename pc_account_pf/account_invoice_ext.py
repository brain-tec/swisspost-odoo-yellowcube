# b-*- encoding: utf-8 -*-
##############################################################################
#
#    Copyright (c) 2017 brain-tec AG (http://www.braintec-group.com)
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

from openerp.osv import orm, osv, fields
from openerp.addons.pc_generics import generics
from openerp.addons.delivery_carrier_label_postlogistics.postlogistics.\
    web_service import PostlogisticsWebService


@generics.has_mako_header()
class account_invoice_ext(osv.Model):
    _inherit = "account.invoice"

    def invoice_print(self, cr, uid, ids, context=None):
        if context is None:
            context = {}

        datas = {'ids': ids,
                 'model': 'account.invoice',
                 'form': self.read(cr, uid, ids[0], context=context)
                 }
        return {'type': 'ir.actions.report.xml',
                'report_name': 'invoice.report',
                'datas': datas,
                'nodestroy': True,
                'context': context,
                }

    def action_generate_carrier_label(self, cr, uid, ids, context=None):
        return self.generate_labels(cr, uid, ids, context=context)

    def generate_labels(self, cr, uid, ids, context=None):
        """ This is very much inspired from the method generate_labels()
            from the module base_delivery_carrier_label, but was adapted
            for account.invoice instead of stock.picking.something.
        """
        if context is None:
            context = {}
        if not isinstance(ids, list):
            ids = [ids]

        shipping_label_obj = self.pool.get('shipping.label')

        for inv in self.browse(cr, uid, ids, context=context):
            shipping_labels = inv.generate_postlogistics_label_for_invoice()
            for label in shipping_labels:
                data = {
                    'name': label['name'],
                    'res_id': inv.id,
                    'res_model': 'account.invoice',
                    'datas': label['file'],
                    'file_type': label['file_type'],
                }
                if label.get('tracking_id'):
                    data['tracking_id'] = label['tracking_id']

                # We remove the default_type set by the account.invoice since
                # it's set to be out_invoice and that collides with the
                # value that expects the ir.attachment.
                ctx = context.copy()
                if 'default_type' in ctx:
                    del ctx['default_type']

                shipping_label_obj.create(cr, uid, data, context=ctx)

        return True

    def generate_postlogistics_label_for_invoice(self, cr, uid, ids, context=None):
        """ Generates Post-logistics labels for invoices.

            This is inspired by the method _generate_postlogistics_label()
            of the module delivery_carrier_label_postlogistics.
        """
        if context is None:
            context = {}
        if not isinstance(ids, list):
            ids = [ids]
        assert len(ids) == 1, 'ids must be a 1-element list.'

        user_obj = self.pool.get('res.users')

        invoice = self.browse(cr, uid, ids[0], context=context)

        user = user_obj.browse(cr, uid, uid, context=context)
        company = user.company_id

        webservice_class = PostlogisticsWebService
        web_service = webservice_class(company)

        trackings = []

        # Here comes the hack: the method generate_label() from
        # PostlogisticsWebService expects a picking, because it
        # 1) was intended for pickings,
        # 2) thus it expects the object named 'picking' to have certain
        #    fields that are only on pickings.
        # So what we do here, to avoid re-defining too many methods, is to
        # make the invoice have those required fields, so that the label
        # can be generated. Of course, this works because generate_label()
        # doesn't check the type of the object.
        # So: in the original call, the first parameter is not 'invoice',
        # but 'picking'.
        res = web_service.generate_label(invoice, trackings, user_lang=user.lang)

        if 'errors' in res:
            raise orm.except_orm('Error', '\n'.join(res['errors']))

        label = res['value'][0]
        tracking_number = label['tracking_number']
        invoice.write({'carrier_tracking_ref': tracking_number})

        return [{'tracking_id': False,
                 'file': label['binary'],
                 'file_type': label['file_type'],
                 'name': tracking_number + '.' + label['file_type'],
                 }]

    def get_barcode_for_report(self, cr, uid, ids, context=None):
        """ Gets a barcode for the invoice, and returns its base64 encoding
            along with its type, in a tuple (base64, file_type)
        """
        data = self.generate_postlogistics_label_for_invoice(
            cr, uid, ids, context=context)
        return data[0]['file'], data[0]['file_type']

    _columns = {
        # Fields added to be able to generate the barcode label for invoices
        # instead of pickings.
        'carrier_tracking_ref': fields.char(
            'Carrier Tracking Ref', size=256),
        'option_ids': fields.many2many(
            'delivery.carrier.option',
            string='Delivery Carrier Options'),
    }

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
