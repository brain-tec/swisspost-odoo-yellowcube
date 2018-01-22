<html>
	<head>
		<style type="text/css">
			${css}
		</style>
	</head>
	<body>
	
	<% grouped_invoices = get_grouped_invoices(objects) %>
	% if len(grouped_invoices) > 0:
		%for partner_invoices in grouped_invoices:
			%for level_invoices in  partner_invoices:
				<% setLang(level_invoices[0]['lang']) %>
				<% partner_invoice_addr_data = get_partner_invoice_address_data(cr, uid, level_invoices[0]['partner_id'])%>
				<% partner_addr_data = get_partner_invoice_address_data(cr, uid, level_invoices[0]['company_id'])%>

		<div>
			<div class="report_rest_header">
                <div class="report_rest_header_2">
                    <div class="report_rest_header_2_1">
                     	<!--  Partner address table-->
                        <table>
                            <tr>
                                <td class="report_rest_header_td">${partner_addr_data['name'] or ''}</td>
                            </tr>
                            <tr>
                                <td class="report_rest_header_td">${partner_addr_data['street'] or ''}</td>
                            </tr>
                            <tr>
                                <td class="report_rest_header_td">${partner_addr_data['street2'] or ''}</td>
                            </tr>
                            <tr>
                                <td class="report_rest_header_td">
                                    ${partner_addr_data['country_code'] or ''}-${partner_addr_data['zip'] or ''}&nbsp;${partner_addr_data['city'] or ''} 
                                </td>
                            </tr>
                            <tr>
                                <td class="report_rest_header_td">${partner_addr_data['country_name'] or ''}</td>
                            </tr>
                        </table>
                    </div>
                    <div class="report_rest_header_2_2">
                        <!--  Invoice address table-->
                        <table>
                            <tr>
                                <td class="report_rest_header_td">${partner_invoice_addr_data['name'] or ''}</td>
                            </tr>
                            <tr>
                                <td class="report_rest_header_td">${partner_invoice_addr_data['street'] or ''}</td>
                            </tr>
                            <tr>
                                <td class="report_rest_header_td">${partner_invoice_addr_data['street2'] or ''}</td>
                            </tr>
                            <tr>
                                <td class="report_rest_header_td">
                                    ${partner_invoice_addr_data['country_code'] or ''}-${partner_invoice_addr_data['zip'] or ''}&nbsp;${partner_invoice_addr_data['city'] or ''} 
                                </td>
                            </tr>
                            <tr>
                                <td class="report_rest_header_td">${partner_invoice_addr_data['country_name'] or ''}</td>
                            </tr>
                        </table>
                    </div>
                </div> <!-- END report_rest_header_2 -->
            
                <div style="clear:both;"></div>
                <div class="report_rest_header_3">
                    <div class="report_rest_header_3_1">
                        <table>
                            <tr>
                                <td class="report_rest_header_td_small" style="width:20mm;">${_("Date")}:</td>
                                <td class="report_rest_header_td_small">${ formatLang( current_date, date=True)}</td>
                            </tr>
                            <!-- 
                            <tr>
                                <td class="report_rest_header_td_small">${_("Our Ref.")}:</td>
                                <td class="report_rest_header_td_small">${ level_invoices[0]['followup_responsible']}</td>
                            </tr>
                            <tr>
                                <td class="report_rest_header_td_small">${_("Email")}:</td>
                                <td class="report_rest_header_td_small">${ level_invoices[0]['followup_responsible_email']}</td>
                            </tr>
                             -->
                        </table>
                    </div>
                    <div class="report_rest_header_3_2">
                        <table>
                            <tr>
                                <td class="report_rest_header_td_small">&nbsp;</td>
                                <td class="report_rest_header_td_small">&nbsp;</td>
                            </tr>
                        </table>
                    </div>
                </div> <!-- END report_rest_header_3 -->
           
                <!-- 
                <div style="clear:both;"></div>
       			<div style="margin-top:15mm;margin-bottom:5mm;">
                    <table style="width:17cm;">
                        <tr>
                            <td style="text-align:left; font-size:10pt; width:12cm; font-weight:bold;">${_("Document")}: ${_("Customer account statement")}</td>
                        </tr>
                    </table>
                </div>
             </div>
              -->
            <div style="clear:both;"></div>
            <div style="width: 17cm;margin-top:15mm;">
            	${ format(get_followup_level_text(cr, uid,  level_invoices[0]['invoice_id'], level_invoices[0]['lang']))}
            </div>
            <div style="clear:both;"></div>
            
            <div class="report_data_header" style="margin-top:5mm;">
                <table style="width: 17cm;">
                    <tr>
                        <td class="report_data_hline" style="width: 25mm;" >${_("Invoice No.")}</td>
                        <td class="report_data_hline" style="width: 25mm; text-align:right;" >${_("Date")}</td>
                        <td class="report_data_hline" style="width: 25mm; text-align:right;" >${_("Due Date")}</td>
                        <td class="report_data_hline" style="width: 25mm; text-align:right;" >${_("Amount")}</td>
                        <td class="report_data_hline" style="width: 25mm; text-align:right;" >${_("Unpaid")}</td>
                        <td class="report_data_hline" style="width: 25mm; text-align:right;" >${_("Dunning Charge")}</td>
                        <td class="report_data_hline" style="width: 24mm; text-align:right;" >${_("Total")}</td>
                    </tr>
                </table>
            </div>
            <div style="clear:both;"></div>
            <div class="report_data">
                <table style="width: 17cm;" >
	                <% total = 0 %>
	                %for invoice in level_invoices:
	                	<% total = total + invoice['followup_total'] %>
	                    <tr>
	                        <td class="report_data_line" style="width: 25mm;" >${invoice['number']}</td>
	                        <td class="report_data_line" style="width: 25mm; text-align:right;" >${invoice['date_invoice']}</td>
	                        <td class="report_data_line" style="width: 25mm; text-align:right;" >${invoice['date_due']}</td>
	                        <td class="report_data_line" style="width: 25mm; text-align:right;" >${formatLang(invoice['total'])  or formatLang(0)} ${invoice['currency']}</td>
	                        <td class="report_data_line" style="width: 25mm; text-align:right;" >${formatLang(invoice['total_unpaid'])  or formatLang(0)} ${invoice['currency']}</td>
	                        <td class="report_data_line" style="width: 25mm; text-align:right;" >${formatLang(invoice['penalization_total'])  or formatLang(0)} ${invoice['currency']}</td>
	                        <td class="report_data_line" style="width: 24mm; text-align:right;" >${formatLang(invoice['followup_total'])  or formatLang(0)} ${invoice['currency']}</td>
	                    </tr>                
	                %endfor
	                	<tr>
	                 		<td colspan = "6"  style="border-top: solid 1px #000;font-size:8pt;padding-top:5px;">${_("Total")}</td>
	                        <td  style=" text-align:right;border-top: solid 1px #000;font-size:8pt;padding-top:5px;" >${formatLang(total)  or formatLang(0)} ${invoice['currency']}</td>
	                    </tr> 
                </table>
        	</div> <!-- end report_data-->
		</div>
			%endfor
			<p style="page-break-after: always">&nbsp;</p>
		%endfor
	% else:
		<span style="font-size:14pt; font-weight:bold;">${_("No invoices in follow-up process to be printed!")}</span>
	% endif:
	</body>
</html>