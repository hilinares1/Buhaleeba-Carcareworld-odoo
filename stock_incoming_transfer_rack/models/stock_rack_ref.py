# -*- coding: utf-8 -*-

from odoo import models, fields, api


class StockRackRef(models.Model):
    _name = 'stock.rack.shelf'
    _rec_name = 'complete_name'

    name = fields.Char(
        string='Name',
        required=True,
    )
    code = fields.Char(
        string='Code',
        required=True,
    )
    parent_id = fields.Many2one(
        'stock.rack.shelf',
        index=True,
        ondelete='cascade',
    )
    complete_name = fields.Char(
        'Complete Name',
        compute='_compute_complete_name',
        store=True
    )
    
    @api.depends('name', 'parent_id.complete_name')
    def _compute_complete_name(self):
        for rack_shelf in self:
            if rack_shelf.parent_id:
                rack_shelf.complete_name = '%s / %s' % (rack_shelf.name , rack_shelf.parent_id.complete_name)
            else:
                rack_shelf.complete_name = rack_shelf.name

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
