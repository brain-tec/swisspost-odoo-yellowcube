<html>
    <head>
        <style type="text/css">
            ${css}
        </style>
    </head>

    <body style="border:0.01; margin: 0.01;">

    % for o in objects:

        <% conf_data = get_configuration_data({'lang': o.partner_id.lang}) %>
        <% setLang(o.partner_id.lang) %>

        <!-- Determines the number of pages, and the lines per page. -->
        <% num_lines_per_page_first = conf_data.stock_picking_report_num_lines_per_page_first or 10 %> 
        <% num_lines_per_page_not_first = conf_data.stock_picking_report_num_lines_per_page_not_first or 15 %>
        <% page_lines = assign_lines_to_pages(o.move_lines, num_lines_per_page_first, num_lines_per_page_not_first) %>
        <% total_pages = len(page_lines) %>

        <% num_slip_line = 1 %>
        % while get_page_num() < total_pages:

        <div class="container_defining_margins">

            <div class="report_pseudo_header">
                <div class="report_header_logo">
                    ${o.get_logo(conf_data.stock_picking_logo)}
                </div>
                <div class="report_header_address">
                    ${o.company_id.partner_id.name or ''} <span class="linebreak" />
                    <% partner_addr_data = o.get_company_address('linebreak') %>
                    ${partner_addr_data or ''}
                </div>
                <div class="report_header_pagenumber">
                    ${_('Page')}: ${get_page_num() + 1} / ${total_pages}
                </div>
            </div>
            <div class="horizontal_line_black"></div>

			<% client_order_ref = o.sale_id and o.sale_id.client_order_ref or False%>

            <% invoice_number = o.sale_id and len(o.sale_id.invoice_ids) > 0 and o.sale_id.invoice_ids[0].number or '' %>
            % if is_first_page():
            <div class="intro_info">
                <div class="intro_info_info">
                    <div class="airy_element"><span>${_("Phone")}</span><span>${o.company_id.partner_id.phone or ''}</span></div>
                    <div class="airy_element"><span>${_("E-Mail")}</span><span>${o.company_id.partner_id.email or ''}</span></div>
                    <div class="airy_element"><span>${_("Web")}</span><span>${o.company_id.partner_id.website or ''}</span></div>
                    <div class="airy_element"><span>${_("Tax number")}</span><span>${o.company_id.vat or ''}</span></div>
                    <div class="airy_element"><span>&nbsp;</span><span>&nbsp;</span></div>

                    <div class="airy_element"><span>${_("Customer number")}</span><span>${o.partner_id.get_ref() or ''}</span></div>
                    <div class="airy_element"><span>${_("Sale order number")}</span><span>${o.sale_id.name or ''}</span></div>
                    <div class="airy_element"><span>${_("Date")}</span><span>${formatLang(get_date_today() or '', date=True)}</span></div>
                    %if client_order_ref:
                    <div class="airy_element"><span>${_("Your reference")}</span><span>${client_order_ref}</span></div>
                    %endif
                    <div class="airy_element"><span>&nbsp;</span><span>&nbsp;</span></div>
                    <div class="airy_element"><span>&nbsp;</span><span>&nbsp;</span></div>
                </div>
                <div style="clear:both"></div>
                <div class="intro_info_info_optional">
                    %if o.carrier_id.show_name_on_picking:
                    <div class="airy_element"
                         style="font-size:${conf_data.stock_picking_report_delivery_method_size}pt;
                                font-weight:${conf_data.stock_picking_report_delivery_method_weight};">
                        <span style="width:${conf_data.stock_picking_report_delivery_optional_info_width_left}mm">
                            ${_('Delivery method')}</span><span>${o.carrier_id.name}
                        </span>
                    </div>
                    %endif
                    <div style="clear:both"></div>
                    %if o.carrier_id.show_customer_phone_on_picking:
                    <div class="airy_element"
                         style="font-size:${conf_data.stock_picking_report_customer_phone_size}pt;
                                font-weight:${conf_data.stock_picking_report_customer_phone_weight};">
                        <span style="width:${conf_data.stock_picking_report_delivery_optional_info_width_left}mm">
                            ${_('Customer phone number')}</span><span>${o.partner_id.mobile or o.partner_id.phone or ''}
                        </span>
                    </div>
                    %endif
                </div>

                <% address_fields = o.get_address_fields() %>
                <div class="address_window">
                    <div class="addr_head">
                        <div class="addr_head_left">
                            <div class="addr_head_left_frankingmark">P.P.</div>
                            <div class="addr_head_left_postcode">
                            ${conf_data.stock_picking_franking_country_code or ''} - ${conf_data.stock_picking_franking_zip or ''} <span class="linebreak" />
                            ${conf_data.stock_picking_franking_town or ''}
                            </div>
                        </div>
                        <div class="addr_head_right">
                            <div class="addr_head_right_processing">
                                B-ECONOMY
                            </div>
                            <div class="addr_head_right_logo_and_invoice_number">
                                Post CH AG <span class="linebreak" />
                                ${conf_data.stock_picking_postmail_rrn or ''}
                            </div>
                        </div>
                    </div>
                    <div class="addr_separator"></div>
                    <div class="addr_body">
                        <div class="addr_body_address">
                            <% separate_salutation = False if bool(o.partner_id.company) else True %>
                            <% delivery_address = o.partner_id.get_html_full_address('linebreak', separate_salutation=separate_salutation) %>
                            ${delivery_address}
                        </div>
                        <div class="addr_body_qr">
                            ${o.get_logo(conf_data.stock_picking_qr)}
                        </div>
                    </div>
                </div><!-- <div class="address_window"> -->
            </div> 

            <div style="clear:both;"></div>
            <div class="inline_delivery_address">
                %if o.sale_id and conf_data.stock_picking_report_print_invoice_address:
                   <u>${_('Invoice Address')}</u><span class="linebreak" />
                   <% delivery_address = o.sale_id.partner_invoice_id.get_html_full_address() %>
                   ${delivery_address}
                %else:
                	&nbsp;
                %endif
            </div>

            % else:
            <div class="intro_info_not_first_page"></div>
            % endif

            <% move_lines = page_lines[get_page_num()] %>

            <div class="mako_document_title">
                ${_('DELIVERY NUMBER')}: ${o.name or ''}
            </div>

            % if is_first_page():
            <div class="mako_document_content_delivery_slip">
            % else:
            <div class="mako_document_content_not_first_page_delivery_slip">
            % endif

                <% num_columns_in_table = 4 %>
                % if conf_data.stock_picking_report_show_lots:
                    <% num_columns_in_table += 1 %>
                % endif

                <!-- <div class="invoice_lines"> -->
                <table style="width:100%;" class="print_friendly">
                % for object_line in move_lines:

                    <% type_of_line, content_of_line = object_line %>

                    % if type_of_line == 'heading_regular_line':
                        <tr>
                            <td class="line_invoice_line shadowed">${_("Pos.")}</td>
                            <td class="line_product_no shadowed">${_("Product No.")}</td>
                            %if conf_data.stock_picking_report_show_lots:
                            	<td class="line_product_name_picking shadowed">${_("Description")}</td>
                            	<td class="line_lot_no shadowed">${_("Lot No.")}</td>
                           	%else:
                           		<td class="line_product_name_picking_no_lots shadowed">${_("Description")}</td>
                           	%endif
                            <td class="line_quantity shadowed">${_("Quantity")}</td>
                        </tr>
                    % endif

                    %if type_of_line == 'regular_line':
						<tr>
                            <td class="line_invoice_line">${num_slip_line}</td>
                            <% num_slip_line += 1 %>
                            <td class="line_product_no">${content_of_line.product_id and content_of_line.product_id.default_code or ''}</td>
                            %if conf_data.stock_picking_report_show_lots:
                                <td class="line_product_name_picking">${content_of_line.product_id and content_of_line.product_id.name or ''}</td>
                                <td class="line_lot_no">${content_of_line.prodlot_id and content_of_line.prodlot_id.name or ''}</td>
                            %else:
                                <td class="line_product_name_picking_no_lots">${content_of_line.product_id and content_of_line.product_id.name or ''}</td>
                            %endif
                            <td class="line_quantity">${content_of_line.product_qty or ''}</td>
                    	</tr>
                    % endif

                    % if type_of_line == 'note_message':
                        <tr>
                            <td class="line_invoice_line_no_padding_left" colspan="${num_columns_in_table}">
                                <p style="text-align: justify; text-justify: inter-word;">
                                    ${_('Note')}: ${o.sale_id.note or ''}
                                </p>
                            </td>
                        </tr>
                    % endif

                    % if type_of_line == 'ending_message':
                        <tr>
                            <td class="line_invoice_line_no_padding_left" colspan="${num_columns_in_table}">
                                <p style="text-align: justify; text-justify: inter-word;">
                                    ${conf_data.stock_picking_ending_text or ''}
                                </p>
                            </td>
                        </tr>
                    % endif

                    % if type_of_line == 'gift_text':
                        <tr>
                            <td class="line_invoice_line_no_padding_left" colspan="${num_columns_in_table}">
                                <p style="margin-top: 1cm;"><i>Gift text:</i></p>
                                <p style="text-align: justify; text-justify: inter-word;">
                                    ${o.sale_id.additional_message_content.replace('\n', '<br />')}
                                </p>
                            </td>
                        </tr>
                    % endif

                    % if type_of_line == 'blank_line':
                        <tr>
                            <td colspan="${num_columns_in_table}">&nbsp;</td>
                        </tr>
                    % endif

                    % if type_of_line == 'more_deliveries_to_come_message':
                        <tr>
                            <td class="line_invoice_line_no_padding_left" colspan="${num_columns_in_table}">
                                <p style="text-align: justify; text-justify: inter-word;">
                                    ${conf_data.stock_picking_report_text_for_partial_deliveries or ''}
                                </p>
                            </td>
                        </tr>
                    % endif


                    % if type_of_line == 'backorder_products_title':
                        <tr><td colspan="${num_columns_in_table}">&nbsp;</td></tr>
                        <tr>
                            <td class="line_invoice_line_no_padding_left" colspan="9">
                                <strong>
                                    ${conf_data.stock_picking_backorder_line_text}
                                </strong>
                            </td>
                        </tr>
                        <tr><td colspan="${num_columns_in_table}">&nbsp;</td></tr>
                    % endif

                    % if type_of_line == 'backorder_products_heading':
                        <tr>
                            <td class="line_invoice_line shadowed" colspan="2">${_("Product No.")}</td>
                            <!-- <td class="line_product_no shadowed"></td> -->
                            <td class="line_product_name_picking shadowed"
                            % if conf_data.stock_picking_report_show_lots:
                                colspan="2">
                            % else:
                                colspan="1">
                            % endif
                            ${_("Description")}</td>
                            <!-- <td class="line_lot_no shadowed"></td> -->
                            <td class="line_quantity shadowed">${_("Quantity")}</td>
                        </tr>
                    % endif

                    % if type_of_line == 'backorder_products_line':
                        <tr>
                            <% product, product_uom_qty, product_uom = content_of_line %>

                            <td class="line_invoice_line" colspan="2">${product.default_code}</td>
                            <!-- <td class="line_product_no" colspan="2"></td> -->
                            <td class="line_product_name_picking"
                            % if conf_data.stock_picking_report_show_lots:
                                colspan="2">
                            % else:
                                colspan="1">
                            % endif
                                ${product.name}</td>
                            <!-- td class="line_lot_no">${product_uom_qty}</td> -->
                            <td class="line_quantity">${product_uom_qty}</td>
                        </tr>
                    % endif

                % endfor
                </table>
            </div>  <!-- div class="mako_document_content_delivery_slip" -->

        </div>  <!-- div class="container_defining_margins" -->

        <% increment_page_num() %>
        % endwhile

    % endfor
    </body>
</html>
