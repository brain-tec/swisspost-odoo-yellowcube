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
         <% num_lines_per_page_first = conf_data.invoice_pf_report_num_lines_per_page_first or 9 %>
         <% num_lines_per_page_not_first = conf_data.invoice_pf_report_num_lines_per_page_not_first or 20 %>
         <% page_lines = assign_lines_to_pages(o.invoice_line, num_lines_per_page_first, num_lines_per_page_not_first) %>

         <% total_pages = len(page_lines) %>
         <% subtotal_amount_with_taxes = 0.0 %>
         
         <% num_invoice_line = 1 %>
          % while get_page_num() < total_pages:
        
           <div class="container_defining_margins">

            <div class="report_pseudo_header">
                <div class="report_header_logo" style="top: ${conf_data.invoice_pf_logo_top}mm">
                    ${o.get_logo(conf_data.invoice_pf_logo, width=conf_data.invoice_pf_logo_max_width)}
                </div>
            </div>

            % if is_first_page():
            <div class="intro_info">
                <div class="intro_info_info">
                    <div class="airy_element"><span><strong>${o.company_id.name}</strong></span><span>&nbsp;</span></div>
                    <div class="airy_element"><span><strong>${o.company_id.street} ${o.company_id.street_no}</strong></span><span>&nbsp;</span></div>
                    <div class="airy_element"><span><strong>${o.company_id.zip} ${o.company_id.city}</strong></span><span>&nbsp;</span></div>

                    <div class="airy_element"><span>&nbsp;</span><span>&nbsp;</span></div>

                    <div class="airy_element"><span>${_("Phone")} ${o.company_id.partner_id.phone or ''}</span><span> </span></div>
                    <div class="airy_element"><span>${o.company_id.partner_id.email or ''}</span><span> </span></div>
                    <div class="airy_element"><span>${clean_url(o.company_id.partner_id.website or '')}</span><span> </span></div>

                    <div class="airy_element"><span>&nbsp;</span><span>&nbsp;</span></div>

                    <div class="airy_element"><span>${_("Policy No.")}</span><span>${o.origin or ''}</span></div>
                    <div class="airy_element"><span>${_("Invoice date")}</span><span>${formatLang(o.date_invoice or '', date=True)}</span></div>
                    <div class="airy_element"><span>${_("Invoice number")}</span><span>${o.name or ''}</span></div>
                    <div class="airy_element"><span>${_("To be paid until")}</span>
                        <span>
                            % if o.state == 'paid':
                            ${_('This invoice has already been paid')}
                            % else:
                            ${formatLang(o.date_due or '', date=True)}
                            % endif
                        </span>
                    </div>
                </div>

                <% address_fields = o.get_address_fields() %>
                <div class="address_window">
                    <div class="addr_head">
                        <div class="addr_head_left">
                            <div class="addr_head_left_frankingmark">P.P.</div>
                            <div class="addr_head_left_postcode">
                            ${conf_data.invoice_pf_franking_country_code or ''} - ${conf_data.invoice_pf_franking_zip or ''} <span class="linebreak" />
                            ${conf_data.invoice_pf_franking_town or ''}
                            </div>
                        </div>
                        <div class="addr_head_right">
                            <div class="addr_head_right_processing">
                                B-ECONOMY
                            </div>
                            <div class="addr_head_right_logo_and_invoice_number">
                                Post CH AG <span class="linebreak" />
                                ${conf_data.invoice_pf_postmail_rrn or ''}
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
                            ${o.get_logo(conf_data.invoice_pf_qr)}
                        </div>
                    </div>
                </div>

            </div><!-- <div class="intro_info"> -->

            <div style="clear:both;"></div>

            % else:
            <div class="intro_info_not_first_page"></div>
            % endif

            <% invoice_lines = page_lines[get_page_num()] %>

            % if is_first_page():
                <div class="mako_document_title">
                    ${o.title1 or ''} <br/>
                    ${o.title2 or ''} <br/>
                    ${o.title3 or ''}
                </div>

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
                            <td class="line_invoice_pf_description shadowed">
                                ${_("Description")}
                            </td>
                            <td class="line_invoice_pf_period_price shadowed">
                                ${_("Price for a year")}<br/>
                                ${_("in")} ${currency_name}
                            </td>
                            <td class="line_invoice_pf_yearly_price shadowed">
                                ${_("Price for the mentioned period")}<br/>
                                ${_("in")} ${currency_name}
                            </td>
                          </tr>
                       % endif

                       % if type_of_line == 'regular_line':
                          <tr>
                            <td class="line_invoice_pf_description">
                                ${content_of_line.product_id.name or ''}
                            </td>
                            <td class="line_invoice_pf_period_price">
                                ${formatLang(content_of_line.price_unit, monetary=True)}
                            </td>
                            <td class="line_invoice_pf_yearly_price">
                                ${formatLang(content_of_line.quantity * content_of_line.price_unit, monetary=True)}
                            </td>
                          </tr>
                       % endif

                       % if type_of_line == 'blank_line':
                          <tr class="low_height"><td colspan="3">&nbsp;</td></tr>
                       % endif

                       % if type_of_line == 'total':
                          <tr>
                            <td class="line_invoice_pf_description no_padding_left double_border_top_cell double_border_bottom_cell" colspan="2">
                                <b>${_("Total in our favour")}</b>
                            </td>
                            <td class="line_invoice_pf_yearly_price double_border_top_cell double_border_bottom_cell" style="font-weight: bold;">
                                ${formatLang(o.amount_total, monetary=True)}
                            </td>
                          </tr>
                       % endif

                       % if type_of_line == 'ending_message':
                          <!-- Prints the ending message. -->
                          <tr class="low_height"><td colspan="3">&nbsp;</td></tr>
                          <tr>
                            <td class="line_invoice_pf_description no_padding_left" colspan="3">
                                ${split_into_html_lines(conf_data.invoice_pf_ending_text)}
                            </td>
                          </tr>
                          <tr class="low_height"><td colspan="3">&nbsp;</td></tr>
							
                          <!-- Prints an optional comment. -->
	            	      % if o.comment:
    	            	  <tr>
    	            	    <td class="line_invoice_pf_description no_padding_left" colspan="3">
        	            	    ${o.comment}
                		    </td>
                		  </tr>
                	      %endif

                	   % endif

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
                     <% tt += [v for v in o.partner_bank_id.get_account_number().split('-')[0]+(str(o.partner_bank_id.get_account_number().split('-')[1])).rjust(6,'0')+o.partner_bank_id.get_account_number().split('-')[2]] %>
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
