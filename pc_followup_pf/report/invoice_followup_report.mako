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

        <div class="container_defining_margins">

            <div class="report_pseudo_header">
                <div class="report_header_logo" style="top: ${conf_data.invoice_pf_logo_top}mm">
                    ${o.get_logo(conf_data.invoice_pf_logo, width=conf_data.invoice_pf_logo_max_width)}
                </div>
            </div>

            <div class="intro_info">
                <div class="intro_info_info">
                    <div class="airy_element">
                        <span><strong>${o.company_id.name}</strong></span><span>&nbsp;</span>
                    </div>
                    <div class="airy_element">
                        <span><strong>${o.company_id.street} ${o.company_id.street_no}</strong></span><span>&nbsp;</span>
                    </div>
                    <div class="airy_element">
                        <span><strong>${o.company_id.zip} ${o.company_id.city}</strong></span><span>&nbsp;</span>
                    </div>

                    <div class="airy_element">
                        <span>&nbsp;</span><span>&nbsp;</span>
                    </div>

                    <div class="airy_element">
                        <span>${_("Phone")} ${o.company_id.partner_id.phone or ''}</span><span> </span>
                    </div>
                    <div class="airy_element">
                        <span>${o.company_id.partner_id.email or ''}</span><span> </span>
                    </div>
                    <div class="airy_element">
                        <span>${clean_url(o.company_id.partner_id.website or '')}</span><span> </span>
                    </div>

                    <div class="airy_element">
                        <span>&nbsp;</span><span>&nbsp;</span>
                    </div>
                    <div class="airy_element">
                        <span>${_("Policy No.")}</span><span>${o.origin or ''}</span></div>
                    <div class="airy_element">
                        <span>${_("Invoice date")}</span><span>${formatLang(o.date_invoice or '', date=True)}</span>
                    </div>
                    <div class="airy_element">
                        <span>${_("Invoice number")}</span><span>${o.name or ''}</span>
                    </div>
                    <div class="airy_element">
                        <span>${_("Dunning date")}</span><span>${o.followup_level_date or ''}</span>
                    </div>
                    <div class="airy_element">
                        <span>${_("To be paid until")}</span>
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
                    % if o.followup_level_id.use_barcode_address:
                        <% barcode_base64, barcode_format = o.get_barcode_for_report(context={'lang': o.partner_id.lang}) %>
                        <img style="border: 1px solid black; padding: 1px; width: 80mm; height: 45mm;"
                             src="data:image/${barcode_format};base64,${barcode_base64}" />
                    % else:
                    <div class="addr_head">
                        <div class="addr_head_left">
                            <div class="addr_head_left_frankingmark">P.P.</div>
                            <div class="addr_head_left_postcode">
                                ${conf_data.invoice_pf_franking_country_code or ''}
                                - ${conf_data.invoice_pf_franking_zip or ''}
                                <span class="linebreak"/>
                                ${conf_data.invoice_pf_franking_town or ''}
                            </div>
                        </div>
                        <div class="addr_head_right">
                            <div class="addr_head_right_processing">
                                B-ECONOMY
                            </div>
                            <div class="addr_head_right_logo_and_invoice_number">
                                Post CH AG <span class="linebreak"/>
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
                    % endif
                </div>

            </div><!-- <div class="intro_info"> -->

            <div style="clear:both;"></div>

            <div class="mako_document_title">
                ${o.followup_level_id.name or ''} <br/>

                <% followup_title = o.followup_level_id and o.followup_level_id.letter_title%>
                % if followup_title:
                    ${o.followup_level_id.get_followup_text_with_wildcards(o.id, split_into_html_lines(followup_title))}
                % else:
                    &nbsp;
                % endif

            </div>

            <div class="mako_document_content">

                <table style="width:100%;" class="print_friendly">

                    <!-- Heading of the table. -->
                    <tr>
                        <td class="line_followup_description shadowed">${_("Description")}</td>
                        <td class="line_followup_price_full shadowed">
                            ${_("Total amount")} <br/>
                            ${_("in")} ${currency_name}
                        </td>
                        <td class="line_followup_price_pending shadowed">
                            ${_("Pending amount")} <br/>
                            ${_("in")} ${currency_name}
                        </td>
                    </tr>

                    <!-- Information regarding the pending invoice. -->
                    <tr>
                        <td class="line_followup_description">
                            ${_('Invoice from ')} ${formatLang(o.date_invoice, date=True)} ${_(' with due date ')} ${formatLang(o.date_due, date=True)}
                        </td>
                        <td class="line_followup_price_full">
                            ${o.amount_total}
                        </td>
                        <td class="line_followup_price_pending">
                            ${o.residual}
                            <% total_amount = o.residual %>
                        </td>
                    </tr>

                    <!-- Information regarding the dunning fee, if any. -->
                    % if o.followup_level_id.product_id:
                        <tr>
                            <td class="line_followup_description">
                                ${_('Overdue fines')}
                            </td>
                            <td class="line_followup_price_full">
                                &nbsp;
                            </td>
                            <td class="line_followup_price_pending">
                                <% dunning_fee = o.followup_level_id.product_id.list_price %>
                            <% total_amount += dunning_fee %>
                            ${dunning_fee}
                            </td>
                        </tr>
                    % endif

                    <!-- Prints the "Total" line. -->
                    <tr>
                        <td colspan="2" class="line_followup_description double_border_top_cell double_border_bottom_cell">
                            <b>${_("Total in our favour")}</b>
                        </td>
                        <td class="line_followup_price_pending double_border_top_cell double_border_bottom_cell"
                            style="font-weight: bold;">
                            ${formatLang(total_amount, monetary=True)}
                        </td>
                    </tr>

                    <!-- Prints the body of the letter. -->
                    <tr class="low_height">
                        <td colspan="3">&nbsp;</td>
                    </tr>
                    <tr>
                        <td class="line_followup_description" colspan="3">
                            <% followup_description = o.followup_level_id and o.followup_level_id.description %>
                            % if followup_description:
                                ${o.followup_level_id.get_followup_text_with_wildcards(o.id, split_into_html_lines(followup_description))}
                            % else:
                                &nbsp;
                            % endif
                        </td>
                    </tr>
                    <tr class="low_height">
                        <td colspan="3">&nbsp;</td>
                    </tr>

                </table>

            </div>
        </div>

        <div style="clear:both;">

        </div>

        <!-- BVR -->
        <div class="footer_bvr">
            <% has_bank_account = o.partner_bank_id and o.partner_bank_id.get_account_number() or False %>
            <% bvr_amount = total_amount %>
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
                        <div class="digit_amount"
                             style="right:${ref_start_right_amount + (ii*ref_coef_space_amount)}mm;">${void_if_needed(c, o)}</div>
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
                        ${void_if_needed(o.partner_bank_id.bank and o.partner_bank_id.bank.zip, o)}
                        &nbsp;${void_if_needed(o.partner_bank_id.bank and o.partner_bank_id.bank.city, o)}
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
                        <div class="digit_amount"
                             style="right:${ref_start_right_amount2 + (ii*ref_coef_space_amount2)}mm;">${void_if_needed(c, o)}</div>
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
                        ${void_if_needed(o.partner_bank_id.bank and o.partner_bank_id.bank.zip, o)}
                        &nbsp;${void_if_needed(o.partner_bank_id.bank and o.partner_bank_id.bank.city, o)}
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
                            <div class="digitref"
                                 style="left:${ref_start_left + (ii*ref_coef_space)}mm;">${void_if_needed(c, o, True)}</div>
                        %endfor
                    %endif
                </div> <!-- END class="ocrbb" -->

            % endif
        </div> <!-- END class="footer_bvr" -->

    % endfor
<!-- <div style="page-break-inside: avoid;"></div> -->
</body>
</html>
