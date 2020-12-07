# -*- coding: utf-8 -*-

from odoo import models, fields


class PurchaseOrderLine(models.Model):
    _inherit = "purchase.order.line"

    is_landed_costs_line = fields.Boolean(
        string='Landed Costs'
    )

    def _prepare_account_move_line(self, move):
        res = super(PurchaseOrderLine, self)._prepare_account_move_line(move)
        res.update({
            'is_landed_costs_line': self.is_landed_costs_line,
        })
        return res


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
