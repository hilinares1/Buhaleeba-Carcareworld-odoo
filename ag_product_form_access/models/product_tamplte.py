# -*- coding: utf-8 -*-

from odoo import models, fields
from odoo.exceptions import ValidationError


class Product(models.Model):
    _inherit = 'product.template'

    def write(self, vals):
        generate_warn_lst = ['categ_id', 'standard_price', 'list_price', 'property_account_income_id', 'property_account_expense_id', 'asset_category_id', 'property_account_creditor_price_difference']
        for rec in self:
            if any(key in generate_warn_lst for key in vals.keys()) and rec.state == 'confirmed' and not self.env.user.has_group("AG_purchase.group_purchase_operation_manager"):
                raise ValidationError("You are not allowed to modify value of the field(s), if you want you can contact your Operation Manager.")
        return super(Product, self).write(vals)

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
