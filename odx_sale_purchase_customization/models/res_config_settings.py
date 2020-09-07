# -*- coding: utf-8 -*-
###################################################################################
#
#    Copyright (C) 2020 Odox SoftHub LLP(<www.odoxsofthub.com>)
#    Author: Albin Mathew(<albinmathew07@outlook.com>)
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
###################################################################################

from odoo import api, fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    commission_account_id = fields.Many2one(comodel_name='account.account', string="Commission Account")
    discount_account_id = fields.Many2one(comodel_name='account.account', string="Discount Account")
    bank_fee_account_id = fields.Many2one(comodel_name='account.account', string="Bank Fee Account")
    currency_diff_account_id = fields.Many2one(comodel_name='account.account', string="Currency Diff Account")

    @api.model
    def get_values(self):
        res = super(ResConfigSettings, self).get_values()
        params = self.env['ir.config_parameter'].sudo()
        res.update(
            commission_account_id=int(params.get_param('odx_sale_purchase_customization.commission_account_id')),

        )
        res.update(
            discount_account_id=int(params.get_param('odx_sale_purchase_customization.discount_account_id')),

        )
        res.update(
            bank_fee_account_id=int(params.get_param('odx_sale_purchase_customization.bank_fee_account_id')),

        )
        res.update(
            currency_diff_account_id=int(params.get_param('odx_sale_purchase_customization.currency_diff_account_id')),

        )

        return res

    def set_values(self):
        super(ResConfigSettings, self).set_values()
        self.env['ir.config_parameter'].sudo().set_param("odx_sale_purchase_customization.commission_account_id",
                                                         self.commission_account_id.id)
        self.env['ir.config_parameter'].sudo().set_param("odx_sale_purchase_customization.discount_account_id",
                                                         self.discount_account_id.id)
        self.env['ir.config_parameter'].sudo().set_param("odx_sale_purchase_customization.bank_fee_account_id",
                                                         self.bank_fee_account_id.id)
        self.env['ir.config_parameter'].sudo().set_param("odx_sale_purchase_customization.currency_diff_account_id",
                                                         self.currency_diff_account_id.id)



