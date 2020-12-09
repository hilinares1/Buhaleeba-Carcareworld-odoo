# Copyright 2018 Tecnativa - Sergio Teruel
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
from odoo import fields, models
from odoo.exceptions import except_orm, ValidationError ,UserError
from datetime import datetime, timedelta , date
import random

class StockPickingType(models.Model):
    _inherit = "stock.picking.type"

    auto_create_lot = fields.Boolean(string="Auto Create Lot")


class StockPicking(models.Model):
    _inherit = "stock.picking"


    # def _get_lot_name(self):
    #     dates = date.today()
    #     random_num = random.randrange(9, 1, -2)
    #     name = str(self.origin) + "-%s%s"%(dates.strftime("%d%m%y"),random_num)
    #     for line in self.move_line_ids.filtered(
    #             lambda x: (
    #                 not x.lot_id
    #                 and not x.lot_name
    #                 and x.product_id.tracking != "none"
    #                 and x.product_id.auto_create_lot
    #             )
    #         ):
    #         if self.env['stock.production.lot'].search([('name','=',name),('product_id','=',line.product_id.id)]):
    #             self._get_lot_name()
    #         else:
    #             continue
    #     return name
        

    def button_validate(self):

        # dates = date.today()
        # random = random.randrange(10, 1, -2)
        # name = str(self.origin) + "-%s-%s"%(dates.strftime("%m%d%y"),random)
        # if self.env['stock.production.lot'].search([('name','=',name),('product','=',line.product_id.id)]):
        dates = date.today()
        # random_num = random.randrange(9, 1, -2)
        origin = self.origin.replace('P0','')
        name = str(origin) + "-%s%s"%(dates.strftime("%d%m%y"),self.id)
        # for line in self.move_line_ids.filtered(
        #         lambda x: (
        #             not x.lot_id
        #             and not x.lot_name
        #             and x.product_id.tracking != "none"
        #             and x.product_id.auto_create_lot
        #         )
        #     ):
        #     if self.env['stock.production.lot'].search([('name','=',name),('product_id','=',line.product_id.id)]):
        #         random_num = random.randrange(9, 1, -2)
        #         name = str(self.origin) + "-%s%s"%(dates.strftime("%d%m%y"),random_num)
        #     else:
        #         continue
        # raise UserError(name)
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
                # name = str(self.origin) + "-%s"%(datetime.today())
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