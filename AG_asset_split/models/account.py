from odoo import api, fields, models
from odoo import tools

class AccountMove(models.Model):
    _inherit = 'account.move'

    categ_asset_id = fields.Many2one('account.asset.category', string='Category')
