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

from unittest2 import skipIf
from openerp.tests import common
from openerp.addons.pc_generics.ReportLine import \
    ReportLine, split_lines_into_pages, limits_of_page


UNDER_DEVELOPMENT = False
UNDER_DEVELOPMENT_TEXT = 'Test was skipped because of being under development'


class TestReportLine(common.TransactionCase):

    def setUp(self):
        super(TestReportLine, self).setUp()

    def tearDown(self):
        super(TestReportLine, self).tearDown()

    @skipIf(UNDER_DEVELOPMENT, UNDER_DEVELOPMENT_TEXT)
    def test_create_unique_blank_line(self):
        blank_line_1 = ReportLine.BlankLine()
        blank_line_2 = ReportLine.BlankLine()
        self.assertFalse(blank_line_1 is blank_line_2)

    @skipIf(UNDER_DEVELOPMENT, UNDER_DEVELOPMENT_TEXT)
    def test_limits_of_page_non_existing_page(self):
        with self.assertRaises(ValueError):
            limits_of_page(lines=[1, 2, 3, 4], num_page=3,
                           num_lines_1st_page=2,
                           num_lines_other_page=2)

    @skipIf(UNDER_DEVELOPMENT, UNDER_DEVELOPMENT_TEXT)
    def test_limits_of_page_first(self):
        # Tests a perfect fit.
        first_pos, last_pos = \
            limits_of_page(lines=[1, 2], num_page=1,
                           num_lines_1st_page=2,
                           num_lines_other_page=2)
        self.assertEqual(first_pos, 0)
        self.assertEqual(last_pos, 1)

        # Tests a long first page.
        first_pos, last_pos = \
            limits_of_page(lines=[1, 2], num_page=1,
                           num_lines_1st_page=3,
                           num_lines_other_page=2)
        self.assertEqual(first_pos, 0)
        self.assertEqual(last_pos, 1)

        # Tests a short first page.
        first_pos, last_pos = \
            limits_of_page(lines=[1, 2], num_page=1,
                           num_lines_1st_page=1,
                           num_lines_other_page=2)
        self.assertEqual(first_pos, 0)
        self.assertEqual(last_pos, 0)

    @skipIf(UNDER_DEVELOPMENT, UNDER_DEVELOPMENT_TEXT)
    def test_limits_of_page_not_first(self):
        # Tests a middle page.
        first_pos, last_pos = \
            limits_of_page(lines=[1, 2, 3, 4, 5, 6, 7], num_page=2,
                           num_lines_1st_page=2,
                           num_lines_other_page=3)
        self.assertEqual(first_pos, 2)
        self.assertEqual(last_pos, 4)

        # Tests the last page, without overflow.
        first_pos, last_pos = \
            limits_of_page(lines=[1, 2, 3, 4, 5, 6, 7, 8], num_page=3,
                           num_lines_1st_page=2,
                           num_lines_other_page=3)
        self.assertEqual(first_pos, 5)
        self.assertEqual(last_pos, 7)

        # Tests the last page, with overflow.
        first_pos, last_pos = \
            limits_of_page(lines=[1, 2, 3, 4, 5, 6, 7], num_page=3,
                           num_lines_1st_page=2,
                           num_lines_other_page=3)
        self.assertEqual(first_pos, 5)
        self.assertEqual(last_pos, 6)

    @skipIf(UNDER_DEVELOPMENT, UNDER_DEVELOPMENT_TEXT)
    def test_split_lines_into_pages_base_case(self):
        # Tests a case without problems, in which the split is straightforward.

        a = ReportLine(line_type='a')
        b = ReportLine(line_type='b')
        c = ReportLine(line_type='c')
        d = ReportLine(line_type='d')
        e = ReportLine(line_type='e')
        f = ReportLine(line_type='f')
        g = ReportLine(line_type='g')
        b1 = ReportLine(line_type='b1', is_blank=True)

        original_lines = [a, b, c, b1, d, e, f, g]
        expected_split = [[a, b], [c, b1, d], [e, f, g]]

        actual_split = split_lines_into_pages(
            original_lines, num_lines_1st_page=2, num_lines_other_page=3)

        self.assertEqual(actual_split, expected_split)

    @skipIf(UNDER_DEVELOPMENT, UNDER_DEVELOPMENT_TEXT)
    def test_split_lines_into_pages_blank_lines(self):
        # Tests a case with blank lines at beginning of pages.

        a = ReportLine(line_type='a')
        b = ReportLine(line_type='b')
        c = ReportLine(line_type='c')
        d = ReportLine(line_type='d')
        e = ReportLine(line_type='e')
        f = ReportLine(line_type='f')
        b1 = ReportLine(line_type='b1', is_blank=True)
        b2 = ReportLine(line_type='b2', is_blank=True)
        b3 = ReportLine(line_type='b3', is_blank=True)
        b4 = ReportLine(line_type='b4', is_blank=True)
        b5 = ReportLine(line_type='b5', is_blank=True)

        original_lines = [a, b, b1, b2, c, b3, d, b4, e, f, b5]
        expected_split = [[a, b], [c, b3, d], [e, f, b5]]

        actual_split = split_lines_into_pages(
            original_lines, num_lines_1st_page=2, num_lines_other_page=3)

        self.assertEqual(actual_split, expected_split)

    @skipIf(UNDER_DEVELOPMENT, UNDER_DEVELOPMENT_TEXT)
    def test_split_lines_into_pages_header_lines(self):
        # Tests a case which requires to introduce & remove header lines.

        a = ReportLine(line_type='a')
        b = ReportLine(line_type='b')
        c = ReportLine(line_type='c')
        d = ReportLine(line_type='d')
        h1 = ReportLine(line_type='h1', is_header=True)
        rh11 = ReportLine(line_type='rh11', header=h1)
        rh12 = ReportLine(line_type='rh12', header=h1)
        rh13 = ReportLine(line_type='rh13', header=h1)
        h2 = ReportLine(line_type='h2', is_header=True)
        rh21 = ReportLine(line_type='rh21', header=h2)
        rh22 = ReportLine(line_type='rh22', header=h2)

        original_lines = [a, b, c, d, h1, rh11, rh12, rh13, h2, rh21, rh22]
        expected_split = [[a, b],
                          [c, d, ReportLine.BlankLine()],
                          [h1, rh11, rh12],
                          [h1, rh13, ReportLine.BlankLine()],
                          [h2, rh21, rh22],
                          ]

        actual_split = split_lines_into_pages(
            original_lines, num_lines_1st_page=2, num_lines_other_page=3)

        self.assertEqual(actual_split, expected_split)

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
