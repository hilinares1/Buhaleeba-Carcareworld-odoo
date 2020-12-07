# -*- coding: utf-8 -*-

from odoo import models, fields, api


class StockPicking(models.Model):
    # _inherit = "account.invoice"
    _inherit = "stock.picking"