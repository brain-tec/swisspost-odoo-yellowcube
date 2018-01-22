# b-*- encoding: utf-8 -*-
##############################################################################
#
#    Copyright (c) 2017 brain-tec AG (http://www.braintec-group.com)
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


class ReportLine():
    """ ReportLine is a struct to encode a future line in the report.

        Each line indicates if:
        - It is a blank line:
          Blank lines render in the page as a white space, and can not be at the
          beginning of a page.
        - It is a header line:
          Header lines require to be at the beginning of a sequence of lines which
          require a header, and at the start of pages.
        - The header it requires:
          If a type of line requires a header, this field encodes the type of the
          header it requires, so that we know, e.g. in the beginning of a page, to
          add the corresponding header which it requires, without having to look
          backwards in the sequence of lines already introduced.
        - The type of the line. It is a name indicating which type
          of line the ReportLine encodes.
        - The data of the line. It can be any kind of information that the
          line has to carry.
    """

    def __init__(self, line_type=None, is_blank=False,
                 is_header=False, header=False, data=None):
        if line_type is None:
            line_type = ''

        self.line_type = line_type
        self.is_blank = is_blank
        self.is_header = is_header
        self.header = header
        self.data = data

    def __str__(self):
        output = "[{0}]".format(self.line_type)
        if self.header:
            output += "[under={0}]".format(self.header)
        output += "[blank?={0}][header?={1}]".\
            format("Yes" if self.is_blank else "No",
                   "Yes" if self.is_header else "No")
        return " ".join(output)

    def __eq__(self, other):
        return self.line_type == other.line_type and \
               self.is_blank == other.is_blank and \
               self.is_header == other.is_header and \
               self.header == other.header

    @classmethod
    def BlankLine(cls):
        """ Returns a created blank line.
        """
        return cls(line_type='blank_line', is_blank=True)


def split_lines_into_pages(lines, num_lines_1st_page, num_lines_other_page):
    """ Splits a list of lines into a list of lists of lines, each sublist
        being a page. The split has to account for three basic rules:
        # RULE: Blank lines at the beginning of a page has to be removed.
        # RULE: If the page requires a header, and is not a header, the
        #       header required has to be introduced to lead the page.
        # RULE: The last line of the page can not be a header.

    :param lines: A list of objects ReportLine, which *will be modified*.
    :param num_lines_1st_page: The number of lines that go in the first page.
    :param num_lines_other_page: The number of lines that go into the pages
    which are not the first one.
    :return: A list of lists of lines, the i-th sublist containing the lines
    which go into the i-th page.
    """

    # This will keep track of the lists which encode (each one) a page.
    document = []

    # Indicates the page in which we are currently in the document,
    # starting in one.
    current_page_num = 1

    # Have we finished the pagination of the document?
    document_finished = False

    while not document_finished:
        first_line_pos, last_line_pos = limits_of_page(
            lines, current_page_num,
            num_lines_1st_page, num_lines_other_page)

        # RULE: Blank lines at the beginning of a page has to be removed.
        num_blank_lines_removed = 0
        while lines[first_line_pos].is_blank:
            del lines[first_line_pos]
            num_blank_lines_removed += 1

        # If we removed blank lines, we have to re-compute the limits
        # of the page again, since the last line in the page changed.
        if num_blank_lines_removed > 0:
            first_line_pos, last_line_pos = limits_of_page(
                lines, current_page_num,
                num_lines_1st_page, num_lines_other_page)

        # RULE: If the page requires a header, and is not a header, the
        # header required has to be introduced to lead the page.
        first_line = lines[first_line_pos]
        header_introduced = False
        if first_line.header and not first_line.is_header:
            header_introduced = True
            lines.insert(first_line_pos, first_line.header)

        # If we introduced a header, we have to re-compute the limites of the
        # page again, since the last line in the page changed.
        if header_introduced:
            first_line_pos, last_line_pos = limits_of_page(
                lines, current_page_num,
                num_lines_1st_page, num_lines_other_page)

        # RULE: The last line of the page can not be a header. So if we find
        # any at the end, we change it to be blank lines. Since we have to
        # move backwards we get a copy of the position of the last line.
        last_line_pos_copy = last_line_pos
        while last_line_pos_copy > 0 and lines[last_line_pos_copy].is_header:
            lines.insert(last_line_pos_copy, ReportLine.BlankLine())

            # We move backwards since it can happen (althought is unlikely)
            # that several headers are consecutive.
            last_line_pos_copy -= 1

        # We store the lines that go into this page.
        document.append(lines[first_line_pos:last_line_pos + 1])

        document_finished = last_line_pos == len(lines) - 1
        if not document_finished:
            # We finished with this page and the document still not finished,
            # so we move on to the next one.
            current_page_num += 1

    return document


def limits_of_page(lines, num_page, num_lines_1st_page, num_lines_other_page):
    """ Returns the indices of lines for the first and last line of a page.

    :param lines: A list of elements. 
    :param num_page: The page number we want to know the limits of, starting
    in one.
    :param num_lines_1st_page: The number of lines that fit on the first page. 
    :param num_lines_other_page: The number of lines that fit on the pages
    which are not the first one.
    :return: A tuple encoding the indices of elements of :param lines,
    indicating the first and last line for the number of page indicated by
    the :param num_page.
    """
    if num_page == 1:
        # If it's the first page, we take care not overflowing the total
        # amount of lines that we have.
        first_line_pos = 0
        last_line_pos = min(len(lines) - 1, num_lines_1st_page - 1)

    else:
        # If it's not the first page, then a computation has to be done
        # in order to determine its correct limits, with care to avoid
        # overflowing the total amount of lines.

        # We substract one to the page_num because it starts in one.
        last_line_end = \
            num_lines_1st_page + (num_page - 1) * num_lines_other_page
        first_line_pos = last_line_end - num_lines_other_page
        last_line_pos = last_line_end - 1

        # If the first position lies outside the lines, we arrived to a
        # non-existing page.
        if first_line_pos >= len(lines):
            raise ValueError(
                "The page number {0} (1-based) doesn't exist "
                "for the values provided.".format(num_page))

        # We take care not to overflow the document.
        last_line_pos = min(last_line_pos, len(lines) - 1)

    return first_line_pos, last_line_pos

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
