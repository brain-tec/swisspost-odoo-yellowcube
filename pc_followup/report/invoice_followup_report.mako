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
         <% date_today = get_date_today() %>

         <% setLang(o.partner_id.lang) %>
         <!-- Collect data -->

           <div class="container_defining_margins">

           <div class="report_pseudo_header">
                <div class="report_header_logo">
                    ${o.get_logo(conf_data.followup_logo)}
                </div>
                <div class="report_header_address">
                    ${o.company_id.partner_id.name or ''} <span class="linebreak" />
                    <% partner_addr_data = o.get_company_address('linebreak') %>
                    ${partner_addr_data or ''}
                </div>
                <div class="report_header_pagenumber">
                    ${_('Page')}: 1 / 1
                </div>
            </div>

            <div class="horizontal_line_black"></div>

            <div class="intro_info">
                <div class="intro_info_info">
                    <div class="airy_element"><span>${_("Phone")}</span><span>${o.company_id.partner_id.phone or ''}</span></div>
                    <div class="airy_element"><span>${_("E-Mail")}</span><span>${o.company_id.partner_id.email or ''}</span></div>
                    <div class="airy_element"><span>${_("Web")}</span><span>${o.company_id.partner_id.website or ''}</span></div>
                    <div class="airy_element"><span>${_("Tax number")}</span><span>${o.company_id.vat or ''}</span></div>
                    <div class="airy_element"><span>&nbsp;</span><span>&nbsp;</span></div>
                    
                    <div class="airy_element"><span>${_("Customer number")}</span><span>${o.partner_id.get_ref() or ''}</span></div>
                    <div class="airy_element"><span>${_("Invoice date")}</span><span>${formatLang(o.date_invoice or '', date=True)}</span></div>
                    <div class="airy_element"><span>${_("Invoice number")}</span><span>${o.number or ''}</span></div>
                    <div class="airy_element"><span>${_("Reminder date")}</span><span>${formatLang(date_today or '', date=True)}</span></div>
                    <div class="airy_element"><span>&nbsp;</span></div>
                    <div class="airy_element"><span>&nbsp;</span></div>
                    <div class="airy_element"><span>&nbsp;</span></div>
                </div>

                <% address_fields = o.get_address_fields() %>
                <div class="address_window">
                    <div class="addr_head">
                        <div class="addr_head_left">
                            <div class="addr_head_left_frankingmark">P.P.</div>
                            <div class="addr_head_left_postcode">
                            ${conf_data.followup_franking_country_code or ''} - ${conf_data.followup_franking_zip or ''} <span class="linebreak" />
                            ${conf_data.followup_franking_town or ''}
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
                                ${conf_data.followup_postmail_rrn or ''}
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
                            ${o.get_logo(conf_data.invoice_qr)}
                        </div>
                    </div>
                </div><!-- <div class="address_window"> -->

            </div> 

            <div style="clear:both;"></div>
            <div class="inline_delivery_address">
                %if o.sale_ids:
                    <u>${_('Delivery Address')}</u><span class="linebreak" />
                    <% delivery_address = o.sale_ids[0].partner_shipping_id.get_html_full_address() %>
                    ${delivery_address}
                %endif
            </div>

            <!-- <div style="clear:both;"></div> -->

            <div class="mako_document_title">
                <span style="text-transform: uppercase;">${get_followup_title(o, {'lang': o.partner_id.lang})}</span>
                <span>&nbsp;</span>
            </div>

            <div class="mako_document_content">
                    <table style="width:100%;" class="print_friendly">
                        <tr>
                            <td class="followup_line_invoice_line shadowed">${_("Pos.")}</td>
                            <td class="followup_line_document_number shadowed">${_("Justifying")}</td>
                            <td class="followup_line_date shadowed">${_("Date")}</td>
                            <td class="followup_line_due_date shadowed">${_("Due date")}</td>
                            <td class="followup_line_invoice_text shadowed">${_("Justifying document")}</td>
                            <td class="followup_line_overdue_fines shadowed">${_("Overdue fee")}</td>
                            <td class="followup_line_total_amount shadowed">${_("Amount")} ${currency_name}</td>
                        </tr>

                        <!-- Line with the amount to be paid. -->
                        <% num_invoice_line = 1 %>
                        <tr>
                            <td class="followup_line_invoice_line">${num_invoice_line}</td>
                            <td class="followup_line_document_number">${o.number or ''}</td>
                            <td class="followup_line_date">${formatLang(o.date_invoice or '', date=True)}</td>
                            <td class="followup_line_due_date">${formatLang(o.date_due or '', date=True)}</td>
                            <td class="followup_line_invoice_text">${_('Invoice')}</td>
                            <% penalization_total = 0.00 %>
                            % for penalization_invoice in o.followup_penalization_invoice_ids:
                               <% penalization_total += penalization_invoice.amount_total %>
                            % endfor
                            <td class="followup_line_overdue_fines">${formatLang(penalization_total, monetary=True)}</td>
                            <td class="followup_line_total_amount">${formatLang(o.residual, monetary=True)}</td>
                        </tr>

                        <!-- Displays the net amount (excluding taxes) -->
                        <% total_amount_to_pay = o.residual + penalization_total %>
                        <tr>
                            <td class="followup_line_invoice_line" colspan="4">&nbsp;</td>
                            <td class="followup_line_invoice_text" style="font-weight: bold;" colspan="2">Total</td>
                            <td class="followup_line_total_amount double_border_top_cell" style="font-weight: bold;">${formatLang(total_amount_to_pay, monetary=True)}</td>
                        </tr>

                        <!-- Prints the ending message -->
                        <tr><td colspan="7">&nbsp;</td></tr>
                        <tr><td colspan="7">&nbsp;</td></tr>
                        <tr>
                            <td class="followup_line_invoice_line" colspan="7">
                                <% followup_description = o.followup_level_id and o.followup_level_id.description %>
                                % if followup_description:
                                    ${o.followup_level_id.get_followup_text_with_wildcards(o.id, followup_description)}
                                % else:
                                    &nbsp;
                                % endif
                            </td>
                        </tr>

                    </table>
            </div> <!-- END class="mako_document_content" -->

            </div> <!-- class="container_defining_margins" -->

            <div style="clear:both;"></div>

            <!-- BVR -->
            <div class="footer_bvr">
            <%
            bvr_bank_account = o.partner_bank_id or False
            if bvr_bank_account:
                if bvr_bank_account.state == 'bvr':
                    bvr_bank_account = o.partner_bank_id.get_account_number()
                else:
                    bvr_bank_account = o.partner_bank_id.ccp or False
            %>
            % if True:  # Print the BVR always, but maybe filled with X's

                <!-- slip 1 elements -->
                <div class="slip_ref"
                     style="top:${conf_data.esr_slip_ref_top}mm;
                            right:${conf_data.esr_slip_ref_right}mm;
                            font-size:${conf_data.esr_slip_ref_size}pt;">
                        ${_space(_get_ref(o))}
                </div>

                <div class="slip_address_b"
                     style="top:${conf_data.esr_slip_address_b_top}mm;
                            left:${conf_data.esr_slip_address_b_left}mm;
                            font-size:${conf_data.esr_slip_address_b_size}pt;">
                    <table class="slip_add">
                        <% delivery_address = o.partner_id.get_html_full_address('linebreak', separate_salutation=True) %>
                        ${delivery_address}
                    </table>
                </div>

                <div class="slip_bank_acc"
                     style="top:${conf_data.esr_slip_bank_acc_top}mm;
                            left:${conf_data.esr_slip_bank_acc_left}mm;
                            font-size:${conf_data.esr_slip_bank_acc_size}pt;">
                    ${o.partner_bank_id.print_account and bvr_bank_account or ''}
                </div>

                <div class="slip_amount"
                     style="top:${conf_data.esr_slip_amount_top}mm;
                            right:${conf_data.esr_slip_amount_right}mm;
                            font-size:${conf_data.esr_slip_amount_size}pt;">
                    <% ref_start_right_amount = 15 %>
                    <% ref_coef_space_amount = 5 %>
                    %for ii,c in enumerate(('%.2f' % total_amount_to_pay)[:-3][::-1]):
                    <div class="digit_amount" style="right:${ref_start_right_amount + (ii*ref_coef_space_amount)}mm;">${c}</div>
                    %endfor
                    <!--
                    <span style="padding-right:0mm;">${_space(('%.2f' % total_amount_to_pay)[:-3], 1)}</span>
                    -->
                    &nbsp;
                    <span style="padding-left:1mm;">${_space(('%.2f' % total_amount_to_pay)[-2:], 1)}</span>
                </div>

                %if o.partner_bank_id and o.partner_bank_id.print_bank and o.partner_bank_id.bank:
                <div class="slip_bank"
                     style="top:${conf_data.esr_slip_bank_top}mm;
                            left:${conf_data.esr_slip_bank_left}mm;
                            font-size:${conf_data.esr_slip_bank_size}pt;">
                    <table class="slip_add">
                        ${o.partner_bank_id.bank_name or ''} <br/>
                        ${o.partner_bank_id.bank and o.partner_bank_id.bank.zip or ''}&nbsp;${o.partner_bank_id.bank and o.partner_bank_id.bank.city or ''}
                    </table>
                </div>
                %endif

                %if o.partner_bank_id.print_partner:
                <div class="slip_comp"
                     style="top:${conf_data.esr_slip_comp_top}mm;
                            left:${conf_data.esr_slip_comp_left}mm;
                            font-size:${conf_data.esr_slip_comp_size}pt;">
                    <table class="slip_add">
                        <% bank_addr_data = o.partner_bank_id.get_html_full_address('linebreak') %>
                        ${bank_addr_data}
                    </table>
                </div>
                %endif

                <!-- slip 2 elements -->
                <div class="slip2_ref"
                     style="top:${conf_data.esr_slip2_ref_top}mm;
                            right:${conf_data.esr_slip2_ref_right}mm;
                            font-size:${conf_data.esr_slip2_ref_size}pt;">
                        ${_space(_get_ref(o))}
                </div>
                <div class="slip2_amount"
                     style="top:${conf_data.esr_slip2_amount_top}mm;
                            right:${conf_data.esr_slip2_amount_right}mm;
                            font-size:${conf_data.esr_slip2_amount_size}pt;">
                    <% ref_start_right_amount2 = 15 %>
                    <% ref_coef_space_amount2 = 5 %>
                    %for ii,c in enumerate(('%.2f' % total_amount_to_pay)[:-3][::-1]):
                    <div class="digit_amount" style="right:${ref_start_right_amount2 + (ii*ref_coef_space_amount2)}mm;">${c}</div>
                    %endfor
                    <!--
                    <span style="padding-right:0mm;">${_space(('%.2f' % total_amount_to_pay)[:-3], 1)}</span>
                    -->
                    &nbsp;
                    <span style="padding-left:1mm;">${_space(('%.2f' % total_amount_to_pay)[-2:], 1)}</span>
                </div>
                <div class="slip2_address_b"
                     style="top:${conf_data.esr_slip2_address_b_top}mm;
                            left:${conf_data.esr_slip2_address_b_left}mm;
                            font-size:${conf_data.esr_slip2_address_b_size}pt;">
                    <table class="slip_add">
                        <% delivery_address = o.partner_id.get_html_full_address('linebreak', separate_salutation=True) %>
                        ${delivery_address}
                    </table>
                </div>

                %if o.partner_bank_id and o.partner_bank_id.print_bank and o.partner_bank_id.bank:
                <div class="slip2_bank"
                     style="top:${conf_data.esr_slip2_bank_top}mm;
                            left:${conf_data.esr_slip2_bank_left}mm;
                            font-size:${conf_data.esr_slip2_bank_size}pt;">
                    <table class="slip_add">
                        ${o.partner_bank_id.bank_name or ''} <br/>
                        ${o.partner_bank_id.bank and o.partner_bank_id.bank.zip or ''}&nbsp;${o.partner_bank_id.bank and o.partner_bank_id.bank.city or ''}
                    </table>
                </div>
                %endif

                %if o.partner_bank_id.print_partner:
                <div class="slip2_comp"
                     style="top:${conf_data.esr_slip2_comp_top}mm;
                            left:${conf_data.esr_slip2_comp_left}mm;
                            font-size:${conf_data.esr_slip2_comp_size}pt;">
                    <table class="slip_add">
                        <% bank_addr_data = o.partner_bank_id.get_html_full_address('linebreak') %>
                        ${bank_addr_data}
                    </table>
                </div>
                %endif

                <div class="slip2_bank_acc"
                     style="top:${conf_data.esr_slip2_bank_acc_top}mm;
                            left:${conf_data.esr_slip2_bank_acc_left}mm;
                            font-size:${conf_data.esr_slip2_bank_acc_size}pt;">
                    ${o.partner_bank_id.print_account and bvr_bank_account or ''}
                </div>

                <!--- scaner code bar -->
                <div class="ocrbb"
                     style="top:${conf_data.esr_ocrbb_top}mm;
                            left:${conf_data.esr_ocrbb_left}mm;
                            font-size:${conf_data.esr_ocrbb_size}pt;">
                <% ref_start_left = conf_data.esr_ocrbb_digitref_start %>
                <% ref_coef_space = conf_data.esr_ocrbb_digitref_coefficient %>
                <% tt = [ v for v in mod10r('01'+str('%.2f' % total_amount_to_pay).replace('.','').rjust(10,'0')) ] %>
                <% tt.append('&gt;') %>
                <% tt += [v for v in _get_ref(o)] %>
                <% tt.append('+') %>
                <% tt.append('&nbsp;') %>
                % if bvr_bank_account:
                  <%
                  bvr_parts = bvr_bank_account.split('-')
                  if len(bvr_parts) != 3:
                      raise Exception("Bad BVR: {0}".format(bvr_bank_account))
                  tt += [v for v in bvr_parts[0]+(str(bvr_parts[1])).rjust(6,'0')+bvr_parts[2]]
                  %>
                % else:
                  <% raise Exception("Missing BVR") %>
                % endif
                <% tt.append('&gt;') %>

                %for ii,c in enumerate(tt) :
                    <div class="digitref"  style="left:${ref_start_left + (ii*ref_coef_space)}mm;">${c}</div>
                %endfor
                </div> <!-- END class="ocrbb" -->

            % endif
            </div> <!-- END class="footer_bvr" -->

        % endfor
        <!-- <div style="page-break-inside: avoid;"></div> -->
    </body>
</html>
