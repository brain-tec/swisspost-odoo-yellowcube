<html>
    <head>
        <style type="text/css">
            ${css}
        </style>
    </head>

    <body style="border:0.01; margin: 0.01;">

        % for o in objects:

         <% conf_data = get_configuration_data({'lang': o.partner_id.lang}) %>

         <% currency_name = o.currency_id.symbol or '' %>
         
         <% setLang(o.partner_id.lang) %>

         <!-- Collect data -->
         <% num_lines_per_page_first = conf_data.invoice_report_num_lines_per_page_first or 9 %>
         <% num_lines_per_page_not_first = conf_data.invoice_report_num_lines_per_page_not_first or 20 %>
         <% page_lines = assign_lines_to_pages(o.invoice_line, num_lines_per_page_first, num_lines_per_page_not_first) %>

         <% total_pages = len(page_lines) %>
         <% subtotal_amount_with_taxes = 0.0 %>
         
         <% num_invoice_line = 1 %>
          % while get_page_num() < total_pages:
        
           <div class="container_defining_margins">

            <div class="report_pseudo_header">
                <div class="report_header_logo">
                    ${o.get_logo(conf_data.invoice_logo)}
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
            <!-- <div style="height: 1mm;"></div> -->

            <% sale_ids = o.get_sale_order_ids() %>
            <% client_order_ref = sale_ids and len(sale_ids) > 0 and sale_ids[0].client_order_ref or False%>

            % if is_first_page():
            <div class="intro_info">
                <div class="intro_info_info">
                    <div class="airy_element"><span>${_("Phone")}</span><span>${o.company_id.partner_id.phone or ''}</span></div>
                    <div class="airy_element"><span>${_("E-Mail")}</span><span>${o.company_id.partner_id.email or ''}</span></div>
                    <div class="airy_element"><span>${_("Web")}</span><span>${o.company_id.partner_id.website or ''}</span></div>
                    <div class="airy_element"><span>${_("Tax number")}</span><span>${o.company_id.vat or ''}</span></div>
                    <div class="airy_element"><span>&nbsp;</span><span>&nbsp;</span></div>
                    
                    <div class="airy_element"><span>${_("Customer number")}</span><span>${o.partner_id.get_ref() or ''}</span></div>
                    <div class="airy_element"><span>${_("Sale order number")}</span><span>${sale_ids and len(sale_ids) > 0 and sale_ids[0].name or _('No sale order associated')}</span></div>
                    %if client_order_ref:
                    <div class="airy_element"><span>${_("Your reference")}</span><span>${client_order_ref}</span></div>
                    %endif
                    <div class="airy_element"><span>${_("Sale order date")}</span><span>${formatLang(sale_ids and len(sale_ids) > 0 and sale_ids[0].date_order or '', date=True) or _('No sale order associated')}</span></div>
                    <div class="airy_element"><span>${_("Invoice date")}</span><span>${formatLang(o.date_invoice or '', date=True)}</span></div>
                    <div class="airy_element"><span>${_("Invoice number")}</span><span>${o.number or ''}</span></div>
                    %if sale_ids and len(sale_ids) > 0 and sale_ids[0].payment_method_id.epayment:
                        <div class="airy_element"><span>&nbsp;</span></div>
                    %else:
                        <div class="airy_element"><span>${_("Invoice due date")}</span>
                             <span>
                              % if o.state == 'paid':
                                ${_('This invoice has already been paid')}
                              % else:
                                ${formatLang(o.date_due or '', date=True)}
                              % endif
                             </span>
                        </div>
                    %endif
                    %if not client_order_ref:
                    <div class="airy_element"><span>&nbsp;</span></div>
                    %endif
                </div><!-- <div class="intro_info_info"> -->

                <!--  <div style="clear:both;"></div> -->

                <% address_fields = o.get_address_fields() %>
                <div class="address_window">
                    <div class="addr_head">
                        <div class="addr_head_left">
                            <div class="addr_head_left_frankingmark">P.P.</div>
                            <div class="addr_head_left_postcode">
                            ${conf_data.invoice_franking_country_code or ''} - ${conf_data.invoice_franking_zip or ''} <span class="linebreak" />
                            ${conf_data.invoice_franking_town or ''}
                            </div>
                        </div>
                        <div class="addr_head_right">
                            <div class="addr_head_right_processing">
                                B-ECONOMY
                                <!--
                                <span style="font-size: 12pt;">P.P.</span>
                                <span style="font-size: 24pt;">A</span>
                                -->
                            </div>
                            <div class="addr_head_right_logo_and_invoice_number">
                                Post CH AG <span class="linebreak" />
                                ${conf_data.invoice_postmail_rrn or ''}
                            </div>
                        </div>
                    </div>
                    <div class="addr_separator"></div>
                    <div class="addr_body">
                        <div class="addr_body_address">
                            <% separate_salutation = False if bool(o.partner_id.company) else True %>
                            <% invoice_address = o.partner_id.get_html_full_address('linebreak', separate_salutation=separate_salutation) %>
                            ${invoice_address}
                        </div>
                        <div class="addr_body_qr">
                            ${o.get_logo(conf_data.invoice_qr)}
                        </div>
                    </div>
                </div><!-- <div class="address_window"> -->

            </div><!-- <div class="intro_info"> -->

            <div style="clear:both;"></div>
            <div class="inline_delivery_address">
                %if sale_ids and conf_data.invoice_report_print_delivery_address:
                   <u>${_('Delivery Address')}</u><span class="linebreak" />
                   <% delivery_address = sale_ids[0].partner_shipping_id.get_html_full_address() %>
                   ${delivery_address}
                %else:
                	&nbsp;
                %endif
            </div>
            
            % else:
            <div class="intro_info_not_first_page"></div>
            % endif

            <% invoice_lines = page_lines[get_page_num()] %>

            <div class="mako_document_title">
                <span style="text-transform: uppercase;">${get_invoice_title(o.type, o.state, {'lang': o.partner_id.lang})}</span>
                <% is_partial_invoice = o.is_partial_invoice() %>
                %if is_partial_invoice:
		    <!-- currently deactivated -->
                    <!-- <span>${_('Partial Invoice')}</span> -->
                    <span>&nbsp;</span>
                %else:
                    <span>&nbsp;</span>
                %endif
            </div>

            % if is_first_page():
                <div class="mako_document_content">
            % else:
                <div class="mako_document_content_not_first_page">
            % endif
                    <!-- <div class="invoice_lines"> -->
                    <table style="width:100%;" class="print_friendly">
                    % for object_line in invoice_lines:

                       <% type_of_line = object_line.line_type %>
                       <% content_of_line = object_line.data %>

                       % if type_of_line == 'heading_regular_line':
                          <tr>
                            <td class="line_invoice_line shadowed">${_("Pos.")}</td>
                            <td class="line_product_no shadowed">${_("Product No.")}</td>
                            <td class="line_product_name shadowed" colspan="2">${_("Description")}</td>
                            <!-- <td class="line_lot_no shadowed">${_("Lot No.")}</td> -->
                            <td class="line_quantity shadowed">${_("Quantity")}</td>
                            <td class="line_item_price shadowed">${_("Item price")}</td>
                            % if conf_data.invoice_report_discount_column_type == 'hide':
                            <td class="line_discount shadowed">&nbsp;</td>
                            % else:
                            <td class="line_discount shadowed">${conf_data.invoice_report_discount_column_text}</td>
                            % endif
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
                            <td class="line_invoice_line">${num_invoice_line}</td>
                            <% num_invoice_line += 1 %>
                            <td class="line_product_no">${content_of_line.product_id.default_code}</td>
                            <td class="line_product_name" colspan="2">${content_of_line.product_id.name or ''}</td>
                            <!-- <td class="line_lot_no shadowed">&nbsp;</td> -->
                            <td class="line_quantity">${formatLang(content_of_line.quantity or '')}</td>
                            <td class="line_item_price">${content_of_line.price_unit and formatLang(content_of_line.price_unit, monetary=True) or formatLang(0, monetary=True)}</td>

                            <% total_price_as_is = content_of_line.price_total_less_disc %>

                            % if conf_data.invoice_report_discount_column_type == 'percentage':
                                <td class="line_discount">${formatLang(content_of_line.discount or 0, dp='Discount')}</td>
                            % elif conf_data.invoice_report_discount_column_type == 'amount':
                                <td class="line_discount">${formatLang(content_of_line.quantity * content_of_line.price_unit - total_price_as_is, monetary=True)}</td>
                            % else:
                                <td class="line_discount">&nbsp;</td>
                            % endif

                            <td class="line_total_price">${formatLang(total_price_as_is, monetary=True)}</td>
                            <td class="line_tax_code">${len(content_of_line.invoice_line_tax_id) and content_of_line.invoice_line_tax_id[0].description or ''}</td>
                          </tr>
                       % endif

                       % if type_of_line == 'discount_line':
                          <tr>
                            <td class="line_invoice_line_no_padding_left" colspan="7">${get_discount_description(content_of_line, {'lang': o.partner_id.lang})}</td>
                            <% num_invoice_line += 1 %>
                            <td class="line_total_price">${content_of_line.price_unit}</td>
                            <td class="line_tax_code">${len(content_of_line.invoice_line_tax_id) and content_of_line.invoice_line_tax_id[0].description or ''}</td>
                          </tr>
                       % endif
 
                       % if type_of_line == 'total_amount_saved':
                          <% total_discount_line = content_of_line %>
                          <tr>
                            <td class="line_invoice_line_no_padding_left" colspan="6">${conf_data.invoice_report_discounted_total_amount_text}</td>
                            <td class="line_discount">${formatLang(content_of_line, monetary=True)}</td>
                            <td class="line_total_price" colspan="2">&nbsp;</td>
                          </tr>
                       % endif
 
                       % if type_of_line == 'tax_line':
                          <tr>
                            <% tax_id = content_of_line %>
                            <% tax_code, quantity_with_taxes, quantity_corresponding_to_taxes = get_tax_breakdown(o.invoice_line, o, tax_id, {'lang': o.partner_id.lang}) %>
                            <td class="line_invoice_line_no_padding_left" colspan="3">${_('Tax Amount')} (${'{0}'.format(tax_code)})</td>
                            <td class="line_lot_no">${_('of')}</td>
                            <td class="line_quantity">${formatLang(quantity_with_taxes, monetary=True)}</td>
                            <td class="line_item_price">${formatLang(quantity_corresponding_to_taxes, monetary=True)}</td>
                            <td class="line_discount" colspan="3">&nbsp;</td>
                          </tr>
                       % endif

                       % if type_of_line == 'blank_line':
                          <tr class="low_height"><td colspan="9">&nbsp;</td></tr>
                       % endif

                       % if type_of_line == 'subtotal':
                          <tr>
                            <td class="line_invoice_line_no_padding_left" colspan="7">${_("Subtotal")}</td>
                            <!-- If content_of_line is None, it means we don't have discount lines, thus we must take the subtotal
                                 (which is displayed always with taxes) directly from the account.invoice. -->
                            % if content_of_line is None:
                              <% subtotal = o.amount_untaxed + o.amount_tax %>
                            % else:
                              <% subtotal = content_of_line.price_unit %>
                            % endif
                            <td class="line_total_price border_top_cell">${formatLang(subtotal, monetary=True)}</td>
                            <td class="line_tax_code">&nbsp;</td>
                          </tr>
                       % endif

                       % if type_of_line == 'total':
                          <tr>
                            <td class="line_invoice_line_no_padding_left" colspan="7"><b>${_("Total:")} ${"{currency_name}".format(currency_name=currency_name)}</b></td>
                            <td class="line_total_price double_border_top_cell" style="font-weight: bold;">${formatLang(o.amount_total, monetary=True)}</td>
                            <td class="line_tax_code">&nbsp;</td>
                          </tr>
                       % endif

                       % if type_of_line == 'ending_message':
                          <!-- Prints the ending message -->
                          <tr class="low_height"><td colspan="9">&nbsp;</td></tr>
                          <tr>
                            <td class="line_invoice_line_no_padding_left" colspan="9">                            
                                ${o.ending_text(o.type)}
                            </td>
                          </tr>
                          <tr class="low_height"><td colspan="9">&nbsp;</td></tr>
							
                          <!-- Prints an optional comment. -->
	            	      % if o.comment:
    	            	  <tr>
    	            	    <td class="line_invoice_line_no_padding_left" colspan="9">   
        	            	    ${_('Comment')}:</br>
        	            	    ${o.comment}
                		    </td>
                		  </tr>
                	      %endif

                          <!-- Optionally prints an additional message for partial deliveries:
                               If the 'invoice sale order' then only prints the text if the sale order has a back order.
                               If the 'invoice delivery order', then print in in all but the last invoice.
                          -->
                          <% show_text_for_partial_deliveries = sale_ids and ((sale_ids[0].invoice_policy == 'order' and sale_ids[0].has_backorder()) or (sale_ids[0].invoice_policy == 'delivery' and o.is_last_invoice() and sale_ids[0].has_backorder())) %>
	            	      % if show_text_for_partial_deliveries:
    	            	  <tr>
    	            	    <td class="line_invoice_line_no_padding_left" colspan="9">   
        	            	    ${conf_data.invoice_report_text_for_partial_deliveries or ''}    
                		    </td>
                		  </tr>
                	      %endif
                	   % endif

                       % if type_of_line == 'gift_card':
                          <% gift_amount, gift_card_name = content_of_line%>
                          <tr>
                            <td class="line_invoice_line_no_padding_left" colspan="7">${_("Gift-card {gift_card_name}".format(gift_card_name=gift_card_name))}</td>
                            <% num_invoice_line += 1 %>
                            <td class="line_total_price">${gift_amount}</td>
                            <td class="line_tax_code">&nbsp;</td>
                          </tr>
                       % endif

                       % if type_of_line == 'total_minus_gift_cards':
                          <tr>
                            <td class="line_invoice_line_no_padding_left" colspan="7"><b>${_("Total:")} ${"{currency_name}".format(currency_name=currency_name)}</b></td>
                            <td class="line_total_price double_border_top_cell" style="font-weight: bold;">${formatLang(o.residual, monetary=True)}</td>
                            <td class="line_tax_code">&nbsp;</td>
                          </tr>
                       % endif

                       %if type_of_line == 'backorder_products_title':
                          <tr><td colspan="9">&nbsp;</td></tr>
                          <tr>
                              <td class="line_invoice_line_no_padding_left" colspan="9">
                                  <strong>
                                    ${conf_data.invoice_backorder_line_text}
                                  </strong>
                              </td>
                          </tr>
                          <tr><td colspan="9">&nbsp;</td></tr>
                       %endif

                       %if type_of_line == 'backorder_products_heading':
                          <tr>
                            <td class="line_invoice_line shadowed" colspan="2">${_("Product No.")}</td>
                            <!-- <td class="line_product_no shadowed">${_("Description")}</td> -->
                            <td class="line_product_name shadowed" colspan="5">${_("Description")}</td>
                            <!-- <td class="line_lot_no shadowed"></td> -->
                            <!-- <td class="line_quantity shadowed"></td> -->
                            <!-- <td class="line_item_price shadowed"></td> -->
                            <!-- <td class="line_discount shadowed"></td> -->
                            <td class="line_total_price shadowed">${_("Quantity")}</td>
                            <!-- <td class="line_tax_code shadowed">${_("Unit of Measure")}</td> -->
                          </tr>
                       %endif

                       %if type_of_line == 'backorder_products_line':
                          <% product, product_uom_qty, product_uom = content_of_line %>
                          <tr>
                            <td class="line_invoice_line" colspan="2">${product.default_code}</td>
                            <!-- <td class="line_product_no"></td> -->
                            <td class="line_product_name" colspan="5">${product.name}</td>
                            <!-- <td class="line_lot_no"></td> -->
                            <!-- <td class="line_quantity"></td> -->
                            <!-- <td class="line_item_price"></td> -->
                            <!-- <td class="line_discount"></td> -->
                            <td class="line_total_price">${product_uom_qty}</td>
                            <!-- <td class="line_tax_code">${product_uom.name}</td> -->
                          </tr>
                       %endif

                    % endfor
                    </table>
                    <!-- </div> --> <!-- class="invoice_lines" -->

                </div> <!-- END class="mako_document_content" or "mako_document_content_not_first_page" -->

            </div> <!-- class="container_defining_margins" -->

            <div style="clear:both;">

            </div>

            <!-- BVR -->
            <div class="footer_bvr">
            <% has_bank_account = o.partner_bank_id and o.partner_bank_id.get_account_number() or False %>
            <% bvr_amount = o.residual %>
            % if print_bvr(o.type):  # Print the BVR in case that it won't be a refund invoice. Note that maybe it will be filled with X's

                <!-- slip 1 elements -->
                <div class="slip_ref"
                     style="top:${get_top_of_css_class(conf_data, 'esr_slip_ref_top')}mm;
                            right:${conf_data.esr_slip_ref_right}mm;
                            font-size:${conf_data.esr_slip_ref_size}pt;">
                        ${void_if_needed(_space(_get_ref(o)), o)}
                </div>

                <div class="slip_address_b"
                     style="top:${get_top_of_css_class(conf_data, 'esr_slip_address_b_top')}mm;
                            left:${conf_data.esr_slip_address_b_left}mm;
                            font-size:${conf_data.esr_slip_address_b_size}pt;">
                    <table class="slip_add">
                        <% invoice_address = o.partner_id.get_html_full_address('linebreak', separate_salutation=False) %>
                        ${void_if_needed(invoice_address, o)}
                    </table>
                </div>

                <div class="slip_bank_acc"
                     style="top:${get_top_of_css_class(conf_data, 'esr_slip_bank_acc_top')}mm;
                            left:${conf_data.esr_slip_bank_acc_left}mm;
                            font-size:${conf_data.esr_slip_bank_acc_size}pt;">
                    ${void_if_needed(o.partner_bank_id.print_account and o.partner_bank_id.get_account_number(), o)}
                </div>

                <div class="slip_amount"
                     style="top:${get_top_of_css_class(conf_data, 'esr_slip_amount_top')}mm;
                            right:${conf_data.esr_slip_amount_right}mm;
                            font-size:${conf_data.esr_slip_amount_size}pt;">
                    %if not show_blank_instead_of_amount_on_bvr(o):
                       <% ref_start_right_amount = 15 %>
                       <% ref_coef_space_amount = 5 %>
                       %for ii,c in enumerate(('%.2f' % bvr_amount)[:-3][::-1]):
                       <div class="digit_amount" style="right:${ref_start_right_amount + (ii*ref_coef_space_amount)}mm;">${void_if_needed(c, o)}</div>
                       %endfor
                       <!--
                       <span style="padding-right:0mm;">${void_if_needed(_space(('%.2f' % bvr_amount)[:-3], 1), o)}</span>
                       -->
                       &nbsp;
                       <span style="padding-left:1mm;">${void_if_needed(_space(('%.2f' % bvr_amount)[-2:], 1), o)}</span>
                    %endif
                </div>

                %if o.partner_bank_id and o.partner_bank_id.print_bank and o.partner_bank_id.bank:
                <div class="slip_bank"
                     style="top:${get_top_of_css_class(conf_data, 'esr_slip_bank_top')}mm;
                            left:${conf_data.esr_slip_bank_left}mm;
                            font-size:${conf_data.esr_slip_bank_size}pt;">
                    <table class="slip_add">
                        ${void_if_needed(o.partner_bank_id.bank_name, o)} <br/>
                        ${void_if_needed(o.partner_bank_id.bank and o.partner_bank_id.bank.zip, o)}&nbsp;${void_if_needed(o.partner_bank_id.bank and o.partner_bank_id.bank.city, o)}
                    </table>
                </div>
                %endif

                %if o.partner_bank_id.print_partner:
                <div class="slip_comp"
                     style="top:${get_top_of_css_class(conf_data, 'esr_slip_comp_top')}mm;
                            left:${conf_data.esr_slip_comp_left}mm;
                            font-size:${conf_data.esr_slip_comp_size}pt;">
                    <table class="slip_add">
                        <% bank_addr_data = o.partner_bank_id.get_html_full_address('linebreak') %>
                        ${void_if_needed(bank_addr_data, o)}
                    </table>
                </div>
                %endif

                <!-- slip 2 elements -->
                <div class="slip2_ref"
                     style="top:${get_top_of_css_class(conf_data, 'esr_slip2_ref_top')}mm;
                            right:${conf_data.esr_slip2_ref_right}mm;
                            font-size:${conf_data.esr_slip2_ref_size}pt;">
                        ${void_if_needed(_space(_get_ref(o)), o)}
                </div>
                <div class="slip2_amount"
                     style="top:${get_top_of_css_class(conf_data, 'esr_slip2_amount_top')}mm;
                            right:${conf_data.esr_slip2_amount_right}mm;
                            font-size:${conf_data.esr_slip2_amount_size}pt;">
                    %if not show_blank_instead_of_amount_on_bvr(o):
                       <% ref_start_right_amount2 = 15 %>
                       <% ref_coef_space_amount2 = 5 %>
                       %for ii,c in enumerate(('%.2f' % bvr_amount)[:-3][::-1]):
                       <div class="digit_amount" style="right:${ref_start_right_amount2 + (ii*ref_coef_space_amount2)}mm;">${void_if_needed(c, o)}</div>
                       %endfor
                       <!--
                       <span style="padding-right:0mm;">${void_if_needed(_space(('%.2f' % bvr_amount)[:-3], 1), o)}</span>
                        -->
                       &nbsp;
                       <span style="padding-left:1mm;">${void_if_needed(_space(('%.2f' % bvr_amount)[-2:], 1), o)}</span>
                    %endif
                </div>
                <div class="slip2_address_b"
                     style="top:${get_top_of_css_class(conf_data, 'esr_slip2_address_b_top')}mm;
                            left:${conf_data.esr_slip2_address_b_left}mm;
                            font-size:${conf_data.esr_slip2_address_b_size}pt;">
                    <table class="slip_add">
                        <% invoice_address = o.partner_id.get_html_full_address('linebreak', separate_salutation=False) %>
                        ${void_if_needed(invoice_address, o)}
                    </table>
                </div>

                %if o.partner_bank_id and o.partner_bank_id.print_bank and o.partner_bank_id.bank:
                <div class="slip2_bank"
                     style="top:${get_top_of_css_class(conf_data, 'esr_slip2_bank_top')}mm;
                            left:${conf_data.esr_slip2_bank_left}mm;
                            font-size:${conf_data.esr_slip2_bank_size}pt;">
                    <table class="slip_add">
                        ${void_if_needed(o.partner_bank_id.bank_name, o)} <br/>
                        ${void_if_needed(o.partner_bank_id.bank and o.partner_bank_id.bank.zip, o)}&nbsp;${void_if_needed(o.partner_bank_id.bank and o.partner_bank_id.bank.city, o)}
                    </table>
                </div>
                %endif

                %if o.partner_bank_id.print_partner:
                <div class="slip2_comp"
                     style="top:${get_top_of_css_class(conf_data, 'esr_slip2_comp_top')}mm;
                            left:${conf_data.esr_slip2_comp_left}mm;
                            font-size:${conf_data.esr_slip2_comp_size}pt;">
                    <table class="slip_add">
                        <% bank_addr_data = o.partner_bank_id.get_html_full_address('linebreak') %>
                        ${void_if_needed(bank_addr_data, o)}
                    </table>
                </div>
                %endif

                <div class="slip2_bank_acc"
                     style="top:${get_top_of_css_class(conf_data, 'esr_slip2_bank_acc_top')}mm;
                            left:${conf_data.esr_slip2_bank_acc_left}mm;
                            font-size:${conf_data.esr_slip2_bank_acc_size}pt;">
                    ${void_if_needed(o.partner_bank_id.print_account and o.partner_bank_id.get_account_number(), o)}
                </div>

                <!--- scaner code bar -->
                <div class="ocrbb"
                     style="top:${get_top_of_css_class(conf_data, 'esr_ocrbb_top')}mm;
                            left:${conf_data.esr_ocrbb_left}mm;
                            font-size:${conf_data.esr_ocrbb_size}pt;">
                %if not show_blank_instead_of_amount_on_bvr(o):
                   <% ref_start_left = conf_data.esr_ocrbb_digitref_start %>
                   <% ref_coef_space = conf_data.esr_ocrbb_digitref_coefficient %>
                   <% tt = [ v for v in mod10r('01'+str('%.2f' % bvr_amount).replace('.','').rjust(10,'0')) ] %>
                   <% tt.append('&gt;') %>
                   <% tt += [v for v in _get_ref(o)] %>
                   <% tt.append('+') %>
                   <% tt.append('&nbsp;') %>
                   % if has_bank_account:
                     % if o.partner_bank_id.state == 'iban':
                        <% tt += [v for v in o.partner_bank_id.get_account_number() ] %>
                     %else:
                        <% tt += [v for v in o.partner_bank_id.get_account_number().split('-')[0]+(str(o.partner_bank_id.get_account_number().split('-')[1])).rjust(6,'0')+o.partner_bank_id.get_account_number().split('-')[2]] %>
                     % endif
                   % else:
                     <% tt = [0] * 50 %>
                   % endif
                   <% tt.append('&gt;') %>

                   %for ii,c in enumerate(tt) :
                       <div class="digitref"  style="left:${ref_start_left + (ii*ref_coef_space)}mm;">${void_if_needed(c, o, True)}</div>
                   %endfor
                %endif
                </div> <!-- END class="ocrbb" -->

            % endif
            </div> <!-- END class="footer_bvr" -->

           <% increment_page_num() %>
          % endwhile
        % endfor
        <!-- <div style="page-break-inside: avoid;"></div> -->
    </body>
</html>
