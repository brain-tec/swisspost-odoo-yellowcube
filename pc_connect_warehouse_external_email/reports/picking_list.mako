<html>
    <head>
        <style type="text/css">
            ${css}
        </style>
    </head>

    <body style="border:0.01; margin: 0.01;">

        <% lang_to_use = objects[0].company_id.partner_id.lang %>
        <% setLang(lang_to_use) %>

		<!-- We get all the data we are going to need to craft the mako. -->
		<% conf_data = get_configuration_data() %>
		<% NUM_COLUMNS_FOR_DELIVERY_ORDERS = 4 %>
        <% NUM_ELEMENTS_PER_PAGE = conf_data.email_connector_report_picking_list_num_lines or 30 %>
		<% creation_datetime = formatLang(get_creation_datetime({'lang': lang_to_use}), date_time=True) %>
		<% num_delivery_orders = len(objects) %>
        <% elements_to_pages = assign_elements_to_pages(objects, NUM_ELEMENTS_PER_PAGE, NUM_COLUMNS_FOR_DELIVERY_ORDERS, {'lang': lang_to_use}) %>

		<!-- We get the total amount of page numbers to use. -->
		<% num_total_pages = len(elements_to_pages) %>
		<% num_current_page = 0 %> <!-- Page 0 is the first page in this mako. -->

		<!-- We first create the pages containing the list of deliveries -->
		% while num_current_page < num_total_pages:
    
            <% current_page = elements_to_pages[num_current_page] %>

            <div class="container_defining_margins">

                <!-- Every page has the pseudo-header. -->
                <% o = objects[0] %>
                <div class="report_pseudo_header">
                    <div class="report_header_logo">
                        ${o.get_logo(conf_data.email_connector_report_picking_list_logo)}
                    </div>
                    <div class="report_header_address">
                        ${o.company_id.partner_id.name or ''} <span class="linebreak" />
                        <% partner_addr_data = o.get_company_address('linebreak') %>
                        ${partner_addr_data or ''}
                    </div>
                    <div class="report_header_pagenumber">
                        ${_('Page')}: ${num_current_page + 1} / ${num_total_pages}
                    </div>
                </div>
                <div class="horizontal_line_black"></div>

                <div class="picking_list_content">
                    % for element_in_current_page in current_page:

                        <!-- We start a table. -->
                        % if element_in_current_page[0] == 'start_table':
                            <table style="width:100%;" class="print_friendly">
                        % endif

                        <!-- We end a table. -->
                        % if element_in_current_page[0] == 'end_table':
                            </table>
                        % endif

                        <!-- The title of the document. -->
                        % if element_in_current_page[0] == 'picking_list_title':
                            <div class="picking_list_title">${_('Picking List')}</div>
                        % endif

                        <!-- The date in which the document was created. -->
                        % if element_in_current_page[0] == 'document_creation_date':
                            <tr>
                                <td style="width: 35%;">${_('Creation Date')}:</td>
                                <td colspan="3">${creation_datetime}</td>
                            </tr>
                        % endif

                        <!-- The number of delivery orders contained in this batch. -->
                        % if element_in_current_page[0] == 'number_of_delivery_orders':
                            <tr>
                                <td>${_('Number of delivery orders in this batch')}:</td>
                                <td colspan="3">${num_delivery_orders}</td>
                            </tr>
                        % endif

                        <!-- Title for the list of pickings contained. -->
                        % if element_in_current_page[0] == 'picking_list_delivery_orders_title':
                            <tr><td colspan="4"><div class="picking_list_title">${_('List of Pickings')}</div></td></tr>
                        % endif

                        <!-- A line containing a subset of the delivery orders contained in this order. -->
                        % if element_in_current_page[0] == 'picking_list_delivery_orders_item':
                            <tr>
                                % for item in element_in_current_page[-1]:
                                    <td style="width: 25%;">${item}</td>
                                % endfor
                            </tr>
                        % endif

                        <!-- Title for the list of products contained. -->
                        % if element_in_current_page[0] == 'picking_list_products_title':
                            <div class="picking_list_title">${_('List of Products')}</div>
                        % endif

                        <!-- Heading of the list of products contained. -->
                        % if element_in_current_page[0] == 'picking_list_products_heading':
                            <tr>
                                <td class="picking_list_products_default_code"><strong>${_('Default Code')}</strong></td>
                                <td class="picking_list_products_description"><strong>${_('Description')}</strong></td>
                                <td class="picking_list_products_uom"><strong>${_('Unit of Measure')}</strong></td>
                                <td class="picking_list_products_qty"><strong>${_('Quantity')}</strong></td>
                            </tr>
                        % endif

                        <!-- An entry in the list of products contained. -->
                        % if element_in_current_page[0] == 'picking_list_products_item':
                            <% product_id = element_in_current_page[-1][0] %>
                            <% product = get_product(product_id, {'lang': lang_to_use}) %>
                            <% uom_id = element_in_current_page[-1][1] %>
                            <% uom = get_uom(uom_id, {'lang': lang_to_use}) %>
                            <% quantity = element_in_current_page[-1][2] %>
                            <tr>
                                <td class="picking_list_products_default_code">${product.default_code}</td>
                                <td class="picking_list_products_description">${product.name}</td>
                                <td class="picking_list_products_uom">${uom.name}</td>
                                <td class="picking_list_products_qty">${quantity}</td>
                            </tr>
                        % endif
                        
                        <!-- This is to cleary show that we have reached the end of the report. -->
                        % if element_in_current_page[0] == 'picking_list_end_of_report':
                            <div class="picking_list_title">-----${_('END of the Picking List')}-----</div>
                        % endif

                    % endfor
                </div>

            <% num_current_page += 1 %>
            </div>

		% endwhile
    </body>

</html>
