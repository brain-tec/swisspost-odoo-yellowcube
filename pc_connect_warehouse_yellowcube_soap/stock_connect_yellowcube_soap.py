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
from openerp.tools import DEFAULT_SERVER_DATETIME_FORMAT, DEFAULT_SERVER_DATE_FORMAT
from openerp.addons.pc_connect_master.utilities.others import format_exception
from datetime import timedelta, datetime
from SOAPpy import SOAPProxy
from openerp.addons.pc_connect_warehouse_yellowcube.xsd.xml_tools import _XmlTools
from lxml import etree
import copy
import pytz
import subprocess
import os
import HTMLParser
import logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


_ERR_MSG = _('Error sending {0} file:{1}\n{2}')


class stock_connect_yellowcube_soap(osv.Model):
    _name = "stock.connect.yellowcubesoap"
    _inherit = 'stock.connect.yellowcube'

    def files_needing_ack(self, cr, uid, ids, context=None):
        """ Returns a set of file-types needing an acknowledgement (i.e. ACK)
            from the server.
        """
        stock_connect = self.__this(cr, uid, ids, context=context)

        if stock_connect.type == 'yellowcubesoap':
            file_types = set(['art', 'wab', 'wbl'])

        else:
            file_types = \
                super(stock_connect_yellowcube_soap, self).files_needing_ack(
                    cr, uid, ids, context=context)
        return file_types

    def __this(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        if isinstance(ids, list):
            ids = ids[0]
        return self.pool.get('stock.connect').browse(cr, uid, ids, context)

    def _sign_xml(self, out_data, keyfile, certfile):
        # out_data = wsse_signing.sign(out_data, keyfile, certfile)
        cmd = [
            "/usr/bin/php5",
            "{0}/sign.php".format('/'.join(os.path.realpath(__file__).split('/')[:-1]))
        ]
        php_script = subprocess.Popen(cmd,
                                      stdin=subprocess.PIPE,
                                      stdout=subprocess.PIPE)
        _input = '{0}\n{1}\n{2}\n\n\n'.format(keyfile.strip(),
                                              certfile.strip(),
                                              out_data)
        #return_code = php_script.wait()
        #if return_code != 0:
        #    raise Exception("Error while signing soap petition: {0}".format(return_code))
        result, _ = php_script.communicate(_input)
        return result

    def _send_item(self, cr, uid, ids, server, xml_node, action, schema_name=None, context=None):
        """
        @param server: connection proxy to outside server
        @param xml_node: lxml xml element to send
        @param action: SOAP action to query
        @param schema_name: schema to validate the node against before sending, if set.
        @return: xml_return_message, error_message
        """
        try:
            tools = context.get('xml_tools', _XmlTools)
            if schema_name:
                r = tools.validate_xml(schema_name, xml_node, print_error=bool(server.config.debug))
                if r:
                    return None, r
            else:
                r = None
            xml_kargs = {
                'pretty_print': True,
                'xml_declaration': False
            }
            this = self.__this(cr, uid, ids, context)
            root = tools.create_root('{{{soapenv}}}Envelope')
            ns = tools.schema_namespaces['soapenv']
            # 0 soapenv:Header
            xml_header = tools.create_element('Header', ns=ns)
            body = tools.create_element('Body', ns=ns)
            body.append(xml_node)
            root.append(xml_header)
            root.append(body)
            out_data = tools.xml_to_string(root, **xml_kargs)
            parser = etree.XMLParser(remove_blank_text=True)
            out_data = tools.xml_to_string(tools.open_xml(out_data, repair=False, parser=parser), pretty_print=True)

            if this.yc_soapsec_key_path:
                out_data = self._sign_xml(out_data,
                                          keyfile=this.yc_soapsec_key_path, 
                                          certfile=this.yc_soapsec_cert_path)

            with _soap_debug(this, action) as soap_debug:
                soap_debug.write('SENDING', out_data)
                r, namespace = server.transport.call(server.proxy,
                                                     out_data,
                                                     server.namespace,
                                                     action,
                                                     encoding=server.encoding,
                                                     http_proxy=server.http_proxy,
                                                     config=server.config,
                                                     timeout=server.timeout)
                soap_debug.write('RECEIVING', r)
            response = etree.fromstring(r)
            body = response.iterchildren('{*}Body').next()
            fault = body.xpath('soapenv:Fault', namespaces=tools.schema_namespaces)
            if fault:
                return fault[0], tools.xml_to_string(fault[0]).replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
            return body[0], None
        except Exception as e:
            error_msg = _('An error happened while connecting to the '
                          'server proxy {0} with the namespace {1} using the '
                          'action {2}: {3}').format(server.proxy,
                                                    server.namespace,
                                                    action,
                                                    format_exception(e))
            return None, error_msg
        return None, 'Unknown error'

    def _save_error(self, cr, uid, ids, text, context=None, show_errors=False):
        if not isinstance(ids, list):
            ids = [ids]
        if context is None:
            # So we can safely change the context
            ctx2 = {}
        else:
            ctx2 = context.copy()
        ctx2['mail_thread_no_duplicate'] = timedelta(hours=1)
        con_obj = self.pool.get('stock.connect')
        logger.error(text)
        if ctx2.get('show_errors', show_errors):
            for _id in ids:
                con_obj.message_post(cr, uid, _id, text, context=ctx2)
        else:
            raise osv.except_osv('Error on connection', text)

    def _get_timestamp(self):
        now = datetime.now()
        ts = now.strftime('%Y%m%d%H%M%S')
        return ts

    def _get_control_reference(self, cr, uid, ids, ns, type_, context=None):
        if context is None:
            context = {}
        if isinstance(ids, list):
            ids = ids[0]
        connect = self.pool.get('stock.connect').browse(cr, uid, ids, context)
        tools = context.get('xml_tools', _XmlTools)

        ts = self._get_timestamp()

        ret = tools.create_element('ControlReference', ns=ns)
        ret.append(tools.create_element('Type', ns=ns, text=type_))
        ret.append(tools.create_element('Sender', ns=ns, text=connect.yc_sender))
        ret.append(tools.create_element('Receiver', ns=ns, text=connect.yc_receiver))
        ret.append(tools.create_element('Timestamp', ns=ns, text=ts))
        ret.append(tools.create_element('OperatingMode', ns=ns, text=connect.yc_operating_mode))
        ret.append(tools.create_element('Version', ns=ns, text='1.0'))
        return ret

    def _save_file(self, cr, uid, ids, name, _input, _type, data, context=None):
        if context is None:
            context = {}
        if not isinstance(ids, list):
            ids = [ids]
        tools = context.get('xml_tools', _XmlTools)
        file_obj = self.pool.get('stock.connect.file')
        if not isinstance(data, str):
            data = tools.xml_to_string(data)
        if _type in ['BUR', 'WAR', 'WBA'] and '<!-- Currently no {0}s available -->'.format(_type) in data:
            logger.debug('Ignoring empty {0} file'.format(_type))
            return
        for _id in ids:
            file_obj.create(cr,
                            uid,
                            {'name': name,
                             'input': _input,
                             'type': _type.lower(),
                             'binary_content': False,
                             'content': data,
                             'stock_connect_id': _id},
                            context=context)

    def _get_soap_file(self, cr, uid, ids, server, action, ns_name, root_name, _type, context=None, root=None):
        if context is None:
            context = {}
        tools = context.get('xml_tools', _XmlTools)
        if root is None:
            # If the root is missing, we may create it
            if _type == 'BUR':
                # BUR has changed, so it won't have an specific request for the moment
                # BUR is very special, so delegate
                return self._get_bur_soap_file(cr, uid, ids, server, action, ns_name, root_name, _type, context)
            ns = tools.schema_namespaces[ns_name]
            root = tools.create_element(root_name, ns=ns)
            root.append(self._get_control_reference(cr, uid, ids, ns, _type, context))
        ret, err = self._send_item(cr, uid, ids, server, root, action, context=context)
        if err:
            self._save_error(cr, uid, ids, _ERR_MSG.format(ns_name, '', err), context=context, show_errors=bool(ret or False))
            return False
        self._save_file(cr, uid, ids, '{0}_{1}'.format(self._get_timestamp(), _type), True, _type, ret, context)
        return ret or True

    def _get_bur_soap_file(self, cr, uid, ids, server, action, ns_name, root_name, _type, context=None):
        tools = context.get('xml_tools', _XmlTools)
        ns = tools.schema_namespaces[ns_name]
        root = tools.create_element(root_name, ns=ns)
        root.append(self._get_control_reference(cr, uid, ids, ns, _type, context))
        this = self.__this(cr, uid, ids, context)
        _now = datetime.now()

        if this.yc_bur_send_elapsed_days:
            if this.yc_last_bur_check:
                _old = datetime.strptime(this.yc_last_bur_check,
                                         DEFAULT_SERVER_DATETIME_FORMAT)
                diff = _now - _old
                diff = int(diff.days)
                if diff > 999:
                    diff = 999
                if diff == 0 and _now.day != _old.day:
                    # The never-feed-after-midnight check
                    diff = 1
                root.append(tools.create_element(
                    'ElapsedDays', text=diff, ns=ns))
            else:
                # By default we send 1 day
                root.append(tools.create_element(
                    'ElapsedDays', text=1, ns=ns))

        if self._get_soap_file(cr, uid, ids, server, action, ns_name, root_name, _type, context, root):
            # If everything goes clear, we set the last check
            this.write({'yc_last_bur_check': _now.strftime(DEFAULT_SERVER_DATETIME_FORMAT)})

    def _get_file_for_soap(self, cr, uid, ids, file_id, context=None):
        tools = context.get('xml_tools', _XmlTools)
        _file = self.pool.get('stock.connect.file').browse(cr, uid, file_id, context)
        return tools.open_xml(_file.content, _file.type)

    def _get_wab_for_soap(self, cr, uid, ids, file_id, context=None):
        tools = context.get('xml_tools', _XmlTools)
        ns = tools.schema_namespaces['wab']
        _file = self.pool.get('stock.connect.file').browse(cr, uid, file_id, context)
        wab_root = tools.open_xml(_file.content, 'wab')
        order_docs = wab_root.xpath('//wab:OrderDocuments', namespaces=tools.schema_namespaces)[0]
        names = [x.text for x in order_docs[0]]
        order_docs.remove(order_docs[0])
        for att in _file.attachments:
            if att.name not in names:
                raise Exception('Unknown file {0}'.format(att.name), 'Expecting one of: {0}'.format(', '.join.names))
            names.remove(att.name)
            doc = tools.create_element('Docs', ns=ns)
            doc.append(tools.create_element('DocType', text=att.name.split('_')[1][:2], ns=ns))
            doc.append(tools.create_element('DocMimeType', text=att.name[-3:], ns=ns))
            doc.append(tools.create_element('DocStream', text=att.datas, ns=ns))
            order_docs.append(doc)

        return wab_root

    def _get_art_for_soap(self, cr, uid, ids, file_id, context=None):
        if context is None:
            context = {}
        tools = context.get('xml_tools', _XmlTools)
        _file = self.pool.get('stock.connect.file').browse(cr, uid, file_id, context)
        art_root = tools.open_xml(_file.content, 'art')
        ns = tools.schema_namespaces['art']
        ret = []
        control_reference = tools.nspath(art_root, '//art:ControlReference')[0]
        pos_no = 0
        pending = False
        limit = context['limit_files']
        if _file.internal_index < 0:
            return ret
        for article in tools.nspath(art_root, '//art:Article'):
            # Have we read enough?
            if limit[0] and limit[0] <= limit[1]:
                pending = True
                break
            # The pointer points to the next one
            pos_no += 1
            # Are we reading new items?
            if pos_no > _file.internal_index:
                limit[1] += 1
            else:
                continue
            new_root = tools.create_root('{{{art}}}ART')
            new_root.append(copy.deepcopy(control_reference))
            art_list = tools.create_element('ArticleList', ns=ns)
            art_list.append(article)
            new_root.append(art_list)
            ret.append(new_root)
        if pending:
            _file.write({'internal_index': pos_no})
        else:
            _file.write({'internal_index': -1})
        return ret

    def _get_wbl_for_soap(self, cr, uid, ids, file_id, context=None):
        if context is None:
            context = {}
        tools = context.get('xml_tools', _XmlTools)
        _file = self.pool.get('stock.connect.file').browse(cr, uid, file_id, context)
        wbl_root = tools.open_xml(_file.content, 'wbl')
        return wbl_root

    def _send_item_to_soap(self, cr, uid, ids, server, file_id, xml_part, action, schema_name, context=None):

        return self._send_item(cr, uid, ids, server, xml_part, action, schema_name=schema_name, context=context)

    def _send_xml_on_soap(self, cr, uid, ids, server, function, action, _type, context=None):
        if context is None:
            context = {}
        file_obj = self.pool.get('stock.connect.file')
        file_ids = file_obj.search(cr, uid, [('priority', '>=', 0),
                                             ('type', '=', _type),
                                             ('stock_connect_id', '=', ids),
                                             ('input', '=', False),
                                             ('state', '=', 'ready'),
                                             ('parent_file_id', '=', False),
                                             ('error', '=', False)], context=context)
        file_obj.lock_file(cr, uid, file_ids, context=context)
        html_parser = HTMLParser.HTMLParser()
        for file_id in file_ids:
            err = False
            limit = context['limit_files']
            rets = []
            filename_index = None
            if limit[0] and limit[0] <= limit[1]:
                break
            try:
                cr.execute("SAVEPOINT soap_send_file;")
                _file = file_obj.browse(cr, uid, file_id, context)
                filename_index = _file.internal_index
                xml_root = function(cr, uid, ids, file_id, context=context)
                if not isinstance(xml_root, list):
                    xml_root = [xml_root]
                    filename_index = None
                for xml_part in xml_root:
                    ret, err = self._send_item_to_soap(cr, uid, ids, server, file_id, xml_part, action, schema_name=_type, context=context)
                    if err:
                        # This undoes the encoding made in _send_item()
                        # I kept the encoding in _send_item() just in case
                        # it's used by anyone else and wants it that way.
                        err_decoded = html_parser.unescape(err or '')
                        _file.write({'error': True,
                                     'info': err_decoded,
                                     })

                        project_issue_obj = self.pool.get('project.issue')

                        project_issue_obj.create_issue(cr, uid,
                                                       'stock.connect.file',
                                                       file_id, err,
                                                       context=context)
                        break

                    if ret:
                        rets.append(ret)

                    if not err and not ret:
                        break
                cr.execute("RELEASE SAVEPOINT soap_send_file;")
            except Exception as e:
                cr.execute("ROLLBACK TO SAVEPOINT soap_send_file;")
                err = format_exception(e)
            if err:
                error_context = context.copy()
                error_context.update({'show_errors': True})
                self._save_error(cr, uid, ids, err, context=error_context)
            elif len(rets) > 0:
                needs_response_from_server = False
                _file = file_obj.browse(cr, uid, file_id, context=context)

                if _file.internal_index <= 0:
                    if _type in self.files_needing_ack(cr, uid, ids, context=context):
                        # By default server_ack is set to True, so special
                        # cases (only those which require an acknowledgement)
                        # can set it to False. So if it's set to False, is
                        # becase we expect an ACK to arrive in the future.
                        needs_response_from_server = True
                        _file.write({'internal_index': 0, 'state': 'done', 'server_ack': False})
                    else:
                        _file.write({'internal_index': 0, 'state': 'done'})

                if needs_response_from_server:
                    # If the type of file needs an acknoledgement (i.e. a
                    # response from the server) we prepare the files for them.
                    pos_no = 0
                    for ret in rets:
                        pos_no += 1
                        if filename_index is None:
                            name = 'RESPONSE_{0}'.format(_file.name)
                        else:
                            name = 'RESPONSE_sub{0}_{1}'.format(
                                filename_index + pos_no, _file.name)
                        self._save_soap_return(cr, uid, ids, file_id, name,
                                               ret, action, context)

        file_obj.unlock_file(cr, uid, file_ids, context=context)

    def _save_soap_return(self, cr, uid, ids, file_id, filename, xml_node, action, context=None):
        if context is None:
            context = {}
        tools = context.get('xml_tools', _XmlTools)
        file_obj = self.pool.get('stock.connect.file')
        event_obj = self.pool.get('stock.event')
        resp = file_obj.create(cr, uid, {'content': tools.xml_to_string(xml_node),
                                         'name': filename,
                                         'input': True,
                                         'stock_connect_id': ids,
                                         'res_id': file_id,
                                         'model': 'stock.connect.file'}, context)
        event_obj.create(cr, uid, {'event_code': 'yellowcubesoap_{0}'.format(action),
                                   'res_id': resp,
                                   'model': 'stock.connect.file',
                                   }, context)
        return

    def _get_proxy(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        if isinstance(ids, list):
            ids = ids[0]
        tools = context.get('xml_tools', _XmlTools)
        connect = self.pool.get('stock.connect').browse(cr, uid, ids, context)
        config = self.pool.get('configuration.data').get(cr, uid, [], context)
        wsdl = etree.parse(connect.yc_wsdl_endpoint)
        # server = SoapClient(wsdl=connect.yc_wsdl_endpoint)
        server = SOAPProxy(wsdl.xpath('//soap:address', namespaces=tools.schema_namespaces)[0].attrib['location'])
        server.config.debug = 1 if config.debug else 0
        return server

    def connection_get_files(self, cr, uid, ids, context=None):
        self._process_gen_response(cr, uid, ids, context=context)
        if isinstance(ids, list):
            # We must treat different connections, differently
            for _id in ids:
                self.connection_get_files(cr, uid, _id, context)
            return True
        if context is None:
            ctx2 = {}
        else:
            ctx2 = context.copy()
        this = self.__this(cr, uid, ids, context)
        ctx2['warehouse_id'] = this.warehouse_ids[0].id

        datetime_now_str = datetime.now().strftime(DEFAULT_SERVER_DATETIME_FORMAT)
        this = self.__this(cr, uid, ids, ctx2)
        server = self._get_proxy(cr, uid, ids, ctx2)

        # Fills in the list of actions to perform.
        actions = []
        if self.is_type_enabled(cr, uid, ids, 'bar', context=ctx2) and self._attempt_to_download_bar(cr, uid, ids, ctx2):
            actions.append(('GetInventory', 'bar_req', 'BAR_Request', 'BAR'))
        actions.extend([
            # ('GetYCCustomerOrderStatus', None, None, None),
            ('GetYCCustomerOrderReply', 'war_req', 'WAR_Request', 'WAR'),
            ('GetYCGoodsMovements', 'bur_req', 'BUR_Request', 'BUR'),
            # ('GetInsertArticleMasterDataStatus', None, None, None),
            # ('GetYCSupplierOrderStatus', None, None, None),
            ('GetYCSupplierOrderReply', 'wba_req', 'WBA_Request', 'WBA'),
        ])

        # Performs the actions, in the order introduced.
        for action in actions:
            if not self.is_type_enabled(cr, uid, ids, action[1], context=ctx2):
                continue
            success = self._get_soap_file(cr, uid, ids, server, *action, context=ctx2)

            if success and action[1] in ['bar_req', 'war_req', 'wba_req']:
                if isinstance(success, etree._Element):
                    type_ = action[1][:3]
                    expr = "//*[local-name()='{0}']".format(
                        type_.upper())
                    items = success.xpath(expr)
                    if len(items) > 0:
                        this.write({
                            'yc_{0}_last_check'.format(type_): datetime_now_str
                        })
                    else:
                        logger.info('{0} response was empty'.format(action[1]))

        return True

    def _attempt_to_download_bar(self, cr, uid, ids, context=None):
        ''' Returns whether we are going to attempt to download a BAR file or not,
            i.e. whether we are going to send a BAR request.
               We only download a BAR once a day, and only between a timeframe, and only if no
            WAR has been processed in advance during the same day.
               If the timeframe is not defined, we do not download the BAR, to be conservative.
        '''
        if context is None:
            context = {}
        if type(ids) is not list:
            ids = [ids]

        attempt_to_download_bar = True

        config_data = self.pool.get('configuration.data').get(cr, uid, [], context=context)
        current_timezone = config_data.support_timezone
        now = datetime.now(pytz.timezone(current_timezone))

        stock_connect = self.pool.get('stock.connect').browse(cr, uid, ids[0], context=context)
        if (not stock_connect.yc_bar_check_starting_hour) or (not stock_connect.yc_bar_check_ending_hour):
            attempt_to_download_bar = False

        else:
            current_hour = now.hour + now.minute / 60.0  # Converts the hour to a decimal number.
            timewindow_is_opened = stock_connect.yc_bar_check_starting_hour <= current_hour <= stock_connect.yc_bar_check_ending_hour
            bar_was_retrieved_today = stock_connect._datefield_encodes_today_date('yc_bar_last_check', now, current_timezone, context=context)
            war_was_seen_today = stock_connect._datefield_encodes_today_date('yc_war_last_check', now, current_timezone, context=context)
            wba_was_seen_today = stock_connect._datefield_encodes_today_date('yc_wba_last_check', now, current_timezone, context=context)

            if (not timewindow_is_opened) or (bar_was_retrieved_today) or (war_was_seen_today) or (wba_was_seen_today):
                attempt_to_download_bar = False

        return attempt_to_download_bar

    def connection_send_files(self, cr, uid, ids, context=None):
        if isinstance(ids, list):
            # We must treat different connections, differently
            for _id in ids:
                self.connection_send_files(cr, uid, _id, context)
            return True
        if context is None:
            ctx2 = {}
        else:
            ctx2 = context.copy()
        this = self.__this(cr, uid, ids, ctx2)
        ctx2['warehouse_id'] = this.warehouse_ids[0].id
        # Limit of transmissions
        ctx2['limit_files'] = [this.limit_of_connections, 0]

        server = self._get_proxy(cr, uid, ids, ctx2)
        actions = [
            (self._get_wab_for_soap, 'CreateYCCustomerOrder', 'wab'),
            (self._get_wbl_for_soap, 'CreateYCSupplierOrder', 'wbl'),
            (self._get_art_for_soap, 'InsertArticleMasterData', 'art'),
        ]
        for action in actions:
            limit = ctx2['limit_files']
            if self.is_type_enabled(cr, uid, ids, action[2], context=ctx2):
                self._send_xml_on_soap(cr, uid, ids, server, *action, context=ctx2)
            if limit[0] and limit[0] <= limit[1]:
                break
        return True

    def _process_gen_response(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        if type(ids) is not list:
            ids = [ids]
        tools = context.get('xml_tools', _XmlTools)

        stock_connect_file_obj = self.pool.get('stock.connect.file')

        stock_connect = self.browse(cr, uid, ids[0], context=context)

        domain = [
            ('stock_connect_id', '=', stock_connect.id),
            ('model', '=', 'stock.connect.file'),
            ('state', '=', 'draft'),
            ('type', '=', False),
            ('input', '=', True),
            ('error', '=', False)
        ]
        gen_file_ids = stock_connect_file_obj.search(cr, uid, domain, context=context)
        for gen_file in stock_connect_file_obj.browse(cr, uid, gen_file_ids, context=context):
            # Find the elements and mark them
            if 'GEN_Response>' in gen_file.content:
                gen_file.write({'type': 'gen', 'state': 'ready'})
        domain[2] = ('state', '=', 'ready')
        domain[3] = ('type', '=', 'gen')

        def __read_file(xml_node):
            return {
                'type': tools.nspath(xml, 'gen:MessageType')[0].text,
                'ref': tools.nspath(xml, 'gen:Reference')[0].text,
                'status_text': tools.nspath(xml, 'gen:StatusText')[0].text,
                'status_code': int(tools.nspath(xml, 'gen:StatusCode')[0].text),
                'status_type': tools.nspath(xml, 'gen:StatusType')[0].text,
            }

        server = self._get_proxy(cr, uid, ids, context=context)
        gen_file_ids = stock_connect_file_obj.search(cr, uid, domain, order='id ASC', context=context)
        for gen_file in stock_connect_file_obj.browse(cr, uid, gen_file_ids, context=context):
            # Process all the files
            try:
                original_file = stock_connect_file_obj.browse(cr, uid, gen_file.res_id, context)
                if original_file.server_ack:
                    # Only process if required
                    msg = _("Ignoring Response on behalf old ACK on file")
                    logger.warning(msg)
                    gen_file.write({'error': False, 'state': 'cancel', 'info': msg})
                    continue
                xml = tools.open_xml(gen_file.content, repair=False)
                values = __read_file(xml)
                if values['status_type'] != 'S' or values['status_code'] > 100:
                    # Don't re-process errors
                    raise Exception(_("Error on Status response"), values['status_text'])
                elif values['status_code'] == 100:
                    # If it was finished, don't reprocess
                    gen_file.write({'state': 'done', 'info': values['status_text'], 'internal_index': values['status_code']})
                    original_file.write({'server_ack': True})
                else:
                    # Send a request
                    ns = tools.schema_namespaces['gen_req']
                    xml_req = tools.create_root('{{{gen_req}}}GEN_STATUS')
                    xml_req.append(self._get_control_reference(cr, uid, ids, ns, values['type'], context=context))
                    xml_req.append(tools.create_element('Reference', text=values['ref'], ns=ns))
                    xml_ret, err_ret = self._send_item(cr, uid, ids, server, xml_req, action='GetInsertArticleMasterDataStatus', schema_name='gen_req', context=context)
                    if err_ret:
                        # Write errors on file
                        gen_file.write({'error': True, 'info': err_ret})
                    else:
                        values_ret = __read_file(xml_ret)
                        if values_ret['status_type'] != 'S' or values_ret['status_code'] > 100:
                            # Strange status codes are errors
                            gen_file.write({'error': True, 'info': tools.xml_to_string(xml_ret), 'internal_index': values_ret['status_code']})
                        elif values_ret['status_code'] < 100:
                            # Modify the file if pending, avoiding excess of inputs
                            gen_file.write({'content': tools.xml_to_string(xml_ret), 'internal_index': values_ret['status_code']})
                        else:
                            # Propagate end
                            gen_file.write({'state': 'done', 'content': tools.xml_to_string(xml_ret), 'info': values_ret['status_text'], 'internal_index': values_ret['status_code']})
                            original_file.write({'server_ack': True})
            except Exception as e:
                logger.error(format_exception(e))
                gen_file.write({'error': True, 'info': format_exception(e)})


class _soap_debug:
    _file = None

    def __init__(self, yc_soap, action):
        self.yc_soap = yc_soap
        self.action = action

    def __enter__(self):
        if self.yc_soap.yc_soap_debugfile:
            now = datetime.now()
            params = {
                'action': self.action,
                'date': now.strftime('%Y%m%d'),
                'time': now.strftime('%H%M%S'),
                'dbname': self.yc_soap._cr.dbname,
            }
            name = self.yc_soap.yc_soap_debugfile.format(**params)
            self._file = open(name, 'a')
        return self

    def write(self, case, text):
        if self._file:
            self._file.write('+++ ')
            self._file.write(datetime.now().strftime('%x %X '))
            self._file.write(case)
            self._file.write('\n')
            self._file.write(text)
            self._file.write('\n---\n')

    def __exit__(self, _type, value, traceback):
        if self._file:
            self._file.close()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: