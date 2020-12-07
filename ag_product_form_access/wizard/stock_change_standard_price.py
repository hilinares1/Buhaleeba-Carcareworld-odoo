# -*- coding: utf-8 -*-

from odoo import models
from odoo.exceptions import ValidationError


class StockChangeStandardPrice(models.TransientModel):
    _inherit = "stock.change.standard.price"

    #@Override
    def change_price(self):
        self.ensure_one()
        if self._context['active_model'] == 'product.template':
            product_tmpl_id = self.env['product.template'].browse(self._context['active_id'])
            if product_tmpl_id.state == 'confirmed' and not self.env.user.has_group("AG_purchase.group_purchase_operation_manager"):
                raise ValidationError("You are not allowed to modify value of the field(s), if you want you can contact your Operation Manager.")
        return super(StockChangeStandardPrice, self).change_price()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
