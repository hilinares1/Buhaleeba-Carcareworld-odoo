# Copyright 2016 ACSONE SA/NV (<http://acsone.eu>)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from dateutil.relativedelta import relativedelta
from dateutil.rrule import DAILY, MONTHLY, WEEKLY, YEARLY, rrule

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class LandCostGenerator(models.TransientModel):
    _name = "landed.cost.generator"
    _description = "Land Generator"

    validate = fields.Boolean('Validate',default=False)

    def Validate(self):
        self.validate = True
        active = self.env['stock.picking'].browse(self._context['active_ids'])
        res = active.button_validate()
        return res

    def Create_landcost(self):
        active = self.env['stock.picking'].browse(self._context['active_ids'])
        return {
        #'name': self.order_id,
        'res_model': 'stock.landed.cost',
        'type': 'ir.actions.act_window',
        'context': {'default_picking_ids':[(6,0, [active.id])]},
        'view_mode': 'form',
        'view_type': 'form',
        'view_id': self.env.ref("stock_landed_costs.view_stock_landed_cost_form").id,
        'target': 'new'
    }
