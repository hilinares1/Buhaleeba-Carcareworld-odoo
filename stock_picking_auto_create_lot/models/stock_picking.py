# Copyright 2018 Tecnativa - Sergio Teruel
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
from odoo import fields, models
from odoo.exceptions import except_orm, ValidationError ,UserError
from datetime import datetime, timedelta , date

class StockPickingType(models.Model):
    _inherit = "stock.picking.type"

    auto_create_lot = fields.Boolean(string="Auto Create Lot")


class StockPicking(models.Model):
    _inherit = "stock.picking"

    def button_validate(self):
        if self.move_line_ids_without_package:
            for move in self.move_line_ids_without_package:
                if move.lot_id.name != move.issued_lot:
                    raise UserError('The issued lot and assigned lot from system not same for this product %s'%(move.product_id.name))

        if self.picking_type_id.auto_create_lot:
            i = 1
            lot = {}
            for line in self.move_line_ids.filtered(
                lambda x: (
                    not x.lot_id
                    and not x.lot_name
                    and x.product_id.tracking != "none"
                    and x.product_id.auto_create_lot
                )
            ):
                name = str(self.origin) + "-%s"%(date.today())
                if i == 1:
                    lot = self.env["stock.production.lot"].create(
                        {"name":name,"product_id": line.product_id.id, "company_id": line.company_id.id}
                    )
                    line.lot_id = lot.id
                else:
                    lot2 = self.env["stock.production.lot"].create(
                        {"name":lot.name,"product_id": line.product_id.id, "company_id": line.company_id.id}
                    )
                    line.lot_id = lot2.id
                i = i + 1
        return super().button_validate()


class StockMoveLine(models.Model):
    _inherit = "stock.move.line"

    issued_lot = fields.Char('Issued Lot')