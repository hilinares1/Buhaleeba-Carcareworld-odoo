
from dateutil.relativedelta import relativedelta
from odoo import api, fields, models, _
from odoo.exceptions import UserError
import numpy


class AccountInvoiceLine(models.Model):
    _inherit = 'account.move.line'


    def asset_create(self):

        if self.asset_category_id:
            for x in numpy.arange(self.quantity):
                vals = {
                    'name': self.name,
                    'code': self.name or False,
                    'category_id': self.asset_category_id.id,

                    'value': self.price_subtotal / self.quantity,
                    'partner_id': self.move_id.partner_id.id,
                    'company_id': self.move_id.company_id.id,
                    'currency_id': self.move_id.company_currency_id.id,
                    'date': self.move_id.invoice_date,
                    'invoice_id': self.move_id.id,
                }

                changed_vals = self.env['account.asset.asset'].onchange_category_id_values(vals['category_id'])
                vals.update(changed_vals['value'])
                asset = self.env['account.asset.asset'].create(vals)
                if self.asset_category_id.open_asset:
                    asset.validate()
        return True


class AccountAssetAssetInherit(models.Model):
    _inherit = 'account.asset.asset'

    sales_value = fields.Float(string='Sale Value')
