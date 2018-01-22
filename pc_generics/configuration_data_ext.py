# b-*- encoding: utf-8 -*-
##############################################################################
#
#    Copyright (c) 2015 brain-tec AG (http://www.braintec-group.com)
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
from openerp.osv import osv, fields
from openerp.tools.translate import _


class configuration_data_ext(osv.Model):
    _inherit = 'configuration.data'

    _columns = {
        # Fields related with the positioning of the ESR in modules pc_account and pc_followup.
        'esr_bvr_background_top': fields.float('BVR Background (top)', help='bvr_background (distance from the top of the page, in mm.)'),
        'esr_bvr_background_left': fields.float('BVR Background (left)', help='bvr_background (distance from the left of the page, in mm.)'),

        'esr_slip_bank_top': fields.float('Left Bank (top)', help='slip_bank (distance from the top of the page, in mm.)'),
        'esr_slip_bank_left': fields.float('Left Bank (left)', help='slip_bank (distance from the left of the page, in mm.)'),
        'esr_slip_bank_size': fields.float('Left Bank (size)', help='slip_bank (size of the font, in pt.)'),

        'esr_slip_comp_top': fields.float('Left Bank Owner Address (top)', help='slip_comp (distance from the top of the page, in mm.)'),
        'esr_slip_comp_left': fields.float('Left Bank Owner Address (left)', help='slip_comp (distance from the left of the page, in mm.)'),
        'esr_slip_comp_size': fields.float('Left Bank Owner Address (size)', help='slip_comp (size of the font, in pt.)'),

        'esr_slip_bank_acc_top': fields.float('Left Bank Account Number (top)', help='slip_bank_acc (distance from the top of the page, in mm.)'),
        'esr_slip_bank_acc_left': fields.float('Left Bank Account Number (left )', help='slip_bank_acc (distance from the left of the page, in mm.)'),
        'esr_slip_bank_acc_size': fields.float('Left Bank Account Number (size)', help='slip_bank_acc (size of the font, in pt.)'),

        'esr_slip_amount_top': fields.float('Left Amount (top)', help='slip_amount (distance from the top of the page, in mm.)'),
        'esr_slip_amount_right': fields.float('Left Amount (right)', help='slip_amount (distance from the right of the page, in mm.)'),
        'esr_slip_amount_size': fields.float('Left Amount (size)', help='slip_amount (size of the font, in pt.)'),

        'esr_slip_ref_top': fields.float('Left Reference Number (top)', help='slip_ref (distance from the top of the page, in mm.)'),
        'esr_slip_ref_right': fields.float('Left Reference Number (right)', help='slip_ref (distance from the right of the page, in mm.)'),
        'esr_slip_ref_size': fields.float('Left Reference Number (size)', help='slip_ref (size of the font, in pt.)'),

        'esr_slip_address_b_top': fields.float('Left Customer Address (top)', help='slip_address_b (distance from the top of the page, in mm.)'),
        'esr_slip_address_b_left': fields.float('Left Customer Address (left)', help='slip_address_b (distance from the left of the page, in mm.)'),
        'esr_slip_address_b_size': fields.float('Left Customer Address (size)', help='slip_address_b (size of the font, in pt.)'),

        'esr_slip2_bank_top': fields.float('Right Bank (top)', help='slip2_bank (distance from the top of the page, in mm.)'),
        'esr_slip2_bank_left': fields.float('Right Bank (left)', help='slip2_bank (distance from the left of the page, in mm.)'),
        'esr_slip2_bank_size': fields.float('Right Bank (size)', help='slip2_bank (size of the font, in pt.)'),

        'esr_slip2_comp_top': fields.float('Right Bank Owner Address (top)', help='slip2_comp (distance from the top of the page, in mm.)'),
        'esr_slip2_comp_left': fields.float('Right Bank Owner Address (left)', help='slip2_comp (distance from the left of the page, in mm.)'),
        'esr_slip2_comp_size': fields.float('Right Bank Owner Address (size)', help='slip2_comp (size of the font, in pt.)'),

        'esr_slip2_bank_acc_top': fields.float('Right Bank Account Number (top)', help='slip2_bank_acc (distance from the top of the page, in mm.)'),
        'esr_slip2_bank_acc_left': fields.float('Right Bank Account Number (left)', help='slip2_bank_acc (distance from the left of the page, in mm.)'),
        'esr_slip2_bank_acc_size': fields.float('Right Bank Account Number (size)', help='slip2_bank_acc (size of the font, in pt.)'),

        'esr_slip2_amount_top': fields.float('Right Amount (tope)', help='slip2_amount (distance from the top of the page, in mm.)'),
        'esr_slip2_amount_right': fields.float('Right Amount (right)', help='slip2_amount (distance from the right of the page, in mm.)'),
        'esr_slip2_amount_size': fields.float('Right Amount (size)', help='slip2_amount (size of the font, in pt.)'),

        'esr_slip2_ref_top': fields.float('Right Reference Number (top)', help='slip2_ref (distance from the top of the page, in mm.)'),
        'esr_slip2_ref_right': fields.float('Right Reference Number (right)', help='slip2_ref (distance from the right of the page, in mm.)'),
        'esr_slip2_ref_size': fields.float('Right Reference Number (size)', help='slip2_ref (size of the font, in pt.)'),

        'esr_slip2_address_b_top': fields.float('Right Customer Address (top)', help='slip2_address_b (distance from the top of the page, in mm.)'),
        'esr_slip2_address_b_left': fields.float('Right Customer Address (left)', help='slip2_address_b (distance from the left of the page, in mm.)'),
        'esr_slip2_address_b_size': fields.float('Right Customer Address (size)', help='slip2_address_b (size of the font, in pt.)'),

        'esr_ocrbb_top': fields.float('OCR Code (top)', help='ocrbb (distance from the top of the page, in mm.)'),
        'esr_ocrbb_left': fields.float('OCR Code (left)', help='ocrbb (distance from the left of the page, in mm.)'),
        'esr_ocrbb_size': fields.float('OCR Code (size)', help='ocrbb (size of the font, in pt.)'),
        'esr_ocrbb_width': fields.float('OCR Code Characters (width)', help='ocrbb (width of characters, in mm.)'),
        'esr_ocrbb_digitref_start': fields.float('OCR Code Characters (left internal start)', help='digitref (extra left space to start showing the digits, in mm.)'),
        'esr_ocrbb_digitref_coefficient': fields.float('OCR Code Characters (coefficient)', help='digitref (extra separation between the start of one digit and the next one, in mm.'),
    }

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
