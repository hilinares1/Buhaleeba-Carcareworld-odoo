# -*- coding: utf-8 -*-

from odoo import models, fields,api


class PurchaseOrderLine(models.Model):
    _inherit = "purchase.order.line"

    is_landed_costs_line = fields.Boolean(
        string='Landed Costs',compute='get_landed_cost',store=True
    )

    @api.onchange('product_id')
    def get_landed_cost(self):
        for rec in self:
            if rec.product_id:
                rec.is_landed_costs_line = rec.product_id.landed_cost_ok
            else:
                rec.is_landed_costs_line = False

    def _prepare_account_move_line(self, move):
        res = super(PurchaseOrderLine, self)._prepare_account_move_line(move)
        res.update({
            'is_landed_costs_line': self.is_landed_costs_line,
        })
        return res


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
