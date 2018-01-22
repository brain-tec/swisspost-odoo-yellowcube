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
from yellowcube_testcase import yellowcube_testcase, subTest
from ..xml_abstract_factory import get_factory
from ..xsd.xml_tools import _XmlTools as xml_tools
import traceback
import logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
from unittest2 import skipIf

UNDER_DEVELOPMENT = False
UNDER_DEVELOPMENT_TEXT = "Test was skipped because of being under development."


@subTest('sale_process', 'base_test')
@subTest('sale_process', 'partial_delivery', skip_test="Not yet defined test", partial_delivery=True)
@subTest('sale_process', 'missing_wab_ret', missing_wab_ret=True)
@subTest('sale_process', 'strange_characters_partner', strange_characters_partner=True)
class test_yc_wab_war(yellowcube_testcase):

    def setUp(self):
        try:
            super(test_yc_wab_war, self).setUp()
            self.test_warehouse.stock_connect_id.write({
                'yc_enable_wab_file': True,
                'yc_enable_war_file': True,
            })
        except Exception as e:
            logger.error(e)
            logger.error(traceback.format_exc(limit=10))
            raise e

    def _save_war(self, war_root, war_file_name):
        cr, uid, ctx = self.cr, self.uid, self.context
        vals = {
            'input': True,
            'content': xml_tools.xml_to_string(war_root, encoding='unicode',
                                               xml_declaration=False),
            'name': war_file_name,
            'stock_connect_id': self.test_warehouse.stock_connect_id.id,
            'type': 'war',
            'warehouse_id': self.test_warehouse.id,
        }
        stock_connect_file_id = \
            self.stock_connect_file.create(cr, uid, vals, context=ctx)
        return stock_connect_file_id

    @skipIf(UNDER_DEVELOPMENT, UNDER_DEVELOPMENT_TEXT)
    def test_ean_wab_with_ean_activated(self):
        """ Tests the generation of a WAB with a product having an EAN,
            and the stock.connect having the EANs activated.
        """
        cr, uid, ctx = self.cr, self.uid, self.context
        ctx['show_errors'] = False

        # Activates the EANs for the stock.connect.files.
        self.test_warehouse.stock_connect_id.write({'yc_ignore_ean': False})

        # We set a barcode for one product of the sale order that is created.
        product_id = self.ref('product.product_product_34')
        self.product_obj.write(cr, uid, product_id,
                               {'ean13': '7611330002881'}, context=ctx)

        # We make sure the sale order has some pickings to send,
        # and we generate the PDFs.
        self._print_sale_pdfs()
        self.assertGreater(len(self.test_sale.picking_ids), 0,
                           'The sale has some pickings')

        # Here we create a WAB file for an order
        wab_factory = get_factory(
            [self.test_warehouse.pool, cr, uid], "wab", context=ctx)
        wab_factory.generate_files([('sale_id', '=', self.test_sale.id)])
        name = '.*_wab_{0}.*OUT.*\.xml'.format(
            wab_factory.xml_tools.export_filename(
                self.test_sale.name, self.context)
        )
        self.assert_(self._yc_files(name), 'A WAB file is created')

        # We check that the WAB has the EAN.
        wab_file_name = self._yc_files(name)[0]
        wab_file_ids = self.stock_connect_file.search(
            cr, uid, [('name', '=', wab_file_name)], context=ctx)
        wab_file = self.stock_connect_file.browse(
            cr, uid, wab_file_ids[0], context=ctx)
        self.assertFalse(wab_file.error)
        self.assertFalse(wab_file.info)
        self.assertTrue('<EAN>7611330002881</EAN>' in wab_file.content)

    @skipIf(UNDER_DEVELOPMENT, UNDER_DEVELOPMENT_TEXT)
    def test_ean_wab_with_ean_deactivated(self):
        """ Tests the generation of a WAB with a product having an EAN,
            and the stock.connect having the EANs deactivated
        """
        cr, uid, ctx = self.cr, self.uid, self.context
        ctx['show_errors'] = False

        # Deactivates the EANs for the stock.connect.files.
        self.test_warehouse.stock_connect_id.write({'yc_ignore_ean': True})

        # We set a barcode for one product of the sale order that is created.
        product_id = self.ref('product.product_product_34')
        self.product_obj.write(cr, uid, product_id,
                               {'ean13': '7611330002881'}, context=ctx)

        # We make sure the sale order has some pickings to send,
        # and we generate the PDFs.
        self._print_sale_pdfs()
        self.assertGreater(len(self.test_sale.picking_ids), 0,
                           'The sale has some pickings')

        # Here we create a WAB file for an order
        wab_factory = get_factory(
            [self.test_warehouse.pool, cr, uid], "wab", context=ctx)
        wab_factory.generate_files([('sale_id', '=', self.test_sale.id)])
        name = '.*_wab_{0}.*OUT.*\.xml'.format(
            wab_factory.xml_tools.export_filename(
                self.test_sale.name, self.context)
        )
        self.assert_(self._yc_files(name), 'A WAB file is created')

        # We check that the WAB has the EAN.
        wab_file_name = self._yc_files(name)[0]
        wab_file_ids = self.stock_connect_file.search(
            cr, uid, [('name', '=', wab_file_name)], context=ctx)
        wab_file = self.stock_connect_file.browse(
            cr, uid, wab_file_ids[0], context=ctx)
        self.assertFalse(wab_file.error)
        self.assertFalse(wab_file.info)
        self.assertTrue('EAN' not in wab_file.content)

    @skipIf(UNDER_DEVELOPMENT, UNDER_DEVELOPMENT_TEXT)
    def test_ean_war_correct_existing_ean(self):
        """ We received a WAR with a correct EAN set for the product, and the
            product already had the EAN set.
        """
        cr, uid, ctx = self.cr, self.uid, self.context
        ctx['show_errors'] = False

        # Activates the EANs for the stock.connect.files.
        self.test_warehouse.stock_connect_id.write({'yc_ignore_ean': False})

        # We set a barcode for one product of the sale order that is created.
        product_id = self.ref('product.product_product_34')
        self.product_obj.write(cr, uid, product_id,
                               {'ean13': '7611330002881'}, context=ctx)

        # We make sure the sale order has some pickings to send,
        # and we generate the PDFs.
        self._print_sale_pdfs()
        self.assertGreater(len(self.test_sale.picking_ids), 0,
                           'The sale has some pickings')

        # Here we create a WAB file for an order
        wab_factory = get_factory(
            [self.test_warehouse.pool, cr, uid], "wab", context=ctx)
        wab_factory.generate_files([('sale_id', '=', self.test_sale.id)])
        name = '.*_wab_{0}.*OUT.*\.xml'.format(
            wab_factory.xml_tools.export_filename(
                self.test_sale.name, self.context)
        )
        self.assert_(self._yc_files(name), 'A WAB file is created')

        # We check that the WAB has the EAN.
        wab_file_name = self._yc_files(name)[0]
        wab_file_ids = self.stock_connect_file.search(
            cr, uid, [('name', '=', wab_file_name)], context=ctx)
        wab_file = self.stock_connect_file.browse(
            cr, uid, wab_file_ids[0], context=ctx)
        self.assertFalse(wab_file.error)
        self.assertFalse(wab_file.info)
        self.assertTrue('<EAN>7611330002881</EAN>' in wab_file.content)

        # Generates the mirror WAR & saves it.
        result_wab_file = self._yc_files(wab_file_name)[0]
        wab_node = self._get_file_node(result_wab_file)
        war_node = self._create_mirror_war_from_wab(
            wab_node, ean_copy_policy='copy')
        self._save_node(war_node, 'war', path='//warr:CustomerOrderNo')
        war_file_name = wab_file_name.replace('wab', 'war')
        war_connect_file_id = self._save_war(war_node, war_file_name)

        # We check that the WAR has the EAN.
        war_connect_file = self.stock_connect_file.browse(
            cr, uid, war_connect_file_id, context=ctx)
        self.assertTrue('<warr:EAN>7611330002881</warr:EAN>'
                        in war_connect_file.content)

        # We import the WAR file without errors.
        self.test_warehouse.stock_connect_id.connection_process_files()
        war_connect_file = self.stock_connect_file.browse(
            cr, uid, war_connect_file_id, context=ctx)
        self.assertFalse(war_connect_file.error)
        self.assertFalse(war_connect_file.info)
        self.assertEqual(war_connect_file.state, 'done')

    @skipIf(UNDER_DEVELOPMENT, UNDER_DEVELOPMENT_TEXT)
    def test_ean_war_correct_nonexisting_ean(self):
        """ We received a WAR with a correct EAN set for the product, but the
            product did not had an EAN set, thus the WAR sets it on the
            product, and no error is set on the stock.connect.file.
        """
        cr, uid, ctx = self.cr, self.uid, self.context
        ctx['show_errors'] = False

        # Activates the EANs for the stock.connect.files.
        self.test_warehouse.stock_connect_id.write({'yc_ignore_ean': False})

        # We check that the product doesn't have an EAN set.
        product = self.browse_ref('product.product_product_34')
        self.assertFalse(product.ean13)

        # We make sure the sale order has some pickings to send,
        # and we generate the PDFs.
        self._print_sale_pdfs()
        self.assertGreater(len(self.test_sale.picking_ids), 0,
                           'The sale has some pickings')

        # Here we create a WAB file for an order
        wab_factory = get_factory(
            [self.test_warehouse.pool, cr, uid], "wab", context=ctx)
        wab_factory.generate_files([('sale_id', '=', self.test_sale.id)])
        name = '.*_wab_{0}.*OUT.*\.xml'.format(
            wab_factory.xml_tools.export_filename(
                self.test_sale.name, self.context)
        )
        self.assert_(self._yc_files(name), 'A WAB file is created')

        # We check that the WAB does not have the EAN.
        wab_file_name = self._yc_files(name)[0]
        wab_file_ids = self.stock_connect_file.search(
            cr, uid, [('name', '=', wab_file_name)], context=ctx)
        wab_file = self.stock_connect_file.browse(
            cr, uid, wab_file_ids[0], context=ctx)
        self.assertFalse(wab_file.error)
        self.assertFalse(wab_file.info)
        self.assertTrue('<EAN>' not in wab_file.content)

        # Generates the mirror WAR & saves it.
        result_wab_file = self._yc_files(wab_file_name)[0]
        wab_node = self._get_file_node(result_wab_file)
        war_node = self._create_mirror_war_from_wab(
            wab_node, ean_copy_policy='new')
        self._save_node(war_node, 'war', path='//warr:CustomerOrderNo')
        war_file_name = wab_file_name.replace('wab', 'war')
        war_connect_file_id = self._save_war(war_node, war_file_name)

        # We check that the WAR has the EAN.
        war_connect_file = self.stock_connect_file.browse(
            cr, uid, war_connect_file_id, context=ctx)
        self.assertTrue('<warr:EAN>7611330002881</warr:EAN>'
                        in war_connect_file.content)

        # We import the WAR file without errors.
        self.test_warehouse.stock_connect_id.connection_process_files()
        war_connect_file = self.stock_connect_file.browse(
            cr, uid, war_connect_file_id, context=ctx)
        self.assertFalse(war_connect_file.error)
        self.assertFalse(war_connect_file.info)
        self.assertEqual(war_connect_file.state, 'done')

        # We check that the product now has the EAN set to that of the WAR.
        product = self.browse_ref('product.product_product_34')
        self.assertEqual(product.ean13, '7611330002881')

    @skipIf(UNDER_DEVELOPMENT, UNDER_DEVELOPMENT_TEXT)
    def test_ean_war_incorrect_ean_ean_deactivated(self):
        """ We received a WAR with an incorrect EAN set for the product,
            but the file is processed correctly since the EANs are
            eactivated.
        """
        cr, uid, ctx = self.cr, self.uid, self.context
        ctx['show_errors'] = False

        # Deactivates the EANs for the stock.connect.files.
        self.test_warehouse.stock_connect_id.write({'yc_ignore_ean': True})

        # We check that the product doesn't have an EAN set.
        product = self.browse_ref('product.product_product_34')
        self.assertFalse(product.ean13)

        # We make sure the sale order has some pickings to send,
        # and we generate the PDFs.
        self._print_sale_pdfs()
        self.assertGreater(len(self.test_sale.picking_ids), 0,
                           'The sale has some pickings')

        # Here we create a WAB file for an order
        wab_factory = get_factory(
            [self.test_warehouse.pool, cr, uid], "wab", context=ctx)
        wab_factory.generate_files([('sale_id', '=', self.test_sale.id)])
        name = '.*_wab_{0}.*OUT.*\.xml'.format(
            wab_factory.xml_tools.export_filename(
                self.test_sale.name, self.context)
        )
        self.assert_(self._yc_files(name), 'A WAB file is created')

        # We check that the WAB does not have the EAN.
        wab_file_name = self._yc_files(name)[0]
        wab_file_ids = self.stock_connect_file.search(
            cr, uid, [('name', '=', wab_file_name)], context=ctx)
        wab_file = self.stock_connect_file.browse(
            cr, uid, wab_file_ids[0], context=ctx)
        self.assertFalse(wab_file.error)
        self.assertFalse(wab_file.info)
        self.assertTrue('<EAN>' not in wab_file.content)

        # Generates the mirror WAR & saves it.
        result_wab_file = self._yc_files(wab_file_name)[0]
        wab_node = self._get_file_node(result_wab_file)
        war_node = self._create_mirror_war_from_wab(
            wab_node, ean_copy_policy='error')
        self._save_node(war_node, 'war', path='//warr:CustomerOrderNo')
        war_file_name = wab_file_name.replace('wab', 'war')
        war_connect_file_id = self._save_war(war_node, war_file_name)

        # We check that the WAR has the EAN.
        war_connect_file = self.stock_connect_file.browse(
            cr, uid, war_connect_file_id, context=ctx)
        self.assertTrue('<warr:EAN>12345</warr:EAN>'
                        in war_connect_file.content)

        # We import the WAR file without errors.
        self.test_warehouse.stock_connect_id.connection_process_files()
        war_connect_file = self.stock_connect_file.browse(
            cr, uid, war_connect_file_id, context=ctx)
        self.assertFalse(war_connect_file.error)
        self.assertFalse(war_connect_file.info)
        self.assertEqual(war_connect_file.state, 'done')

        # We check that the product doesn't have the EAN set.
        product = self.browse_ref('product.product_product_34')
        self.assertFalse(product.ean13)

    @skipIf(UNDER_DEVELOPMENT, UNDER_DEVELOPMENT_TEXT)
    def test_ean_war_incorrect_ean_ean_activated(self):
        """ We received a WAR with an incorrect EAN set for the product,
            so it raises an error since the EANs are activated.
        """
        cr, uid, ctx = self.cr, self.uid, self.context
        ctx['show_errors'] = False

        # Activates the EANs for the stock.connect.files.
        self.test_warehouse.stock_connect_id.write({'yc_ignore_ean': False})

        # We check that the product doesn't have an EAN set.
        product = self.browse_ref('product.product_product_34')
        self.assertFalse(product.ean13)

        # We make sure the sale order has some pickings to send,
        # and we generate the PDFs.
        self._print_sale_pdfs()
        self.assertGreater(len(self.test_sale.picking_ids), 0,
                           'The sale has some pickings')

        # Here we create a WAB file for an order
        wab_factory = get_factory(
            [self.test_warehouse.pool, cr, uid], "wab", context=ctx)
        wab_factory.generate_files([('sale_id', '=', self.test_sale.id)])
        name = '.*_wab_{0}.*OUT.*\.xml'.format(
            wab_factory.xml_tools.export_filename(
                self.test_sale.name, self.context)
        )
        self.assert_(self._yc_files(name), 'A WAB file is created')

        # We check that the WAB does not have the EAN.
        wab_file_name = self._yc_files(name)[0]
        wab_file_ids = self.stock_connect_file.search(
            cr, uid, [('name', '=', wab_file_name)], context=ctx)
        wab_file = self.stock_connect_file.browse(
            cr, uid, wab_file_ids[0], context=ctx)
        self.assertFalse(wab_file.error)
        self.assertFalse(wab_file.info)
        self.assertTrue('<EAN>' not in wab_file.content)

        # Generates the mirror WAR & saves it.
        result_wab_file = self._yc_files(wab_file_name)[0]
        wab_node = self._get_file_node(result_wab_file)
        war_node = self._create_mirror_war_from_wab(
            wab_node, ean_copy_policy='error')
        self._save_node(war_node, 'war', path='//warr:CustomerOrderNo')
        war_file_name = wab_file_name.replace('wab', 'war')
        war_connect_file_id = self._save_war(war_node, war_file_name)

        # We check that the WAR has the EAN.
        war_connect_file = self.stock_connect_file.browse(
            cr, uid, war_connect_file_id, context=ctx)
        self.assertTrue('<warr:EAN>12345</warr:EAN>'
                        in war_connect_file.content)

        # We import the WAR file with errors.
        self.test_warehouse.stock_connect_id.connection_process_files()
        war_connect_file = self.stock_connect_file.browse(
            cr, uid, war_connect_file_id, context=ctx)
        self.assertTrue(war_connect_file.error)
        self.assertEqual(war_connect_file.state, 'draft')

        # We check that the product doesn't have the EAN set.
        product = self.browse_ref('product.product_product_34')
        self.assertFalse(product.ean13)

    @skipIf(UNDER_DEVELOPMENT, UNDER_DEVELOPMENT_TEXT)
    def test_sale_process_tracking_email(self):
        """ This tests the sending of the tracking email to the partner, once
            the WAR is processed.
        """
        cr, uid, context = self.cr, self.uid, self.context

        # Activates the sending on the configuration, and sets the template.
        tracking_email_template_id = \
            self.ref('pc_connect_warehouse_yellowcube.'
                     'email_template_tracking_email')
        self.conf_obj.write(cr, uid, self.configuration.id, {
            'tracking_email_active': True,
            'tracking_email_template_id': tracking_email_template_id,
        }, context=context)

        # Activates the URL template on the carrier that uses the sale order
        # for this test.
        self.carrier_obj.write(cr, uid, self.test_sale.carrier_id.id, {
            'tracking_url_pattern': 'www.post.ch/example/%s/go',
        }, context=context)

        # Generates the WAB & its associated WAR.
        self.sale_process(strange_characters_partner=True)

        # Checks that the picking has the tracking url set.
        pick_out_id = self.pick_obj.search(
            cr, uid, [('sale_id', '=', self.test_sale.id)], context=context)[0]
        pick_out = self.pick_obj.browse(cr, uid, pick_out_id, context=context)
        expected_track_url = 'www.post.ch/example/%s/go' % \
                                self.war_postal_shippment_no
        self.assertEqual(pick_out.carrier_tracking_url, expected_track_url,
                         'The tracking url expected was {0} and I found {1}.'.
                         format(expected_track_url,
                                pick_out.carrier_tracking_url))

        # Checks that there is a new email sent to the partner.
        num_mails = self.mail_obj.search(
            cr, uid, [('type', '=', 'email'),
                      ('model', '=', 'stock.picking.out'),
                      ('res_id', '=', pick_out_id),
                      ('body_html', 'ilike', '%' + expected_track_url + '%'),
                      ], count=True, context=context)
        self.assertEqual(num_mails, 1, 'I expected to found one email but '
                                       'found {0} instead.'.format(num_mails))

        # Tests that there is a message in the chatter of the picking.
        num_messages = self.message_obj.search(
            cr, uid, [('type', '=', 'notification'),
                      ('model', '=', 'stock.picking'),
                      ('res_id', '=', pick_out_id),
                      ('body', 'ilike', '%' + expected_track_url + '%'),
                      ], count=True, context=context)
        self.assertEqual(num_messages, 1, 'I expected to found one message in '
                                          'the chatter but found {0} instead.'.
                         format(num_mails))

    def sale_process(self, missing_wab_ret=False, partial_delivery=False, strange_characters_partner=False):
        """
        This test, tests the workflow followed after a sale is closed
        """
        self._print_sale_pdfs()
        cr, uid, ctx = self.cr, self.uid, self.context
        ctx['show_errors'] = False
        wab_factory = get_factory([self.test_warehouse.pool, cr, uid], "wab", context=ctx)

        if strange_characters_partner:
            partner = self.test_sale.partner_id
            partner.write({'street': 'strange 0ñ1ç2ü3ñ4~5--ème étage'})
        # First we check some pre-conditions
        self.assertGreater(len(self.test_sale.picking_ids), 0, 'The sale has some pickings')

        # Here we create a WAB file for an order
        wab_factory.generate_files([('sale_id', '=', self.test_sale.id)])
        pick_out_id = self.pick_obj.search(cr, uid, [('sale_id', '=', self.test_sale.id)], context=ctx)[0]
        pick_out = self.pick_obj.browse(cr, uid, pick_out_id, ctx)
        self.assertNotIn(pick_out.state, ['done'], 'The stock.picking is not closed, until everything is delivered')
        name = '.*_wab_{0}.*OUT.*\.xml'.format(
            wab_factory.xml_tools.export_filename(
                self.test_sale.name, self.context)
        )
        self.assert_(self._yc_files(name), 'A WAB file is created')
        # Now we check some fields
        result_wab_file = self._yc_files(name)[0]
        wab_node = self._get_file_node(result_wab_file)
        self._save_node(wab_node, 'wab', path='//CustomerOrderNo')
        self.assertEqual(len([x for x in self.test_sale.order_line if x.product_id.type != 'service']), len(xml_tools.nspath(wab_node, '//Position')), 'A position for each item in the SO')
        # Here we create the response WAR file, accepting everything
        war_node = self._create_mirror_war_from_wab(wab_node)
        self._save_node(war_node, 'war', path='//warr:CustomerOrderNo')
        war_factory = get_factory([self.test_warehouse.pool, cr, uid], "war", context=ctx)
        war_factory.import_file(xml_tools.xml_to_string(war_node))
        # Now we check the stock.picking state
        pick_out = self.pick_obj.browse(cr, uid, pick_out_id, ctx)
        self.assertIn(pick_out.state, ['done'], 'The stock.picking is closed, once everything is delivered')

        # Now for the return of the goods
        if not missing_wab_ret:
            # Here we create a return for the order
            logger.debug("Creating WAB-RET")
            ctx['active_id'] = pick_out.id
            pick_ret_id = self.pick_ret_obj.create(cr, uid, {'yellowcube_return': True, 'yellowcube_return_reason': 'R03'}, context=ctx)
            create_return_dict = self.pick_ret_obj.create_returns(cr, uid,
                                                                  [pick_ret_id],
                                                                  context=ctx)
            pick_in_id = eval(create_return_dict['domain'])[0][2][0]
            pick_in = self.pick_obj.browse(cr, uid, pick_in_id, ctx)
            pick_in.write({'yellowcube_return_reason': 'R01'})
            pick_in.action_confirm()
            self.assertNotIn(pick_in.state, ['done'], 'The stock.picking is not closed, until everything is delivered')
            wab_factory.generate_files([('id', '=', pick_in_id)])
            name = '.*_wab_{0}.*IN.*\.xml'.format(
                wab_factory.xml_tools.export_filename(
                    self.test_sale.name, self.context)
            )
            self.assert_(self._yc_files(name), 'A WAB file is created')
            # Now we check some fields
            result_wab_file = self._yc_files(name)[0]
            wab_node = self._get_file_node(result_wab_file)
            self.assertEqual(len([x for x in self.test_sale.order_line if x.product_id.type != 'service']), len(xml_tools.nspath(wab_node, '//Position')), 'A position for each item in the SO')

        # Here we create the response WAR file, accepting everything
        war_node = self._create_mirror_war_from_wab(wab_node, returngoods=True)
        self._save_node(war_node, 'war', path='//warr:CustomerOrderNo')
        if not missing_wab_ret:
            war_factory.import_file(xml_tools.xml_to_string(war_node))
            # Now we check the stock.picking state
            pick_in = self.pick_obj.browse(cr, uid, pick_in_id, ctx)
            self.assertIn(pick_in.state, ['done'], 'The stock.picking is closed, once everything is delivered')
        else:
            with self.assertRaises(Warning):
                war_factory.import_file(xml_tools.xml_to_string(war_node))

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
