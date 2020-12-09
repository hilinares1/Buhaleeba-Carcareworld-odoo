# Copyright 2018 Tecnativa - Sergio Teruel
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
from odoo import fields, models
from odoo.exceptions import except_orm, ValidationError ,UserError


class ProductTemplate(models.Model):
    _inherit = "product.template"

    auto_create_lot = fields.Boolean(string="Auto Create Lot")

class StockPicking(models.Model):
    _inherit = "stock.picking"

    def button_validate(self):
        res = super(StockPicking,self).button_validate()

        if self.move_line_ids_without_package:
            for move in self.move_line_ids_without_package:
                if move.lot_id.name != move.issued_lot:
                    raise UserError('The issued lot and assigned lot from system not same for this product %s'%(move.product_id.name))

        return res