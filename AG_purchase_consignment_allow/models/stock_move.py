# -*- coding: utf-8 -*-

from odoo import models, fields


class StockMove(models.Model):
    _inherit = 'stock.move'

    def _prepare_common_svl_vals(self):
        res = super(StockMove, self)._prepare_common_svl_vals()
        if self.picking_id and self.picking_id.owner_id:
            res.update({
                'custom_owner_id': self.picking_id.owner_id.id
            })
        return res

#    @FULLY OVERRIDE to Allow generate Valuation Layer for Owner
    def _get_in_move_lines(self):
        self.ensure_one()
        res = self.env['stock.move.line']
        for move_line in self.move_line_ids:
#            if move_line.owner_id and move_line.owner_id != move_line.company_id.partner_id: REMOVED FOR ALLOWED TO CREATE VALUATION FOR ANY OWNER
#                continue
            if not move_line.location_id._should_be_valued() and move_line.location_dest_id._should_be_valued():
                res |= move_line
        return res

#    @FULLY OVERRIDE to Allow generate Valuation Layer for Owner
    def _get_out_move_lines(self):
        res = self.env['stock.move.line']
        for move_line in self.move_line_ids:
#            if move_line.owner_id and move_line.owner_id != move_line.company_id.partner_id: REMOVED FOR ALLOWED TO CREATE VALUATION FOR ANY OWNER
#                continue
            if move_line.location_id._should_be_valued() and not move_line.location_dest_id._should_be_valued():
                res |= move_line
        return res

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
