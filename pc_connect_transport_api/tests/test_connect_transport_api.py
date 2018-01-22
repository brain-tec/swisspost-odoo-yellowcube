# -*- coding: utf-8 -*-
#
#    Copyright (c) 2017 brain-tec AG (http://www.braintec-group.com)
#    All Right Reserved
#
#    See LICENSE file for full licensing details.
from .common import APITestCase
from base64 import b64encode
from unittest2 import skipIf

UNDER_DEVELOPMENT = False
UNDER_DEVELOPMENT_TEXT = "Test was skipped because of being under development."


class test_connect_transport_api(APITestCase):

    @skipIf(UNDER_DEVELOPMENT, UNDER_DEVELOPMENT_TEXT)
    def test_connect_transport_api_create_stock_connect_file(self):
        stock_connect_file_count = len(
            self.registry('stock.connect.file').search(self.cr, 1, []))
        test_wbl = b64encode('''
            <?xml version='1.0' encoding='UTF-8'?>
            <WBL xmlns:art="https://service.swisspost.ch/apache/yellowcube/YellowCube_ART_REQUEST_Artikelstamm.xsd" xmlns:bar="https://service.swisspost.ch/apache/yellowcube/YellowCube_BAR_RESPONSE_ArticleList.xsd" xmlns:bar_req="https://service.swisspost.ch/apache/yellowcube/YellowCube_BAR_REQUEST_ArticleList.xsd" xmlns:bur="https://service.swisspost.ch/apache/yellowcube/YellowCube_BUR_RESPONSE_GoodsMovements.xsd" xmlns:bur_req="https://service.swisspost.ch/apache/yellowcube/YellowCube_BUR_REQUEST_GoodsMovements.xsd" xmlns:gen="https://service.swisspost.ch/apache/yellowcube/YellowCube_GEN_RESPONSE_General.xsd" xmlns:gen_req="https://service.swisspost.ch/apache/yellowcube/YellowCube_GEN_STATUS_REQUEST_General.xsd" xmlns:soap="http://schemas.xmlsoap.org/wsdl/soap/" xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" xmlns:soapsec="http://schemas.xmlsoap.org/soap/security/2000-12" xmlns:w3_xmldsig="http://www.w3.org/2000/09/xmldsig#" xmlns:w3_xmlexcc14n="http://www.w3.org/2001/10/xml-exc-c14n#" xmlns:wab="https://service.swisspost.ch/apache/yellowcube/YellowCube_WAB_REQUEST_Warenausgangsbestellung.xsd" xmlns:war_req="https://service.swisspost.ch/apache/yellowcube/YellowCube_WAR_REQUEST_GoodsIssueReply.xsd" xmlns:warr="https://service.swisspost.ch/apache/yellowcube/YellowCube_WAR_RESPONSE_GoodsIssueReply.xsd" xmlns:wba="https://service.swisspost.ch/apache/yellowcube/YellowCube_WBA_RESPONSE_GoodsReceiptReply.xsd" xmlns:wba_req="https://service.swisspost.ch/apache/yellowcube/YellowCube_WBA_REQUEST_GoodsReceiptReply.xsd" xmlns:wbl="https://service.swisspost.ch/apache/yellowcube/YellowCube_WBL_REQUEST_SupplierOrders.xsd" xmlns:wsse="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-wssecurity-secext-1.0.xsd">
              <ControlReference>
                <Type>WBL</Type>
                <Sender>Sender</Sender>
                <Receiver>YELLOWCUBE</Receiver>
                <Timestamp>20170511121217</Timestamp>
                <OperatingMode>T</OperatingMode>
                <Version>1.0</Version>
              </ControlReference>
              <SupplierOrder>
                <SupplierOrderHeader>
                  <DepositorNo>0000014723</DepositorNo>
                  <Plant>Y048</Plant>
                  <SupplierNo>0000200020</SupplierNo>
                  <!--res.partner#5-->
                  <SupplierName1>Post CH AG</SupplierName1>
                  <SupplierStreet>Wankdorfstrasse 4</SupplierStreet>
                  <SupplierCountryCode>CH</SupplierCountryCode>
                  <SupplierZIPCode>3030</SupplierZIPCode>
                  <SupplierCity>Bern</SupplierCity>
                  <SupplierOrderNo>PO00084IN00041</SupplierOrderNo>
                  <SupplierOrderDate>20170511</SupplierOrderDate>
                  <SupplierOrderDeliveryDate>20170511</SupplierOrderDeliveryDate>
                </SupplierOrderHeader>
                <SupplierOrderPositions>
                  <Position>
                    <PosNo>1</PosNo>
                    <ArticleNo>35995</ArticleNo>
                    <Quantity>50.0</Quantity>
                    <QuantityISO>PCE</QuantityISO>
                    <PosText>Tempete Occitane 75cl</PosText>
                  </Position>
                  <Position>
                    <PosNo>2</PosNo>
                    <ArticleNo>35870</ArticleNo>
                    <Quantity>50.0</Quantity>
                    <QuantityISO>PCE</QuantityISO>
                    <PosText>Haushaltsleiter 4-stufig</PosText>
                  </Position>
                  <Position>
                    <PosNo>3</PosNo>
                    <ArticleNo>77795</ArticleNo>
                    <Quantity>50.0</Quantity>
                    <QuantityISO>PCE</QuantityISO>
                    <PosText>Smoker Texas Ranger L</PosText>
                  </Position>
                </SupplierOrderPositions>
              </SupplierOrder>
              <!--Model: stock.picking ID: 82 Name: IN/00041-->
            </WBL>''')

        # This test is using only the internal call, we are not testing the
        # complete flow with http request. The reason is that the Odoo server
        # seems not to start properly with start_openerp(), the '/web/session/get_session_info' request
        # works, i.e. returns a new session id, but the following '/web/session/authenticate' request
        # stucks until timed out. Testing the same with a Odoo server instance
        # and the request works as expected, so for the time being we will not
        # investigate the problem.
        result = self._api_call(
            'create_stock_connect_file',
            self.connect_transport_api.name,
            {
                'connect_transport_profile': 'WBL profile',
                'filename': 'test',
                'content': test_wbl,
            },
        )
        self.assertEqual('success', result['status'])
        #  we should have now 1 file in stock.connect.file
        self.assertEquals(stock_connect_file_count + 1,
            len(self.registry('stock.connect.file').search(self.cr, 1, [])))

        #  and this file id should match the one we received as result
        self.assertEquals(1,
            len(self.registry('stock.connect.file').search(self.cr, 1, [
                ('id', '=', result['id'])])))

    @skipIf(UNDER_DEVELOPMENT, UNDER_DEVELOPMENT_TEXT)
    def test_connect_transport_api_get_connect_file_status(self):
        stock_connect_file_count = len(self.registry('stock.connect.file').search(self.cr, 1, []))
        test_wbl1 = b64encode('''
            <?xml version='1.0' encoding='UTF-8'?>
            <WBL xmlns:art="https://service.swisspost.ch/apache/yellowcube/YellowCube_ART_REQUEST_Artikelstamm.xsd" xmlns:bar="https://service.swisspost.ch/apache/yellowcube/YellowCube_BAR_RESPONSE_ArticleList.xsd" xmlns:bar_req="https://service.swisspost.ch/apache/yellowcube/YellowCube_BAR_REQUEST_ArticleList.xsd" xmlns:bur="https://service.swisspost.ch/apache/yellowcube/YellowCube_BUR_RESPONSE_GoodsMovements.xsd" xmlns:bur_req="https://service.swisspost.ch/apache/yellowcube/YellowCube_BUR_REQUEST_GoodsMovements.xsd" xmlns:gen="https://service.swisspost.ch/apache/yellowcube/YellowCube_GEN_RESPONSE_General.xsd" xmlns:gen_req="https://service.swisspost.ch/apache/yellowcube/YellowCube_GEN_STATUS_REQUEST_General.xsd" xmlns:soap="http://schemas.xmlsoap.org/wsdl/soap/" xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" xmlns:soapsec="http://schemas.xmlsoap.org/soap/security/2000-12" xmlns:w3_xmldsig="http://www.w3.org/2000/09/xmldsig#" xmlns:w3_xmlexcc14n="http://www.w3.org/2001/10/xml-exc-c14n#" xmlns:wab="https://service.swisspost.ch/apache/yellowcube/YellowCube_WAB_REQUEST_Warenausgangsbestellung.xsd" xmlns:war_req="https://service.swisspost.ch/apache/yellowcube/YellowCube_WAR_REQUEST_GoodsIssueReply.xsd" xmlns:warr="https://service.swisspost.ch/apache/yellowcube/YellowCube_WAR_RESPONSE_GoodsIssueReply.xsd" xmlns:wba="https://service.swisspost.ch/apache/yellowcube/YellowCube_WBA_RESPONSE_GoodsReceiptReply.xsd" xmlns:wba_req="https://service.swisspost.ch/apache/yellowcube/YellowCube_WBA_REQUEST_GoodsReceiptReply.xsd" xmlns:wbl="https://service.swisspost.ch/apache/yellowcube/YellowCube_WBL_REQUEST_SupplierOrders.xsd" xmlns:wsse="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-wssecurity-secext-1.0.xsd">
              <ControlReference>
                <Type>WBL</Type>
                <Sender>Sender</Sender>
                <Receiver>YELLOWCUBE</Receiver>
                <Timestamp>20170511121217</Timestamp>
                <OperatingMode>T</OperatingMode>
                <Version>1.0</Version>
              </ControlReference>
              <SupplierOrder>
                <SupplierOrderHeader>
                  <DepositorNo>0000014723</DepositorNo>
                  <Plant>Y048</Plant>
                  <SupplierNo>0000200020</SupplierNo>
                  <!--res.partner#5-->
                  <SupplierName1>Post CH AG</SupplierName1>
                  <SupplierStreet>Wankdorfstrasse 4</SupplierStreet>
                  <SupplierCountryCode>CH</SupplierCountryCode>
                  <SupplierZIPCode>3030</SupplierZIPCode>
                  <SupplierCity>Bern</SupplierCity>
                  <SupplierOrderNo>PO00084IN00041</SupplierOrderNo>
                  <SupplierOrderDate>20170511</SupplierOrderDate>
                  <SupplierOrderDeliveryDate>20170511</SupplierOrderDeliveryDate>
                </SupplierOrderHeader>
                <SupplierOrderPositions>
                  <Position>
                    <PosNo>1</PosNo>
                    <ArticleNo>35995</ArticleNo>
                    <Quantity>50.0</Quantity>
                    <QuantityISO>PCE</QuantityISO>
                    <PosText>Tempete Occitane 75cl</PosText>
                  </Position>
                  <Position>
                    <PosNo>2</PosNo>
                    <ArticleNo>35870</ArticleNo>
                    <Quantity>50.0</Quantity>
                    <QuantityISO>PCE</QuantityISO>
                    <PosText>Haushaltsleiter 4-stufig</PosText>
                  </Position>
                  <Position>
                    <PosNo>3</PosNo>
                    <ArticleNo>77795</ArticleNo>
                    <Quantity>50.0</Quantity>
                    <QuantityISO>PCE</QuantityISO>
                    <PosText>Smoker Texas Ranger L</PosText>
                  </Position>
                </SupplierOrderPositions>
              </SupplierOrder>
              <!--Model: stock.picking ID: 82 Name: IN/00041-->
            </WBL>''')

        test_wbl2 = b64encode('''
            <?xml version='1.0' encoding='UTF-8'?>
            <WBL xmlns:art="https://service.swisspost.ch/apache/yellowcube/YellowCube_ART_REQUEST_Artikelstamm.xsd" xmlns:bar="https://service.swisspost.ch/apache/yellowcube/YellowCube_BAR_RESPONSE_ArticleList.xsd" xmlns:bar_req="https://service.swisspost.ch/apache/yellowcube/YellowCube_BAR_REQUEST_ArticleList.xsd" xmlns:bur="https://service.swisspost.ch/apache/yellowcube/YellowCube_BUR_RESPONSE_GoodsMovements.xsd" xmlns:bur_req="https://service.swisspost.ch/apache/yellowcube/YellowCube_BUR_REQUEST_GoodsMovements.xsd" xmlns:gen="https://service.swisspost.ch/apache/yellowcube/YellowCube_GEN_RESPONSE_General.xsd" xmlns:gen_req="https://service.swisspost.ch/apache/yellowcube/YellowCube_GEN_STATUS_REQUEST_General.xsd" xmlns:soap="http://schemas.xmlsoap.org/wsdl/soap/" xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" xmlns:soapsec="http://schemas.xmlsoap.org/soap/security/2000-12" xmlns:w3_xmldsig="http://www.w3.org/2000/09/xmldsig#" xmlns:w3_xmlexcc14n="http://www.w3.org/2001/10/xml-exc-c14n#" xmlns:wab="https://service.swisspost.ch/apache/yellowcube/YellowCube_WAB_REQUEST_Warenausgangsbestellung.xsd" xmlns:war_req="https://service.swisspost.ch/apache/yellowcube/YellowCube_WAR_REQUEST_GoodsIssueReply.xsd" xmlns:warr="https://service.swisspost.ch/apache/yellowcube/YellowCube_WAR_RESPONSE_GoodsIssueReply.xsd" xmlns:wba="https://service.swisspost.ch/apache/yellowcube/YellowCube_WBA_RESPONSE_GoodsReceiptReply.xsd" xmlns:wba_req="https://service.swisspost.ch/apache/yellowcube/YellowCube_WBA_REQUEST_GoodsReceiptReply.xsd" xmlns:wbl="https://service.swisspost.ch/apache/yellowcube/YellowCube_WBL_REQUEST_SupplierOrders.xsd" xmlns:wsse="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-wssecurity-secext-1.0.xsd">
              <ControlReference>
                <Type>WBL</Type>
                <Sender>Sender</Sender>
                <Receiver>YELLOWCUBE</Receiver>
                <Timestamp>20170511121217</Timestamp>
                <OperatingMode>T</OperatingMode>
                <Version>1.0</Version>
              </ControlReference>
              <SupplierOrder>
                <SupplierOrderHeader>
                  <DepositorNo>0000014723</DepositorNo>
                  <Plant>Y048</Plant>
                  <SupplierNo>0000200020</SupplierNo>
                  <!--res.partner#5-->
                  <SupplierName1>Post CH AG</SupplierName1>
                  <SupplierStreet>Wankdorfstrasse 4</SupplierStreet>
                  <SupplierCountryCode>CH</SupplierCountryCode>
                  <SupplierZIPCode>3030</SupplierZIPCode>
                  <SupplierCity>Bern</SupplierCity>
                  <SupplierOrderNo>PO00084IN00041</SupplierOrderNo>
                  <SupplierOrderDate>20170511</SupplierOrderDate>
                  <SupplierOrderDeliveryDate>20170511</SupplierOrderDeliveryDate>
                </SupplierOrderHeader>
                <SupplierOrderPositions>
                  <Position>
                    <PosNo>1</PosNo>
                    <ArticleNo>35995</ArticleNo>
                    <Quantity>50.0</Quantity>
                    <QuantityISO>PCE</QuantityISO>
                    <PosText>Tempete Occitane 75cl</PosText>
                  </Position>
                  <Position>
                    <PosNo>2</PosNo>
                    <ArticleNo>35870</ArticleNo>
                    <Quantity>50.0</Quantity>
                    <QuantityISO>PCE</QuantityISO>
                    <PosText>Haushaltsleiter 4-stufig</PosText>
                  </Position>
                  <Position>
                    <PosNo>3</PosNo>
                    <ArticleNo>77795</ArticleNo>
                    <Quantity>50.0</Quantity>
                    <QuantityISO>PCE</QuantityISO>
                    <PosText>Smoker Texas Ranger L</PosText>
                  </Position>
                </SupplierOrderPositions>
              </SupplierOrder>
              <!--Model: stock.picking ID: 82 Name: IN/00041-->
            </WBL>''')

        result = self._api_call(
            'create_stock_connect_file',
            self.connect_transport_api.name,
            {
                'connect_transport_profile': 'WBL profile',
                'filename': 'test1',
                'content': test_wbl1,
            },
        )
        self.assertEqual('success', result['status'])
        #  we should have now 1 file in stock.connect.file
        self.assertEquals(stock_connect_file_count + 1,
            len(self.registry('stock.connect.file').search(self.cr, 1, [])))

        result = self._api_call(
            'create_stock_connect_file',
            self.connect_transport_api.name,
            {
                'connect_transport_profile': 'WBL profile',
                'filename': 'test2',
                'content': test_wbl2,
            },
        )
        self.assertEqual('success', result['status'])
        #  we should have now 2 file in stock.connect.file
        self.assertEquals(stock_connect_file_count + 2,
                          len(self.registry('stock.connect.file').search(
                              self.cr, 1, [])))
        id_to_search_for = result['id']

        result = self._api_call(
            'get_connect_file_status',
            self.connect_transport_api.name,
            {
                'connect_transport_profile': 'WBL profile',
                'file_ids': [id_to_search_for],
                'file_refs': ['test1', 'ddd'],
            },
        )

        self.assertEqual('ok', result['status'])
        self.assertEquals(2, len(result['connect_files']))

        print result
