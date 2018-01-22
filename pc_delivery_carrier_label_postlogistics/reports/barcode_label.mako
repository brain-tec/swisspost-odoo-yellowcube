<html>
    <head>
        <style type="text/css">
            ${css}
        </style>
    </head>

    <body style="border:0.01; margin: 0.01;">

        <% num_pickings = len(objects) %>
        <% num_current_picking = 0 %>

        % while num_current_picking < num_pickings:

			<!-- Gets the current picking -->
            <% o = objects[num_current_picking] %>

            <!-- The language of the barcode report is the language of the shipping address. -->
            <% lang_to_use = o.partner_id.lang %>
            <% setLang(lang_to_use) %>
            <% conf_data = get_configuration_data({'lang': lang_to_use}) %>

			<!-- There will be one page per package (per picking)
			     If no packages are indicated, then there is one page anyway
			     (it's like if it was a virtual-empty-package).
			-->
			<% packages_ids = o.get_different_packages() %>
			<% num_packages = max(1, len(packages_ids)) %>

            <!-- Computes the barcode labels to be used on the report. -->
            <% o.generate_barcodes(packages_ids, context={'lang': lang_to_use}) %>

			% for num_package in xrange(num_packages):

                <% tracking_id = packages_ids and packages_ids[num_package] or None %>
	            <div class="barcode_report_container">
	
	                <!-- Positions the barcode of the company. -->
	                <div class="barcode_report_container_barcode"
	                     style="top:${get_top_of_css_class(conf_data, 'barcode_report_barcode_top')}mm;
	                            left:${conf_data.barcode_report_barcode_left}mm;">
	                    <% barcode_base64 = o.get_barcode(tracking_id, context={'lang': lang_to_use}) %>
	                    <img src="data:image/png;base64,${barcode_base64}" />
	                </div>
	
	                <!-- Positions the logo of the company. -->
	                <div class="barcode_report_container_logo"
	                     style="top:${get_top_of_css_class(conf_data, 'barcode_report_logo_top')}mm;
	                            left:${conf_data.barcode_report_logo_left}mm;
	                            width:${conf_data.barcode_report_logo_width}mm;">
	                    ${o.get_logo(conf_data.barcode_report_logo)}
	                </div>
	
					<!-- If a sending partner is selected, we show its information. -->
					<% sending_partner = conf_data.barcode_report_partner_id %>
					% if sending_partner:
	                <div class="barcode_report_container_partner"
	                     style="top:${get_top_of_css_class(conf_data, 'barcode_report_partner_top')}mm;
	                            left:${conf_data.barcode_report_partner_left}mm;
	                            width:${conf_data.barcode_report_partner_width}mm;
	                            font-size:${conf_data.barcode_report_partner_font_size}pt;">
                             ${sending_partner.get_html_full_address('linebreak')}
                             % if sending_partner.phone:
                             <div class="barcode_report_container_partner_item"><span>${_("Customer service")}</span><span>${sending_partner.phone or ''}</span></div>
                             % endif
                             % if sending_partner.email:
                             <div class="barcode_report_container_partner_item"><span>${_("Email")}</span><span>${sending_partner.email or ''}</span></div>
                             % endif
                             % if sending_partner.website:
							 <div class="barcode_report_container_partner_item"><span>${_("Shop")}</span><span>${sending_partner.website or ''}</span></div>
							 % endif
	                </div>
					% endif
	
	                <!-- Positions the information block. -->
	                <div class="barcode_report_container_info"
	                     style="
	                % if sending_partner:
	                            top:${get_top_of_css_class(conf_data, 'barcode_report_information_top_with_partner')}mm;
	                % else:
	                            top:${get_top_of_css_class(conf_data, 'barcode_report_information_top')}mm;
	                % endif
	                            left:${conf_data.barcode_report_information_left}mm;
	                            width:${conf_data.barcode_report_information_width}mm;">
	                    <table style="width:100%;" class="print_friendly">
	                        <tr style="font-size:${conf_data.barcode_report_information_font_size}pt;">
	                            <td class="barcode_report_left_align">${_('Customer Number')}</td>
	                            <td class="barcode_report_right_align">${o.partner_id.get_ref() or ''}</td>
	                        </tr>
	                        <tr style="font-size:${conf_data.barcode_report_information_font_size}pt;">
	                            <td class="barcode_report_left_align">${_('Sale order')}</td>
	                            <td class="barcode_report_right_align">${o.origin or ''}</td>
	                        </tr>
	                        <tr style="font-size:${conf_data.barcode_report_information_font_size}pt;">
	                            <td class="barcode_report_left_align">${_('Document Number')}</td>
	                            <td class="barcode_report_right_align">${o.name or ''}</td>
	                        </tr>
	                        <tr style="font-size:${conf_data.barcode_report_information_font_size}pt;">
	                            <td class="barcode_report_left_align">${_('Document Date')}</td>
	                            <td class="barcode_report_right_align">${formatLang(o.date or '', date=True)}</td>
	                        </tr>
	                        <!--
	                        <tr>
	                            <td class="barcode_report_left_align">${_('Shipping date')}</td>
	                            <td class="barcode_report_right_align">${o.min_date or ''}</td>
	                        </tr>
	                        -->
	                        <tr>
	                            <td class="barcode_report_left_align">${_('Tax number')}</td>
	                            <td class="barcode_report_right_align">${o.company_id.vat or ''}</td>
	                        </tr>
	                    </table>
	                </div>  <!-- class="barcode_report_container_info" -->

					<!-- If there are more than one package, we print the iterator to know to
					     which package of the total this one package corresponds.
					-->
					% if num_packages > 1:
					<div class="barcode_report_container_package"
						 style="top:${get_top_of_css_class(conf_data, 'barcode_report_package_top')}mm;
	                            left:${conf_data.barcode_report_package_left}mm;
	                            font-size:${conf_data.barcode_report_package_font_size}pt;
	                            font-weight:${conf_data.barcode_report_package_font_weight}">
						<p>${_('Package')}: ${'{:02d}'.format(num_package + 1)} ${_('of')} ${'{:02d}'.format(num_packages)}</p>
					</div>
					% endif

	            </div>  <!-- class="barcode_report_container" -->
				<% increment_page_num() %>  <!-- One page per package & picking. -->

			% endfor

            <% num_current_picking += 1 %>
        % endwhile

    </body>

</html>
