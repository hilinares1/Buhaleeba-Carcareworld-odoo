# -*- coding: utf-8 -*-

import datetime
#from openerp import models, fields, api
from odoo import models, fields, api


class InvoiceRender(models.AbstractModel):
    _name='report.ag_tax_custom_report.invoice_print'

    @api.model
    def _get_customer_invoice(self, data):
        customer_inv = []
#        cinvoice_ids = self.env['account.invoice'].search([('date_invoice', '>=', data.get('start_date', False)), ('date_invoice', '<=', data.get('end_date', False)), ('type', '=', 'out_invoice')], order="number asc, id asc")
        dict_inv = {}
        if not data.get("report_type") or data.get("report_type") == 'sale_report':
            cinvoice_ids = self.env['account.move'].search([('invoice_date', '>=', data.get('start_date', False)), ('invoice_date', '<=', data.get('end_date', False)), ('type', '=', 'out_invoice')], order="name asc, id asc")
#            dict_inv = {}
            for line in cinvoice_ids:
                customer_inv.append(line)
    #            curr_date_inv = fields.Datetime.from_string(line.date_invoice)
                curr_date_inv = fields.Datetime.from_string(line.invoice_date)
                if curr_date_inv.strftime('%B %Y') in dict_inv:
                    dict_inv[curr_date_inv.strftime('%B %Y')].append(line)
                else:
                    dict_inv.update({
                         curr_date_inv.strftime('%B %Y'): [line]
                     })
#        return customer_inv
        inv_keys = list(dict_inv.keys())
        inv_keys.sort(key=lambda x: datetime.datetime.strptime(x,'%B %Y'))
        dict_inv.update({
            'cust_inv_keys': inv_keys,
        })
        return dict_inv
    
    @api.model
    def _get_customer_credit_notes(self, data):
        credit_notes_inv = []
#        credit_notes_ids = self.env['account.invoice'].search([('date_invoice', '>=', data.get('start_date', False)), ('date_invoice', '<=', data.get('end_date', False)), ('type', '=', 'out_refund')], order="number asc, id asc")
        dict_inv = {}
        if not data.get("report_type") or data.get("report_type") == 'sale_report':
            credit_notes_ids = self.env['account.move'].search([('invoice_date', '>=', data.get('start_date', False)), ('invoice_date', '<=', data.get('end_date', False)), ('type', '=', 'out_refund')], order="name asc, id asc")
#            dict_inv = {}
            for line in credit_notes_ids:
                credit_notes_inv.append(line)
    #            curr_date_inv = fields.Datetime.from_string(line.date_invoice)
                curr_date_inv = fields.Datetime.from_string(line.invoice_date)
                if curr_date_inv.strftime('%B %Y') in dict_inv:
                    dict_inv[curr_date_inv.strftime('%B %Y')].append(line)
                else:
                    dict_inv.update({
                         curr_date_inv.strftime('%B %Y'): [line]
                     })
#        return credit_notes_inv
        inv_keys = list(dict_inv.keys())
        inv_keys.sort(key=lambda x: datetime.datetime.strptime(x,'%B %Y'))
        dict_inv.update({
            'credit_notes_keys': inv_keys,
        })
        return dict_inv

    @api.model
    def _get_vendor_invoice(self, data):
        vendor_inv = []
#        vinvoice_ids = self.env['account.invoice'].search([('date_invoice', '>=', data.get('start_date', False)), ('date_invoice', '<=', data.get('end_date', False)), ('type', '=', 'in_invoice')], order="number asc, id asc")
        dict_inv = {}
        if not data.get("report_type") or data.get("report_type") == 'purchase_report':
            vinvoice_ids = self.env['account.move'].search([('invoice_date', '>=', data.get('start_date', False)), ('invoice_date', '<=', data.get('end_date', False)), ('type', '=', 'in_invoice')], order="name asc, id asc")
#            dict_inv = {}
            for vline in vinvoice_ids:
                vendor_inv.append(vline)
    #            curr_date_inv = fields.Datetime.from_string(vline.date_invoice)
                curr_date_inv = fields.Datetime.from_string(vline.invoice_date)
                if curr_date_inv.strftime('%B %Y') in dict_inv:
                    dict_inv[curr_date_inv.strftime('%B %Y')].append(vline)
                else:
                    dict_inv.update({
                         curr_date_inv.strftime('%B %Y'): [vline]
                     })
#        return vendor_inv
        inv_keys = list(dict_inv.keys())
        inv_keys.sort(key=lambda x: datetime.datetime.strptime(x,'%B %Y'))
        dict_inv.update({
            'vinvoice_keys': inv_keys,
        })
        return dict_inv
    
    @api.model
    def _get_supplier_debit_notes(self, data):
        debit_notes_inv = []
#        debit_notes_ids = self.env['account.invoice'].search([('date_invoice', '>=', data.get('start_date', False)), ('date_invoice', '<=', data.get('end_date', False)), ('type', '=', 'in_refund')], order="number asc, id asc")
        dict_inv = {}
        if not data.get("report_type") or data.get("report_type") == 'purchase_report':
            debit_notes_ids = self.env['account.move'].search([('invoice_date', '>=', data.get('start_date', False)), ('invoice_date', '<=', data.get('end_date', False)), ('type', '=', 'in_refund')], order="name asc, id asc")
#            dict_inv = {}
            for line in debit_notes_ids:
                debit_notes_inv.append(line)
    #            curr_date_inv = fields.Datetime.from_string(line.date_invoice)
                curr_date_inv = fields.Datetime.from_string(line.invoice_date)
                if curr_date_inv.strftime('%B %Y') in dict_inv:
                    dict_inv[curr_date_inv.strftime('%B %Y')].append(line)
                else:
                    dict_inv.update({
                         curr_date_inv.strftime('%B %Y'): [line]
                     })
#        return debit_notes_inv
        inv_keys = list(dict_inv.keys())
        inv_keys.sort(key=lambda x: datetime.datetime.strptime(x,'%B %Y'))
        dict_inv.update({
            'debit_notes_keys': inv_keys,
        })
        return dict_inv


    @api.model
#    def render_html(self,docids, data=None):
    def _get_report_values(self, docids, data=None):
        docargs = {
            'doc_ids': data['ids'],
            'doc_model': data['model'],
            'data': data,
            'customer_invoice': self._get_customer_invoice(data),
            'vendor_invoice': self._get_vendor_invoice(data),
            'credit_notes': self._get_customer_credit_notes(data),
            'dedit_notes': self._get_supplier_debit_notes(data),
            'docs': self.env[data['model']].browse(data['ids']),
        }
        return docargs
#        return self.env['report'].render('odoo_tax_custom_report.invoice_print', docargs)

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
