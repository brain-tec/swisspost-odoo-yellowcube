# -*- coding: utf-8 -*-
##############################################################################
#
#    Copyright (c) 2016 brain-tec AG (http://www.braintec-group.com)
#    All Right Reserved
#
#    See LICENSE file for full licensing details.
##############################################################################
from openerp import models, api, fields
from openerp.addons.stock_connector_yellowcube.tests\
    import test_wabwar_file, test_wblwba_file, test_bur_file, test_bar_file
import logging
import datetime
_logger = logging.getLogger(__name__)


class StockConnectorTransportExt(models.Model):
    _inherit = 'stock_connector.transport'

    ycmockup_received_files = fields.Many2many(
        'stock_connector.file',
        'stock_connector_yellowcube_mockup_in_files',
        string='Received Files',
        readonly=True)

    ycmockup_ready_to_send_files = fields.Many2many(
        'stock_connector.file',
        'stock_connector_yellowcube_mockup_out_files',
        string='Files-to-send')

    ycmockup_warehouse = fields.Many2one('stock.warehouse')

    ycmockup_backend_ids = fields.One2many('stock_connector.backend',
                                           'transport_id')

    ycmockup_bur_location = fields.Char()
    ycmockup_bur_dest_location = fields.Char()
    ycmockup_bur_qty_to_set = fields.Float(default=10)

    @api.model
    def select_versions(self):
        """
        Version key is the model name associated with the transport

        :return: list of version that can be used
        """
        ret = super(StockConnectorTransportExt, self).select_versions()
        ret.append(('stock_connector_yellowcube_mockup.transport',
                    'YellowCube Mockup'))
        return ret

    @api.multi
    def ycmockup_create_files(self):
        self.ensure_one()
        wab_files = []
        wbl_files = []
        for received_file in self.ycmockup_received_files:
            _type = received_file.type.lower()
            if _type == 'wab':
                wab_files.append(received_file)
            elif _type == 'wbl':
                wbl_files.append(received_file)

        new_output_files = []
        # WAB into WAR
        for wab_file in wab_files:
            _logger.debug(wab_file.name)
            wab2war = test_wabwar_file.TestWabWarFile()
            wab2war.backend = wab_file.backend_id
            try:
                war_content = wab2war.create_war_from_wab(wab_file.content)
            except:
                war_content = None
            if war_content:
                new_output_files += [(0, None, {
                    'type': False,
                    'content': war_content,
                    'name': wab_file.name.replace('wab', 'war'),
                })]
                self.ycmockup_received_files = [(3, wab_file.id, None)]
        # WBL into WBA
        for wbl_file in wbl_files:
            _logger.debug(wbl_file.name)
            wbl2wba = test_wblwba_file.TestWblWbaFile()
            wbl2wba.backend = wbl_file.backend_id
            try:
                wba_content = wbl2wba.create_wba_from_wbl(wbl_file.content)
            except:
                wba_content = None
            if wba_content:
                new_output_files += [(0, None, {
                    'type': False,
                    'content': wba_content,
                    'name': wbl_file.name.replace('wbl', 'wba'),
                })]
                self.ycmockup_received_files = [(3, wbl_file.id, None)]
        # Set new output files
        self.ycmockup_ready_to_send_files = new_output_files
        return True

    @api.multi
    def ycmockup_create_bur_file(self):
        return self.ycmockup_create_burbar_file('bur')

    @api.multi
    def ycmockup_create_bar_file(self):
        return self.ycmockup_create_burbar_file('bar')

    @api.multi
    def ycmockup_create_burbar_file(self, file_type):
        self.ensure_one()
        self.ycmockup_backend_ids.ensure_one()
        if self.ycmockup_ready_to_send_files.filtered(
                lambda x: file_type in x.name
        ):
            return True
        products_on_art = []
        for received_file in self.ycmockup_received_files.filtered(
            lambda x: x.type.lower() == 'art'
        ):
            products_on_art.extend(received_file.child_ids.filtered(
                lambda x:
                x.res_model == 'product.product' and
                x.res_id not in products_on_art
            ).mapped('res_id'))
        if not products_on_art:
            return True
        _logger.debug('Products on the warehouse: %s' % products_on_art)

        locations_backend = self.ycmockup_backend_ids.binding_ids.filtered(
            lambda x: x.res_model == 'stock.location')

        if not locations_backend:
            return True
        _logger.debug(locations_backend)

        # Set new output files
        query = """
        SELECT
            product_id,
            lot_id,
            location_id,
            SUM (qty)
        FROM
            stock_quant
        WHERE
            location_id IN %s
        AND product_id IN %s
        GROUP BY
            product_id,
            lot_id,
            location_id
        """
        self.env.cr.execute(query,
                            (tuple(locations_backend.mapped('res_id')),
                             tuple(products_on_art)))
        parameters = []
        product_obj = self.env['product.product']
        lot_obj = self.env['stock.production.lot']
        sql_results = self.env.cr.dictfetchall()
        products_on_moves = []
        for result in sql_results:
            if result['product_id'] not in products_on_moves:
                products_on_moves.append(result['product_id'])
        for missing in [x
                        for x in products_on_art
                        if x not in products_on_moves]:
            sql_results.append({
                'product_id': missing,
                'lot_id': False,
                'sum': 0,
                'location_id': locations_backend.filtered(
                    lambda x: x.name == self.ycmockup_bur_dest_location
                ).res_id,
            })

        for result in sql_results:
            location = locations_backend.filtered(
                lambda x: x.res_id == result['location_id']).binding
            actual_qty = result['sum']
            values = {
                'product': product_obj.browse(result['product_id']),
                'qty': 0 if file_type == 'bur' else actual_qty,
                'location': location,
                'dest_location': location,
                'create_binding': False,
                'lot': False,
            }
            if location == self.ycmockup_bur_dest_location and\
                    actual_qty < self.ycmockup_bur_qty_to_set and\
                    file_type == 'bur':
                values['qty'] = self.ycmockup_bur_qty_to_set - actual_qty
                values['location'] = self.ycmockup_bur_location
            if result['lot_id']:
                values['lot'] = lot_obj.browse(result['lot_id']).name
            parameters.append(values)
        _logger.debug(parameters)
        if file_type == 'bur':
            bur_test = test_bur_file.TestBurFile()
            bur_test.backend = self.ycmockup_backend_ids
            file_content = bur_test.create_bur_file(parameters)
        elif file_type == 'bar':
            bar_test = test_bar_file.TestBarFile()
            bar_test.backend = self.ycmockup_backend_ids
            file_content = bar_test.create_bar_file(parameters)
        else:
            return True
        self.ycmockup_ready_to_send_files = [
            (0, None, {
                'type': False,
                'content': file_content,
                'name': '{0}_{1}_{2}.xml'.format(
                    self.ycmockup_backend_ids.yc_parameter_sender,
                    file_type,
                    datetime.datetime.now().strftime('%Y%m%d%H%M%S')
                ),
            })
        ]
        return True
