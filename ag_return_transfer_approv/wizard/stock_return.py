# -*- coding: utf-8 -*-

from odoo import models, fields


class StockReturnPicking(models.TransientModel):
    _inherit = "stock.return.picking"

    custom_return_reason = fields.Char(
        string='Return Reason',
        required=True
    )

    def _prepare_move_default_values(self, return_line, new_picking):
        new_picking.write({
            'custom_return_reason': new_picking.origin + ' ' + self.custom_return_reason,
            'custom_is_returned_picking': True,
        })
        return super(StockReturnPicking, self)._prepare_move_default_values(return_line, new_picking)


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
