from odoo import api, fields, models, _


class AssetDepreciationConfirmationWizard(models.TransientModel):
    _inherit = "asset.depreciation.confirmation.wizard"
    _description = "asset.depreciation.confirmation.wizard"

    asset_categ_id = fields.Many2one('account.asset.category', string='Category')

    def asset_compute(self):
        res = super(AssetDepreciationConfirmationWizard, self).asset_compute()
        domain_filter = []
        if self.asset_categ_id:
            domain_filter.append(('categ_asset_id', '=', self.asset_categ_id.id))
        res['domain'] = str(domain_filter)
        return res
