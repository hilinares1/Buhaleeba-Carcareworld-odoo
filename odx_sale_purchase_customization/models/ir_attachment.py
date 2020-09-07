from odoo import models, fields, api, _


class Attachment(models.Model):
    _inherit = 'ir.attachment'

    sale_id = fields.Many2one('sale.order', string='Sale Order')
    purchase_id = fields.Many2one('purchase.order', string='Purchase Order')
    description = fields.Char(string='Description')
