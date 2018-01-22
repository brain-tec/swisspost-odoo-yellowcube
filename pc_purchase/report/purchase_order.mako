<html>
    <head>
        <style type="text/css">
            ${css}
        </style>
    </head>

    <body style="border:0.01; margin: 0.01;">

        % for o in objects:

         <% conf_data = get_configuration_data({'lang': o.partner_id.lang}) %>
         <% currency_name = o.currency_id.name or '' %>
         <% setLang(o.partner_id.lang) %>

         <!-- Collect data -->
         <% procurement_order = get_procurement_order(o) %>
         <% num_lines_per_page_first = conf_data.purchase_report_num_lines_per_page_first or 10 %>
         <% num_lines_per_page_not_first = conf_data.purchase_report_num_lines_per_page_not_first or 35 %>
         <% page_lines = assign_lines_to_pages(o.order_line, procurement_order, num_lines_per_page_first, num_lines_per_page_not_first, payment_term=o.payment_term_id) %>
         <% total_pages = len(page_lines) %>

         <% num_purchase_line = 1  %>
         % while get_page_num() < total_pages:

         <div class="container_defining_margins">

            <div class="report_pseudo_header">
                <div class="report_header_logo">
                    ${o.get_logo(conf_data.purchase_logo)}
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

            % if is_first_page():
            <div class="intro_info">
                <div class="intro_info_info">
                    <% overriden_company_address = conf_data.purchase_company_address_id or o.company_id.partner_id %>
                    <div class="airy_element"><span>${_("Phone")}</span><span>${overriden_company_address.phone or ''}</span></div>
                    <div class="airy_element"><span>${_("E-Mail")}</span><span>${overriden_company_address.email or ''}</span></div>
                    <div class="airy_element"><span>${_("Web")}</span><span>${o.company_id.partner_id.website or ''}</span></div>
                    <div class="airy_element"><span>${_("Tax number")}</span><span>${o.company_id.partner_id.company_id.vat or ''}</span></div>
                    <div class="airy_element"><span>&nbsp;</span><span>&nbsp;</span></div>

                    <div class="airy_element"><span>${_("Customer number")}</span><span>${o.partner_id.get_ref() or ''}</span></div>
                    <div class="airy_element"><span>${_("Purchase order number")}</span><span>${o.name or ''}</span></div>
                    <div class="airy_element"><span>${_("Purchase order date")}</span><span>${formatLang(o.date_order or '', date=True)}</span></div>
                    <div class="airy_element"><span>${_("Expected Date")}</span><span>${formatLang(o.minimum_planned_date or '', date=True)}</span></div>
                    <div class="airy_element"><span>&nbsp;</span><span>&nbsp;</span></div>
                    <div class="airy_element"><span>&nbsp;</span><span>&nbsp;</span></div>
                </div>
                <div style="clear:both"></div>

                <div class="address_window">
                    <div class="addr_head">
                        <div class="addr_head_left">
                            <div class="addr_head_left_frankingmark">P.P.</div>
                            <div class="addr_head_left_postcode">
                            ${conf_data.purchase_franking_country_code or ''} - ${conf_data.purchase_franking_zip or ''} <span class="linebreak" />
                            ${conf_data.purchase_franking_town or ''}
                            </div>
                        </div>
                        <div class="addr_head_right">
                            <div class="addr_head_right_processing">
                                B-ECONOMY
                            </div>
                            <div class="addr_head_right_logo_and_invoice_number">
                                Post CH AG <span class="linebreak" />
                                ${conf_data.purchase_postmail_rrn or ''}
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
                            ${o.get_logo(conf_data.purchase_qr)}
                        </div>
                    </div>
                </div><!-- <div class="address_window"> -->

                <div class="inline_delivery_address">
                    %if o.warehouse_id and o.warehouse_id.lot_input_id.partner_id and conf_data.purchase_report_print_delivery_address:
                       <u>${_('Delivery Address')}</u><span class="linebreak" />
                       <% delivery_address = o.warehouse_id.lot_input_id.partner_id.get_html_full_address() %>
                       ${delivery_address}
                    %else:
                        &nbsp;
                    %endif
                </div>
            </div>

            <div style="clear:both;"></div>

            % else:
            <div class="intro_info_not_first_page"></div>
            % endif

            <div class="mako_document_title">
                ${_('PURCHASE ORDER')}: ${o.name or ''}
            </div>

            <!-- <div style="clear:both;"></div> -->

            <% order_lines = page_lines[get_page_num()] %>

            % if is_first_page():
            <div class="mako_document_content_purchase_order">
            % else:
            <div class="mako_document_content_not_first_page_purchase_order">
            % endif

                    <table style="width:100%;" class="print_friendly">

                    % for object_line in order_lines:

                       <% type_of_line, content_of_line = object_line %>

                       % if type_of_line == 'heading_regular_line':
                            <tr>
                                <td class="line_invoice_line shadowed">${_("Pos.")}</td>
                                <td class="line_product_description shadowed" colspan="3">[${_("Product No.")}] ${_("Description")}</td>
                                <td class="line_quantity shadowed">${_("Quantity")}</td>
                                <td class="line_item_price shadowed">${_("Item price")}</td>
                                <td class="line_total_price shadowed">
                                    ${_("Total")}
                                    %if o.partner_id.lang[:2] == 'de':
                                    ${currency_name}
                                    %endif
                                </td>
                                <td class="line_tax_code shadowed">${_("Tax code")}</td>
                            </tr>
                       % endif

                       % if type_of_line == 'regular_line':
                            <tr>
                                <td class="line_invoice_line">${num_purchase_line}</td>
                                <% num_purchase_line += 1 %>
                                <td class="line_product_description" colspan="3">${content_of_line.name or ''}</td>
                                <% quantity_as_int = int(float(content_of_line.product_qty)) %>
                                <td class="line_quantity">${quantity_as_int or ''}</td>
                                <td class="line_item_price">${content_of_line.price_unit and formatLang(content_of_line.price_unit, monetary=True) or formatLang(0, monetary=True)}</td>
                                <% total_price = content_of_line.product_qty * content_of_line.price_unit %>
                                <td class="line_total_price">${formatLang(total_price, monetary=True)}</td>
                                <td class="line_tax_code">${len(content_of_line.taxes_id) and content_of_line.taxes_id[0].description or ''}</td>
                            </tr>
                       % endif

                       % if type_of_line == 'tax_line':
                          <tr>
                            <% tax_id = content_of_line %>
                            <% tax_code, quantity_with_taxes, quantity_corresponding_to_taxes = get_tax_breakdown(o.order_line, o, tax_id, {'lang': o.partner_id.lang}) %>
                            <td class="line_invoice_line_no_padding_left" colspan="3">${_('Tax Amount')} (${'{0}'.format(tax_code)})</td>
                            <td class="line_lot_no">${_('of')}</td>
                            <td class="line_quantity">${formatLang(quantity_with_taxes, monetary=True)}</td>
                            <td class="line_item_price">${formatLang(quantity_corresponding_to_taxes, monetary=True)}</td>
                          </tr>
                       % endif

                       % if type_of_line == 'blank_line':
                          <tr class="low_height"><td colspan="7">&nbsp;</td></tr>
                       % endif

                       % if type_of_line == 'total':
                          <tr>
                            <td class="line_invoice_line_no_padding_left" colspan="5"><b>${_("Total:")} ${"{currency_name}".format(currency_name=currency_name)}</b></td>
                            <td class="line_tax_code">&nbsp;</td>
                            <td class="line_total_price double_border_top_cell" style="font-weight: bold;">${formatLang(o.amount_total, monetary=True)}</td>
                            <td class="line_tax_code">&nbsp;</td>
                          </tr>
                       % endif

                       % if type_of_line == 'others':
                          <tr>
                            <td class="print_friendly" colspan="7">${content_of_line}</td>
                          </tr>
                       % endif

                       % if type_of_line == 'payment_term_line':
                          <tr>
                            <td class="line_invoice_line" colspan="7">${_("Payment term")} ${o.payment_term_id.name}</td>
                          </tr>
                       % endif

                    % endfor

                    </table>

            </div> <!-- END class="mako_document_content" -->

         </div> <!-- class="container_defining_margins" -->

         <div style="clear:both;">

         <% increment_page_num() %>
         % endwhile
        % endfor
    </body>
</html>
