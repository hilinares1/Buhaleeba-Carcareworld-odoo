# -*- coding: utf-8 -*-

from odoo import models, fields
from odoo.exceptions import ValidationError


class StockReturnPicking(models.Model):
    _inherit = "stock.picking"

    custom_return_reason = fields.Char(
        string='Return Reason',
        copy=False,
    )
    custom_picking_approve = fields.Boolean(
        string='Is Return Approve',
        copy=False,
    )
    custom_picking_reject = fields.Boolean(
        string='Is Return Reject',
        copy=False,
    )
    custom_is_returned_picking = fields.Boolean(
        string='Is Return Picking',
        copy=False,
    )

    def action_custom_button_approve(self):
        self.custom_picking_approve = True
        self.custom_picking_reject = False

    def action_custom_button_reject(self):
        self.custom_picking_reject = True

    def button_validate(self):
        if self.custom_is_returned_picking and self.custom_picking_reject:
            raise ValidationError("Not Allowed to Validate if Picking is rejected.")
        if self.custom_is_returned_picking and not self.custom_picking_approve:
            raise ValidationError("Not Allowed to Validate Until Picking is not approved.")
        return super(StockReturnPicking, self).button_validate()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
