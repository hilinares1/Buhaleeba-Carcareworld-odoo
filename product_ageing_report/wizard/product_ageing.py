# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import ValidationError


class AgeingAnalysis(models.TransientModel):
    _name = 'product.ageing'

    from_date = fields.Datetime(string="Starting Date", required=True)
    location_id = fields.Many2many('stock.location', string="Location", domain=[('usage', '=', 'internal')])
    product_categ = fields.Many2many('product.category', string="Category")
    interval = fields.Integer(string="Interval(days)", default=30, required=True)
    filter_by = fields.Selection([
        ('location', "Location"), ('lot', "Lot"),
    ], string="Expand By", default='lot')
    owner_id = fields.Many2many('res.partner', string='Owner')

    @api.model
    def compute_ageing(self, data):
        """Redirects to the report with the values obtained from the wizard
                'data['form']':  date duration"""
        rec = self.browse(data)
        data = {}
        data['form'] = rec.read(['from_date', 'location_id', 'product_categ','owner_id','interval'])
        return self.env.ref('product_ageing_report.report_product_ageing').report_action(self,data=data)

    @api.model
    def xlsx_ageing_report(self, data):
        rec = self.browse(data)
        data = {}
        data['form'] = rec.read(['from_date', 'location_id', 'product_categ','owner_id', 'interval', 'filter_by'])
        if not rec.filter_by:
            raise ValidationError('Please select a Expand Option for Report')
        return self.env.ref('product_ageing_report.report_product_ageing_xlsx').report_action(self, data=data)
