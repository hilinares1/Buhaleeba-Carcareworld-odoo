from odoo import models, fields
import datetime
import io
import base64

LETTERS = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'


def excel_style(row, col):
    """ Convert given row and column number to an Excel-style cell name. """
    result = []
    while col:
        col, rem = divmod(col - 1, 26)
        result[:0] = LETTERS[rem]
    return ''.join(result) + str(row)


class StoreReport(models.AbstractModel):
    _name = 'report.mastex.report.report.xlsx'
    _inherit = 'report.report_xlsx.abstract'

    def generate_xlsx_report(self, workbook, data, wiz):

        heading_format = workbook.add_format({'align': 'center',
                                              'valign': 'vcenter',
                                              'bold': True, 'size': 15,
                                              # 'bg_color': '#0077b3',
                                              })
        sub_heading_format = workbook.add_format({'align': 'center',
                                                  'valign': 'vcenter',
                                                  'bold': True, 'size': 11,
                                                  # 'bg_color': '#0077b3',
                                                  # 'font_color': '#FFFFFF'
                                                  })
        sub_heading_format_company = workbook.add_format({'align': 'left',
                                                          'valign': 'left',
                                                          'bold': True, 'size': 11,
                                                          # 'bg_color': '#0077b3',
                                                          # 'font_color': '#FFFFFF'
                                                          })

        col_format = workbook.add_format({'valign': 'left',
                                          'align': 'left',
                                          'bold': True,
                                          'size': 10,
                                          'font_color': '#000000'
                                          })
        data_format = workbook.add_format({'valign': 'center',
                                           'align': 'center',
                                           'size': 10,
                                           'font_color': '#000000'
                                           })
        line_format = workbook.add_format({'align': 'center',
                                           'valign': 'vcenter',
                                           'size': 1,
                                           'bg_color': '#9A9A9A',
                                           })

        col_format.set_text_wrap()
        worksheet = workbook.add_worksheet('Mastex MTO Report')
        worksheet.set_column('A:A', 10)
        worksheet.set_column('B:B', 10)
        worksheet.set_column('C:C', 20)
        worksheet.set_column('D:D', 30)
        worksheet.set_column('E:E', 40)
        worksheet.set_column('F:F', 35)
        worksheet.set_column('G:G', 30)
        worksheet.set_column('H:H', 35)
        worksheet.set_column('I:I', 35)
        worksheet.set_column('J:J', 30)
        worksheet.set_column('K:K', 30)
        worksheet.set_column('L:L', 30)
        worksheet.set_column('M:M', 30)
        worksheet.set_column('N:N', 30)
        worksheet.set_column('O:O', 30)
        worksheet.set_column('P:P', 30)
        worksheet.set_column('Q:Q', 30)
        worksheet.set_column('R:R', 30)
        row = 1
        worksheet.set_row(1, 20)

        row += 1
        worksheet.write(row, 0, "Notes", sub_heading_format)
        worksheet.write(row, 1, " ", sub_heading_format)
        worksheet.write(row, 2, "Commission", sub_heading_format)
        worksheet.write(row, 3, "Customer total with rate difference", sub_heading_format)
        worksheet.write(row, 4, "Customer total" , sub_heading_format)
        worksheet.write(row, 5, "vendor Total" , sub_heading_format)
        worksheet.write(row, 6, "Number of Packages" , sub_heading_format)
        worksheet.write(row, 7, "Actual Quantity", sub_heading_format)
        worksheet.write(row, 8, "Quantity", sub_heading_format)
        worksheet.write(row, 9, "UOM", sub_heading_format)
        worksheet.write(row, 10, "Selling Price", sub_heading_format)
        worksheet.write(row, 11, "Purchase Price", sub_heading_format)
        worksheet.write(row, 12, "Product Name", sub_heading_format)
        worksheet.write(row, 13, "Date of arrival", sub_heading_format)
        worksheet.write(row, 14, "Bill of landing Date", sub_heading_format)
        worksheet.write(row, 15, "Shipment Date", sub_heading_format)
        worksheet.write(row, 16, "LC Number", sub_heading_format)
        worksheet.write(row, 17, "Bank", sub_heading_format)
        worksheet.write(row, 13, "Country", sub_heading_format)
        worksheet.write(row, 14, "Vendor name", sub_heading_format)
        worksheet.write(row, 15, "Customer name", sub_heading_format)
        worksheet.write(row, 16, "Order Number", sub_heading_format)
        worksheet.write(row, 17, "Order Date", sub_heading_format)
        row += 1
        sl_no = 0
