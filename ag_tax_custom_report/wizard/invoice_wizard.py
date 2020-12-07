# -*- coding: utf-8 -*-

import xlwt
#import cStringIO
import io
import base64
import time
import datetime
from datetime import datetime
from datetime import timedelta
from datetime import datetime, timedelta
from dateutil import relativedelta

#from openerp import models, fields,api
from odoo import models, fields, api


class InvoiceWizard(models.TransientModel):
    _name = 'invoice.wizard'

    start_date = fields.Date(
        string = 'Date From',
        required = True,
        default=time.strftime('%Y-%m-01'),
    )
    end_date = fields.Date(
        string = 'Date To',
        required = True,
        default=str(datetime.now() + relativedelta.relativedelta(months=+1, day=1, days=-1))[:10],
    )
    xls_output = fields.Binary(
        string='Excel Output',
    )
    name = fields.Char(
        string='File Name',
        help='Save report as .xls format',
        default='invoicelr.xls',
    )
    report_type = fields.Selection(
        selection=[
            ('sale_report', 'Sales Report'),
            ('purchase_report', 'Purchase Report'),
        ],
        default='sale_report',
        string='Report Type',
        required=True
    )

#    @api.multi
    def print_invoie_report(self):
        data = self.read()[0]
#        start_update = datetime.strptime(data['start_date'], '%Y-%m-%d').strftime('%m/%d/%Y')
        start_update = data['start_date'].strftime('%m/%d/%Y')
#        end_update = datetime.strptime(data['end_date'], '%Y-%m-%d').strftime('%m/%d/%Y')
        end_update = data['end_date'].strftime('%m/%d/%Y')
        data['start_update'] = start_update
        data['end_update'] = end_update
        data['report_type'] = self.report_type
#        cinvoice = cinvoice_ids = self.env['account.invoice'].search([('date_invoice', '>=', self.start_date), ('date_invoice', '<=', self.end_date), ('type', '=', 'out_invoice')], limit=1)
        cinvoice = self.env['account.move']
        if self.report_type == 'sale_report':
            cinvoice = cinvoice_ids = self.env['account.move'].search([('invoice_date', '>=', self.start_date), ('invoice_date', '<=', self.end_date), ('type', '=', 'out_invoice')], limit=1)
#        vinvoice = cinvoice_ids = self.env['account.invoice'].search([('date_invoice', '>=', self.start_date), ('date_invoice', '<=', self.end_date), ('type', '=', 'in_invoice')], limit=1)
        vinvoice = self.env['account.move']
        if self.report_type == 'purchase_report':
            vinvoice = cinvoice_ids = self.env['account.move'].search([('invoice_date', '>=', self.start_date), ('invoice_date', '<=', self.end_date), ('type', '=', 'in_invoice')], limit=1)
        if cinvoice:
            data['ids'] = cinvoice.id
        else:
            data['ids'] = vinvoice.id
#        data['model'] = 'account.invoice'
        data['model'] = 'account.move'
#        return self.env['report'].get_action(self, 'odoo_tax_custom_report.invoice_print',data=data)
        return self.env.ref('ag_tax_custom_report.custom_invoice_report').report_action(self, data=data, config=False)

#    @api.multi
    def export_invoice(self):
        customer_inv = []
#        cinvoice_ids = self.env['account.invoice'].search([('date_invoice', '>=', self.start_date), ('date_invoice', '<=', self.end_date), ('type', '=', 'out_invoice')], order="number asc, id asc")
        cinvoice_ids = self.env['account.move']
        if self.report_type == 'sale_report':
            cinvoice_ids = self.env['account.move'].search([('invoice_date', '>=', self.start_date), ('invoice_date', '<=', self.end_date), ('type', '=', 'out_invoice')], order="name asc, id asc")
        dict_customer_inv = {}
        for inv in cinvoice_ids:
            customer_inv.append(inv)
#            curr_date_inv = fields.Datetime.from_string(inv.date_invoice)
            curr_date_inv = fields.Datetime.from_string(inv.invoice_date)
            if curr_date_inv.strftime('%B %Y') in dict_customer_inv:
                dict_customer_inv[curr_date_inv.strftime('%B %Y')].append(inv)
            else:
                dict_customer_inv.update({
                     curr_date_inv.strftime('%B %Y'): [inv]
                 })

        vendor_inv = []
#        vinvoice_ids = self.env['account.invoice'].search([('date_invoice', '>=', self.start_date), ('date_invoice', '<=', self.end_date), ('type', '=', 'in_invoice')], order="number asc, id asc")
        vinvoice_ids = self.env['account.move']
        if self.report_type == 'purchase_report':
            vinvoice_ids = self.env['account.move'].search([('invoice_date', '>=', self.start_date), ('invoice_date', '<=', self.end_date), ('type', '=', 'in_invoice')], order="name asc, id asc")
        dict_vendor_inv = {}
        for vline in vinvoice_ids:
            vendor_inv.append(vline)
#            curr_date_inv = fields.Datetime.from_string(vline.date_invoice)
            curr_date_inv = fields.Datetime.from_string(vline.invoice_date)
            if curr_date_inv.strftime('%B %Y') in dict_vendor_inv:
                dict_vendor_inv[curr_date_inv.strftime('%B %Y')].append(vline)
            else:
                dict_vendor_inv.update({
                     curr_date_inv.strftime('%B %Y'): [vline]
                 })
        
        #Added Credit Notes
        credit_notes_inv = []
#        creditnote_ids = self.env['account.invoice'].search([('date_invoice', '>=', self.start_date), ('date_invoice', '<=', self.end_date), ('type', '=', 'out_refund')], order="number asc, id asc")
        creditnote_ids = self.env['account.move']
        if self.report_type == 'sale_report':
            creditnote_ids = self.env['account.move'].search([('invoice_date', '>=', self.start_date), ('invoice_date', '<=', self.end_date), ('type', '=', 'out_refund')], order="name asc, id asc")
        dict_credit_notes_inv = {}
        for credit_note in creditnote_ids:
            credit_notes_inv.append(credit_note)
#            curr_date_inv = fields.Datetime.from_string(credit_note.date_invoice)
            curr_date_inv = fields.Datetime.from_string(credit_note.invoice_date)
            if curr_date_inv.strftime('%B %Y') in dict_credit_notes_inv:
                dict_credit_notes_inv[curr_date_inv.strftime('%B %Y')].append(credit_note)
            else:
                dict_credit_notes_inv.update({
                     curr_date_inv.strftime('%B %Y'): [credit_note]
                 })
        
        #Added Debit Notes
        debit_notes_inv = []
#        debitnote_ids = self.env['account.invoice'].search([('date_invoice', '>=', self.start_date), ('date_invoice', '<=', self.end_date), ('type', '=', 'in_refund')], order="number asc, id asc")
        debitnote_ids = self.env['account.move']
        if self.report_type == 'purchase_report':
            debitnote_ids = self.env['account.move'].search([('invoice_date', '>=', self.start_date), ('invoice_date', '<=', self.end_date), ('type', '=', 'in_refund')], order="name asc, id asc")
        dict_debit_notes_inv = {}
        for debit_note in debitnote_ids:
            debit_notes_inv.append(debit_note)
#            curr_date_inv = fields.Datetime.from_string(debit_note.date_invoice)
            curr_date_inv = fields.Datetime.from_string(debit_note.invoice_date)
            if curr_date_inv.strftime('%B %Y') in dict_debit_notes_inv:
                dict_debit_notes_inv[curr_date_inv.strftime('%B %Y')].append(debit_note)
            else:
                dict_debit_notes_inv.update({
                     curr_date_inv.strftime('%B %Y'): [debit_note]
                 })
        
#        return self._get_invoice_excel(customer_inv, vendor_inv, credit_notes_inv, debit_notes_inv)
        return self._get_invoice_excel(dict_customer_inv, dict_vendor_inv, dict_credit_notes_inv, dict_debit_notes_inv)

#    @api.multi
    def _get_invoice_excel(self, cus_invoice, ven_invoice, credit_notes_inv, debit_notes_inv):
        workbook = xlwt.Workbook()
        title_style_comp = xlwt.easyxf('align: horiz center; font: name Times New Roman,bold off, italic off, height 450')
        title_style_comp_left = xlwt.easyxf('align: horiz center ; font: name Times New Roman,bold on, italic off, height 450')
        title_style = xlwt.easyxf('align: horiz center ;font: name Times New Roman,bold off, italic off, height 350')
        title_style2 = xlwt.easyxf('font: name Times New Roman, height 200')
        title_style1 = xlwt.easyxf('font: name Times New Roman,bold off, italic off, height 190; borders: top double, bottom double, left double, right double;')
        title_style1_table_head = xlwt.easyxf('font: name Times New Roman,bold on, italic off, height 200;')
        title_style1_table_head3 = xlwt.easyxf('font: name Times New Roman,bold on, italic off, height 200; borders: top double, bottom double, left double, right double;')
        title_style1_table_head1 = xlwt.easyxf('align: horiz left; font: name Times New Roman,bold on, italic off, height 200')
        title_style1_table_head1b = xlwt.easyxf('align: horiz center;borders: top double, bottom double, left double, right double;font: name Times New Roman,bold on, italic off, height 200')
        title_style1_table_head1t = xlwt.easyxf('align: horiz center;borders: bottom double;font: name Times New Roman,bold on, italic off, height 200')
        title_style1_table_head5 = xlwt.easyxf('align: horiz right; font: name Times New Roman,bold off, italic off, height 190')
        title_style1_consultant = xlwt.easyxf('font: name Times New Roman,bold on, italic off, height 200; borders: top double, bottom double, left double, right double;')
        title_style1_table_head_center = xlwt.easyxf('align: horiz center; font: name Times New Roman,bold on, italic off, height 190; borders: top thick, bottom thick, left thick, right thick;')

        title_style1_table_data = xlwt.easyxf('align: horiz right ;font: name Times New Roman,bold on, italic off, height 190')
        title_style1_table_data_sub = xlwt.easyxf('font: name Times New Roman,bold off, italic off, height 190')
        title_style1_table_data_sub_right = xlwt.easyxf('align: horiz right; font: name Times New Roman,bold off, italic off, height 190')
        title_style1_table_data_sub_left = xlwt.easyxf('align: horiz left; font: name Times New Roman,bold off, italic off, height 190')
        lang = self.env.user.lang
        lang_date = self.env['res.lang'].search([('code', '=', lang)])
        sheet_name = "Invoice"
        sheet = workbook.add_sheet(sheet_name)
        comp_id = self.env.user.company_id
        currency_id = comp_id.currency_id
        column = sheet.col(0)
        column.width = 256 * 20
        column = sheet.col(4)
        column.width = 256 * 20
        if self.start_date:
#            oldformat = datetime.strptime(self.start_date,'%Y-%m-%d')
            oldformat = self.start_date
            newformat = oldformat.strftime(lang_date.date_format)
            sheet.write(3, 0, 'Start Date :',title_style1_table_head)
            sheet.write(3, 1, newformat, title_style1_table_data_sub)
        if self.end_date:
#            oldend = datetime.strptime(self.end_date,'%Y-%m-%d')
            oldend = self.end_date
            newend = oldend.strftime(lang_date.date_format)
            sheet.write(3, 2, 'End Date :',title_style1_table_head)
            sheet.write(3, 3, newend, title_style1_table_data_sub)
        account_name = ''
        srow=8
        gtotal_vat_sales_other_op = 0.0
        if cus_invoice:
            cell = 1
            sheet.write_merge(5, 6, 0, 3, 'VAT on Sales and other Outputs', title_style_comp_left)
            sheet.write_merge(5, 6, 4, 5, 'Start Date - ', title_style_comp_left)
            sheet.write_merge(5, 6, 6, 7, newformat, title_style_comp_left)
            sheet.write_merge(5, 6, 8, 9, 'End Date - ', title_style_comp_left)
            sheet.write_merge(5, 6, 10, 11, newend, title_style_comp_left)

            column = sheet.col(1)
            column.width = 256 * 30
            sheet.write(7, 0, 'SL NO', title_style1_table_head1b)
            sheet.write(7, 1, 'Tax Invoice No', title_style1_table_head1b)
            sheet.write(7, 2, 'Tax Invoice Date', title_style1_table_head1b)
            sheet.write(7, 3, 'Gross Invoice amount (Without VAT)', title_style1_table_head1b)
            sheet.write(7, 4, 'VAT Amount VAT', title_style1_table_head1b)
            sheet.write(7, 5, 'Tax Invoice Amount AED', title_style1_table_head1b)
    #        sheet.write(7, 4, 'VAT Amount VAT', title_style1_table_head1b)
            sheet.write(7, 6, 'Customer No.', title_style1_table_head1b)
            sheet.write(7, 7, 'Customer Name', title_style1_table_head1b)
            sheet.write(7, 8, 'Customer TRN', title_style1_table_head1b)
            sheet.write(7, 9, 'Customer Location', title_style1_table_head1b)
            sheet.write(7, 10, 'Currency', title_style1_table_head1b)
            sheet.write(7, 11, 'Total', title_style1_table_head1b)
            i = 1
            cus_invoice_keys = list(cus_invoice.keys())
            cus_invoice_keys.sort(key=lambda x: datetime.strptime(x,'%B %Y'))
            gtotal_vat_sales_other_op = 0.0
            for data_line in cus_invoice_keys:
                sheet.write(srow, 0, data_line, title_style1_table_head)
                sheet.write(srow, 3, sum(line.amount_untaxed for line in cus_invoice[data_line]), title_style1_table_head)
                sheet.write(srow, 4, sum(line.amount_tax for line in cus_invoice[data_line]), title_style1_table_head)
                sheet.write(srow, 5, sum(line.amount_total for line in cus_invoice[data_line]), title_style1_table_head)
                sheet.write(srow, 10, sum(line.amount_total for line in cus_invoice[data_line]), title_style1_table_head)
                gtotal_vat_sales_other_op += sum(line.amount_total for line in cus_invoice[data_line])
                srow += 1
                for line in cus_invoice[data_line]:
    #                oldate = datetime.strptime(line.date_invoice,'%Y-%m-%d')
                    oldate = line.invoice_date
                    newdate = oldate.strftime(lang_date.date_format)
                    sheet.write(srow, 0, i, title_style1_table_data_sub)
    #                sheet.write(srow, 1, line.number, title_style1_table_data_sub)
                    sheet.write(srow, 1, line.name, title_style1_table_data_sub)
                    sheet.write(srow, 2, newdate, title_style1_table_data_sub)
                    sheet.write(srow, 3, line.amount_untaxed, title_style1_table_data_sub)
                    sheet.write(srow, 4, line.amount_tax, title_style1_table_data_sub)
                    sheet.write(srow, 5, line.amount_total, title_style1_table_data_sub)
    #                sheet.write(srow, 4, line.amount_tax, title_style1_table_data_sub)
                    sheet.write(srow, 6, line.partner_id.sequence_no, title_style1_table_data_sub)
                    sheet.write(srow, 7, line.partner_id.name, title_style1_table_data_sub)
                    sheet.write(srow, 8, line.partner_id.vat, title_style1_table_data_sub)
                    sheet.write(srow, 9, line.partner_id.city, title_style1_table_data_sub)
                    sheet.write(srow, 10, line.currency_id.name, title_style1_table_data_sub)
                    srow = srow + 1;
                    i = i + 1;
            srow = srow + 3;
        lrow = srow + 1
        srow = lrow + 1
        gtotal_vat_expense_other_ip = 0.0
        if ven_invoice:
            sheet.write_merge(lrow, srow, 0, 3, 'VAT on Expenses and other Inputs', title_style_comp_left)
            sheet.write_merge(lrow, srow, 4, 5, 'Start Date - ', title_style_comp_left)
            sheet.write_merge(lrow, srow, 6, 7, newformat, title_style_comp_left)
            sheet.write_merge(lrow, srow, 8, 9, 'End Date - ', title_style_comp_left)
            sheet.write_merge(lrow, srow, 10, 11, newend, title_style_comp_left)
            srow = srow + 1;
            sheet.write(srow, 0, 'SL NO', title_style1_table_head1b)
            sheet.write(srow, 1, 'Tax Invoice No', title_style1_table_head1b)
            sheet.write(srow, 2, 'Tax Invoice Date', title_style1_table_head1b)
            sheet.write(srow, 3, 'Gross Invoice amount (Without VAT)', title_style1_table_head1b)
            sheet.write(srow, 4, 'VAT Amount VAT', title_style1_table_head1b)
            sheet.write(srow, 5, 'Tax Invoice Amount AED', title_style1_table_head1b)
    #        sheet.write(srow, 4, 'VAT Amount VAT', title_style1_table_head1b)
            sheet.write(srow, 6, 'Vendor No.', title_style1_table_head1b)
            sheet.write(srow, 7, 'Supplier Name', title_style1_table_head1b)
            sheet.write(srow, 8, 'Supplier TRN', title_style1_table_head1b)
            sheet.write(srow, 9, 'Supplier Location', title_style1_table_head1b)
            sheet.write(srow, 10, 'Currency', title_style1_table_head1b)
            sheet.write(srow, 11, 'Total', title_style1_table_head1b)
            srow = srow + 1
            j = 1
            ven_invoice_keys = list(ven_invoice.keys())
            ven_invoice_keys.sort(key=lambda x: datetime.strptime(x,'%B %Y'))
            gtotal_vat_expense_other_ip = 0.0
            for data_vline in ven_invoice_keys:
                sheet.write(srow, 0, data_vline, title_style1_table_head)
                sheet.write(srow, 3, sum(line.amount_untaxed for line in ven_invoice[data_vline]), title_style1_table_head)
                sheet.write(srow, 4, sum(line.amount_tax for line in ven_invoice[data_vline]), title_style1_table_head)
                sheet.write(srow, 5, sum(line.amount_total for line in ven_invoice[data_vline]), title_style1_table_head)
                sheet.write(srow, 10, sum(line.amount_total for line in ven_invoice[data_vline]), title_style1_table_head)
                gtotal_vat_expense_other_ip += sum(line.amount_total for line in ven_invoice[data_vline])
                srow += 1
                for vline in ven_invoice[data_vline]:
    #                oldate = datetime.strptime(vline.date_invoice,'%Y-%m-%d')
                    oldate = vline.invoice_date
                    newdate = oldate.strftime(lang_date.date_format)
                    sheet.write(srow, 0, j, title_style1_table_data_sub)
    #                sheet.write(srow, 1, vline.number, title_style1_table_data_sub)
                    sheet.write(srow, 1, vline.name, title_style1_table_data_sub)
                    sheet.write(srow, 2, newdate, title_style1_table_data_sub)
                    sheet.write(srow, 3, vline.amount_untaxed, title_style1_table_data_sub)
                    sheet.write(srow, 4, vline.amount_tax, title_style1_table_data_sub)
                    sheet.write(srow, 5, vline.amount_total, title_style1_table_data_sub)
    #                sheet.write(srow, 4, vline.amount_tax, title_style1_table_data_sub)
                    sheet.write(srow, 6, vline.partner_id.sequence_no, title_style1_table_data_sub)
                    sheet.write(srow, 7, vline.partner_id.name, title_style1_table_data_sub)
                    sheet.write(srow, 8, vline.partner_id.vat, title_style1_table_data_sub)
                    sheet.write(srow, 9, vline.partner_id.city, title_style1_table_data_sub)
                    sheet.write(srow, 10, vline.currency_id.name, title_style1_table_data_sub)
                    srow = srow + 1;
                    j = j + 1;
#        srow = srow + 3
#        lsrow = srow + 1
#        sheet.write_merge(srow, lsrow, 0, 11, 'Reverse Charges - Services', title_style_comp_left)
#        srow = lsrow + 1;
#        sheet.write(srow, 0, 'Ser', title_style1_table_head1b)
#        sheet.write(srow, 1, 'Tax Invoice No', title_style1_table_head1b)
#        sheet.write(srow, 2, 'Tax Invoice Date', title_style1_table_head1b)
#        sheet.write(srow, 3, 'Gross Invoice amount (Without VAT)', title_style1_table_head1b)
#        sheet.write(srow, 4, 'VAT Amount VAT', title_style1_table_head1b)
#        sheet.write(srow, 5, 'Tax Invoice Amount AED', title_style1_table_head1b)
##        sheet.write(srow, 5, 'VAT Amount VAT', title_style1_table_head1b)
#        sheet.write(srow, 6, 'Supplier Name', title_style1_table_head1b)
#        sheet.write(srow, 7, 'Supplier TRN', title_style1_table_head1b)
#        sheet.write(srow, 8, 'Supplier Location', title_style1_table_head1b)
#        sheet.write(srow, 9, 'Currency', title_style1_table_head1b)
#        sheet.write(srow, 10, 'Total', title_style1_table_head1b)
        
        #ADDED Section For Credit Notes
        
            srow = srow + 3;
            lrow = srow + 1
            srow = lrow + 1
        gtotal_credit_notes = 0.0
        if credit_notes_inv:
            sheet.write_merge(lrow, srow, 0, 3, 'VAT on Credit Notes', title_style_comp_left)
            sheet.write_merge(lrow, srow, 4, 5, 'Start Date - ', title_style_comp_left)
            sheet.write_merge(lrow, srow, 6, 7, newformat, title_style_comp_left)
            sheet.write_merge(lrow, srow, 8, 9, 'End Date - ', title_style_comp_left)
            sheet.write_merge(lrow, srow, 10, 11, newend, title_style_comp_left)
            
            cnsrow = srow + 1;
            sheet.write(cnsrow, 0, 'SL NO', title_style1_table_head1b)
            sheet.write(cnsrow, 1, 'Tax Invoice No', title_style1_table_head1b)
            sheet.write(cnsrow, 2, 'Tax Invoice Date', title_style1_table_head1b)
            sheet.write(cnsrow, 3, 'Gross Invoice amount (Without VAT)', title_style1_table_head1b)
            sheet.write(cnsrow, 4, 'VAT Amount', title_style1_table_head1b)
            sheet.write(cnsrow, 5, 'Tax Invoice Amount AED', title_style1_table_head1b)
    #        sheet.write(cnsrow, 5, 'VAT Amount', title_style1_table_head1b)
            sheet.write(cnsrow, 6, 'Customer No.', title_style1_table_head1b)
            sheet.write(cnsrow, 7, 'Customer Name', title_style1_table_head1b)
            sheet.write(cnsrow, 8, 'Customer TRN', title_style1_table_head1b)
            sheet.write(cnsrow, 9, 'Customer Location', title_style1_table_head1b)
            sheet.write(cnsrow, 10, 'Currency', title_style1_table_head1b)
            sheet.write(cnsrow, 11, 'Currency', title_style1_table_head1b)
            
            cnlsrow = cnsrow + 1;
            k = 1
            credit_notes_inv_keys = list(credit_notes_inv.keys())
            credit_notes_inv_keys.sort(key=lambda x: datetime.strptime(x,'%B %Y'))
            gtotal_credit_notes = 0.0
            for data_cnline in credit_notes_inv_keys:
                sheet.write(cnlsrow, 0, data_cnline, title_style1_table_head)
                sheet.write(cnlsrow, 3, sum(line.amount_untaxed for line in credit_notes_inv[data_cnline]), title_style1_table_head)
                sheet.write(cnlsrow, 4, sum(line.amount_tax for line in credit_notes_inv[data_cnline]), title_style1_table_head)
                sheet.write(cnlsrow, 5, sum(line.amount_total for line in credit_notes_inv[data_cnline]), title_style1_table_head)
                sheet.write(cnlsrow, 10, sum(line.amount_total for line in credit_notes_inv[data_cnline]), title_style1_table_head)
                gtotal_credit_notes += sum(line.amount_total for line in credit_notes_inv[data_cnline])
                cnlsrow += 1
                for cnline in credit_notes_inv[data_cnline]:
    #                oldate = datetime.strptime(cnline.date_invoice,'%Y-%m-%d')
                    oldate = cnline.invoice_date
                    newdate = oldate.strftime(lang_date.date_format)
                    sheet.write(cnlsrow, 0, k, title_style1_table_data_sub)
    #                sheet.write(cnlsrow, 1, cnline.number, title_style1_table_data_sub)
                    sheet.write(cnlsrow, 1, cnline.name, title_style1_table_data_sub)
                    sheet.write(cnlsrow, 2, newdate, title_style1_table_data_sub)
                    sheet.write(cnlsrow, 3, cnline.amount_untaxed, title_style1_table_data_sub)
                    sheet.write(cnlsrow, 4, cnline.amount_tax, title_style1_table_data_sub)
                    sheet.write(cnlsrow, 5, cnline.amount_total, title_style1_table_data_sub)
    #                sheet.write(cnlsrow, 4, cnline.amount_tax, title_style1_table_data_sub)
                    sheet.write(cnlsrow, 6, cnline.partner_id.sequence_no, title_style1_table_data_sub)
                    sheet.write(cnlsrow, 7, cnline.partner_id.name, title_style1_table_data_sub)
                    sheet.write(cnlsrow, 8, cnline.partner_id.vat, title_style1_table_data_sub)
                    sheet.write(cnlsrow, 9, cnline.partner_id.city, title_style1_table_data_sub)
                    sheet.write(cnlsrow, 10, cnline.currency_id.name, title_style1_table_data_sub)
                    cnlsrow = cnlsrow + 1;
                    k = k + 1;
            srow = cnlsrow
            
        #ADDED Section For Debit Notes
        
            srow = srow + 3;
            lrow = srow + 1
            srow = lrow + 1
        gtotal_debit_notes = 0.0
        if debit_notes_inv:
            sheet.write_merge(lrow, srow, 0, 3, 'VAT on Debit Notes', title_style_comp_left)
            sheet.write_merge(lrow, srow, 4, 5, 'Start Date - ', title_style_comp_left)
            sheet.write_merge(lrow, srow, 6, 7, newformat, title_style_comp_left)
            sheet.write_merge(lrow, srow, 8, 9, 'End Date - ', title_style_comp_left)
            sheet.write_merge(lrow, srow, 10, 11, newend, title_style_comp_left)
            
            dnsrow = srow + 1;
            sheet.write(dnsrow, 0, 'SL NO', title_style1_table_head1b)
            sheet.write(dnsrow, 1, 'Tax Invoice No', title_style1_table_head1b)
            sheet.write(dnsrow, 2, 'Tax Invoice Date', title_style1_table_head1b)
            sheet.write(dnsrow, 3, 'Gross Invoice amount (Without VAT)', title_style1_table_head1b)
            sheet.write(dnsrow, 4, 'VAT Amount', title_style1_table_head1b)
            sheet.write(dnsrow, 5, 'Tax Invoice Amount AED', title_style1_table_head1b)
    #        sheet.write(dnsrow, 5, 'VAT Amount', title_style1_table_head1b)
            sheet.write(dnsrow, 6, 'Vendor No.', title_style1_table_head1b)
            sheet.write(dnsrow, 7, 'Supplier Name', title_style1_table_head1b)
            sheet.write(dnsrow, 8, 'Supplier TRN', title_style1_table_head1b)
            sheet.write(dnsrow, 9, 'Supplier Location', title_style1_table_head1b)
            sheet.write(dnsrow, 10, 'Currency', title_style1_table_head1b)
            sheet.write(dnsrow, 11, 'Total', title_style1_table_head1b)
            
            dnlsrow = dnsrow + 1;
            srow = dnlsrow
            l = 1
            debit_notes_inv_keys = list(debit_notes_inv.keys())
            debit_notes_inv_keys.sort(key=lambda x: datetime.strptime(x,'%B %Y'))
            gtotal_debit_notes = 0.0
            for dnline in debit_notes_inv_keys:
                sheet.write(dnlsrow, 0, dnline, title_style1_table_head)
                sheet.write(dnlsrow, 3, sum(line.amount_untaxed for line in debit_notes_inv[dnline]), title_style1_table_head)
                sheet.write(dnlsrow, 4, sum(line.amount_tax for line in debit_notes_inv[dnline]), title_style1_table_head)
                sheet.write(dnlsrow, 5, sum(line.amount_total for line in debit_notes_inv[dnline]), title_style1_table_head)
                sheet.write(dnlsrow, 10, sum(line.amount_total for line in debit_notes_inv[dnline]), title_style1_table_data_sub)
                gtotal_debit_notes += sum(line.amount_total for line in debit_notes_inv[dnline])
                dnlsrow += 1
                for dnline in debit_notes_inv[dnline]:
    #                oldate = datetime.strptime(dnline.date_invoice,'%Y-%m-%d')
                    oldate = dnline.invoice_date
                    newdate = oldate.strftime(lang_date.date_format)
                    sheet.write(dnlsrow, 0, l, title_style1_table_data_sub)
    #                sheet.write(dnlsrow, 1, dnline.number, title_style1_table_data_sub)
                    sheet.write(dnlsrow, 1, dnline.name, title_style1_table_data_sub)
                    sheet.write(dnlsrow, 2, newdate, title_style1_table_data_sub)
    #                sheet.write(dnlsrow, 3, cnline.amount_untaxed, title_style1_table_data_sub)
                    sheet.write(dnlsrow, 3, dnline.amount_untaxed, title_style1_table_data_sub)
                    sheet.write(dnlsrow, 4, dnline.amount_tax, title_style1_table_data_sub)
                    sheet.write(dnlsrow, 5, dnline.amount_total, title_style1_table_data_sub)
                    sheet.write(dnlsrow, 6, dnline.partner_id.sequence_no, title_style1_table_data_sub)
                    sheet.write(dnlsrow, 7, dnline.partner_id.name, title_style1_table_data_sub)
                    sheet.write(dnlsrow, 8, dnline.partner_id.vat, title_style1_table_data_sub)
                    sheet.write(dnlsrow, 9, dnline.partner_id.city, title_style1_table_data_sub)
                    sheet.write(dnlsrow, 10, dnline.currency_id.name, title_style1_table_data_sub)
                    dnlsrow = dnlsrow + 1;
                    l = l + 1;
    
            dnlsrow += 4
            srow = dnlsrow
        sheet.write(srow, 9, 'Grand Total', title_style1_table_head)
        sheet.write(srow, 10, gtotal_vat_sales_other_op - gtotal_credit_notes - gtotal_vat_expense_other_ip + gtotal_debit_notes, title_style1_table_head)
#        stream = cStringIO.StringIO()
        stream = io.BytesIO()
        workbook.save(stream)
        attach_id = self.env['invoice.wizard'].create({'name':'VAT Report.xls', 'xls_output': base64.encodestring(stream.getvalue())})
        return {
            'context': self.env.context,
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'invoice.wizard',
            'res_id':attach_id.id,
            'type': 'ir.actions.act_window',
            'target':'new'
        }

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
