# -*- coding: utf-8 -*-

from odoo import models, fields


class StockValuationLayer(models.Model):
    """Stock Valuation Layer"""

    _inherit = 'stock.valuation.layer'

    custom_owner_id = fields.Many2one(
        'res.partner',
        string='Assigned Owner',
    )
